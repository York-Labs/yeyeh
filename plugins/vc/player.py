"""
在 Telegram 语音聊天中播放和控制音频播放

依赖项：
- ffmpeg

所需的组管理员权限：
- 删除消息
- 管理语音聊天（可选）

如何使用：
- 启动用户机器人
- 发送！join启用语音聊天的群聊
  来自用户机器人帐户本身或其联系人
- 使用 /play 回复音频以开始播放
  它在语音聊天中，群里的每个成员
  现在可以使用 !play 命令
  - 查看 !help 获取更多命令
"""
import asyncio
import os
from datetime import datetime, timedelta

# noinspection PyPackageRequirements
import ffmpeg
from pyrogram import Client, filters, emoji
from pyrogram.methods.messages.download_media import DEFAULT_DOWNLOAD_DIR
from pyrogram.types import Message
from pyrogram.utils import MAX_CHANNEL_ID
from pytgcalls import GroupCallFactory, GroupCallFileAction

DELETE_DELAY = 8
DURATION_AUTOPLAY_MIN = 10
DURATION_PLAY_HOUR = 3

USERBOT_HELP = f""""{emoji.LABEL} **常用命令**：
__可供当前语音聊天的群组成员使用__
__ 以 /（斜杠）或 !（感叹号）开头__

/play 用音频回复以播放/play，或显示播放列表
/current 显示当前曲目的当前播放时间
/repo 显示用户机器人的 git 存储库
`!help` 显示命令的帮助


{emoji.LABEL} **管理命令**：
__可供用户机器人帐户本身及其联系人使用__
__用!（感叹号）开头__

`!skip` [n] ... 跳过当前或 n 其中 n >= 2
`!join` 加入当前群组的语音聊天
`!leave` 离开当前语音聊天
`!vc` 检查加入了哪个 VC
`!stop` 停止播放
`!replay` 从头开始播放
`!clean` 删除未使用的 RAW PCM 文件
`!pause` 暂停播放
`!resume` 继续播放
`!mute` 使 VC 用户机器人静音
`!unmute` 取消 VC 用户机器人的静音"""

USERBOT_REPO = f"""{emoji.ROBOT} **电报语音聊天用户机器人**
- 原版：[GitHub](https://github.com/callsmusic/tgvc-userbot)
- 中文版：[GitHub](https://github.com/mengxin239/tgvc-chinese)
- 许可证：AGPL-3.0 或更高版本"""

# - Pyrogram filters

main_filter = (filters.group
               & filters.text
               & ~filters.edited
               & ~filters.via_bot)
self_or_contact_filter = filters.create(
    lambda _, __, message:
    (message.from_user and message.from_user.is_contact) or message.outgoing
)


async def current_vc_filter(_, __, m: Message):
    group_call = mp.group_call
    if not (group_call and group_call.is_connected):
        return False
    chat_id = int("-100" + str(group_call.full_chat.id))
    if m.chat.id == chat_id:
        return True
    return False


current_vc = filters.create(current_vc_filter)


# - class


class MusicPlayer(object):
    def __init__(self):
        self.group_call = None
        self.client = None
        self.chat_id = None
        self.start_time = None
        self.playlist = []
        self.msg = {}

    async def update_start_time(self, reset=False):
        self.start_time = (
            None if reset
            else datetime.utcnow().replace(microsecond=0)
        )

    async def send_playlist(self):
        playlist = self.playlist
        if not playlist:
            pl = f"{emoji.NO_ENTRY} 播放列表是空的哎.."
        else:
            if len(playlist) == 1:
                pl = f"{emoji.REPEAT_SINGLE_BUTTON} **播放列表**:\n"
            else:
                pl = f"{emoji.PLAY_BUTTON} **播放列表**:\n"
            pl += "\n".join([
                f"**{i}**. **[{x.audio.title}]({x.link})**"
                for i, x in enumerate(playlist)
            ])
        if mp.msg.get('playlist') is not None:
            await mp.msg['playlist'].delete()
        mp.msg['playlist'] = await send_text(pl)


mp = MusicPlayer()


# - pytgcalls handlers


async def network_status_changed_handler(context, is_connected: bool):
    if is_connected:
        mp.chat_id = MAX_CHANNEL_ID - context.full_chat.id
        await send_text(f"{emoji.CHECK_MARK_BUTTON}  已加入语音聊天")
    else:
        await send_text(f"{emoji.CROSS_MARK_BUTTON} 已退出语音聊天")
        mp.chat_id = None


async def playout_ended_handler(_, __):
    await skip_current_playing()


# - Pyrogram handlers


@Client.on_message(
    filters.group
    & ~filters.edited
    & current_vc
    & (filters.regex("^(\\/|!)play$") | filters.audio)
)
async def play_track(client, m: Message):
    group_call = mp.group_call
    playlist = mp.playlist
    # check audio
    if m.audio:
        if m.audio.duration > (DURATION_AUTOPLAY_MIN * 60):
            reply = await m.reply_text(
                f"{emoji.ROBOT} 播放时间大于 "
                f"{str(DURATION_AUTOPLAY_MIN)} 分钟的不会被 "
                "添加到播放列表中的呢.."
            )
            await _delay_delete_messages((reply,), DELETE_DELAY)
            return
        m_audio = m
    elif m.reply_to_message and m.reply_to_message.audio:
        m_audio = m.reply_to_message
        if m_audio.audio.duration > (DURATION_PLAY_HOUR * 60 * 60):
            reply = await m.reply_text(
                f"{emoji.ROBOT} 播放时间大于 "
                f"{str(DURATION_PLAY_HOUR)} 小时的不会被添加到列表中的呢.."
            )
            await _delay_delete_messages((reply,), DELETE_DELAY)
            return
    else:
        await mp.send_playlist()
        await m.delete()
        return
    # check already added
    if playlist and playlist[-1].audio.file_unique_id \
            == m_audio.audio.file_unique_id:
        reply = await m.reply_text(f"{emoji.ROBOT} 已经点过这个歌了呢..")
        await _delay_delete_messages((reply, m), DELETE_DELAY)
        return
    # add to playlist
    playlist.append(m_audio)
    if len(playlist) == 1:
        m_status = await m.reply_text(
            f"{emoji.INBOX_TRAY} 正在下载并转码..."
        )
        await download_audio(playlist[0])
        group_call.input_filename = os.path.join(
            client.workdir,
            DEFAULT_DOWNLOAD_DIR,
            f"{playlist[0].audio.file_unique_id}.raw"
        )
        await mp.update_start_time()
        await m_status.delete()
        print(f"- START PLAYING: {playlist[0].audio.title}")
    await mp.send_playlist()
    for track in playlist[:2]:
        await download_audio(track)
    if not m.audio:
        await m.delete()


@Client.on_message(main_filter
                   & current_vc
                   & filters.regex("^(\\/|!)current$"))
async def show_current_playing_time(_, m: Message):
    start_time = mp.start_time
    playlist = mp.playlist
    if not start_time:
        reply = await m.reply_text(f"{emoji.PLAY_BUTTON} 获取不到呢..")
        await _delay_delete_messages((reply, m), DELETE_DELAY)
        return
    utcnow = datetime.utcnow().replace(microsecond=0)
    if mp.msg.get('current') is not None:
        await mp.msg['current'].delete()
    mp.msg['current'] = await playlist[0].reply_text(
        f"{emoji.PLAY_BUTTON}  {utcnow - start_time} / "
        f"{timedelta(seconds=playlist[0].audio.duration)}",
        disable_notification=True
    )
    await m.delete()


@Client.on_message(main_filter
                   & (self_or_contact_filter | current_vc)
                   & filters.regex("^(\\/|!)help$"))
async def show_help(_, m: Message):
    if mp.msg.get('help') is not None:
        await mp.msg['help'].delete()
    mp.msg['help'] = await m.reply_text(USERBOT_HELP, quote=False)
    await m.delete()


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.command("skip", prefixes="!"))
async def skip_track(_, m: Message):
    playlist = mp.playlist
    if len(m.command) == 1:
        await skip_current_playing()
    else:
        try:
            items = list(dict.fromkeys(m.command[1:]))
            items = [int(x) for x in items if x.isdigit()]
            items.sort(reverse=True)
            text = []
            for i in items:
                if 2 <= i <= (len(playlist) - 1):
                    audio = f"[{playlist[i].audio.title}]({playlist[i].link})"
                    playlist.pop(i)
                    text.append(f"{emoji.WASTEBASKET} {i}. **{audio}**")
                else:
                    text.append(f"{emoji.CROSS_MARK} {i}")
            reply = await m.reply_text(
                "\n".join(text),
                disable_web_page_preview=True
            )
            await mp.send_playlist()
        except (ValueError, TypeError):
            reply = await m.reply_text(f"{emoji.NO_ENTRY} 输错了！这个是让你这么用的吗",
                                       disable_web_page_preview=True)
        await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & filters.regex("^!join$"))
async def join_group_call(client, m: Message):
    group_call = mp.group_call
    if not group_call:
        mp.group_call = GroupCallFactory(client).get_file_group_call()
        mp.group_call.add_handler(network_status_changed_handler,
                                  GroupCallFileAction.NETWORK_STATUS_CHANGED)
        mp.group_call.add_handler(playout_ended_handler,
                                  GroupCallFileAction.PLAYOUT_ENDED)
        await mp.group_call.start(m.chat.id)
        await m.delete()
    if group_call and group_call.is_connected:
        await m.reply_text(f"{emoji.ROBOT} 已经加入一个了呢..")


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!leave$"))
async def leave_voice_chat(_, m: Message):
    group_call = mp.group_call
    mp.playlist.clear()
    group_call.input_filename = ''
    await group_call.stop()
    await m.delete()


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & filters.regex("^!vc$"))
async def list_voice_chat(client, m: Message):
    group_call = mp.group_call
    if group_call and group_call.is_connected:
        chat_id = int("-100" + str(group_call.full_chat.id))
        chat = await client.get_chat(chat_id)
        reply = await m.reply_text(
            f"{emoji.MUSICAL_NOTES} **已经加入这个（↓）语音聊天了**:\n"
            f"- **{chat.title}**"
        )
    else:
        reply = await m.reply_text(emoji.NO_ENTRY
                                   + "还没有加入语音聊天呢..")
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!stop$"))
async def stop_playing(_, m: Message):
    group_call = mp.group_call
    group_call.stop_playout()
    reply = await m.reply_text(f"{emoji.STOP_BUTTON} 已停止播放")
    await mp.update_start_time(reset=True)
    mp.playlist.clear()
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!replay$"))
async def restart_playing(_, m: Message):
    group_call = mp.group_call
    if not mp.playlist:
        return
    group_call.restart_playout()
    await mp.update_start_time()
    reply = await m.reply_text(
        f"{emoji.COUNTERCLOCKWISE_ARROWS_BUTTON}  "
        "正在开始从头播放.."
    )
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!pause"))
async def pause_playing(_, m: Message):
    mp.group_call.pause_playout()
    await mp.update_start_time(reset=True)
    reply = await m.reply_text(f"{emoji.PLAY_OR_PAUSE_BUTTON} 已暂停",
                               quote=False)
    mp.msg['pause'] = reply
    await m.delete()


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!resume"))
async def resume_playing(_, m: Message):
    mp.group_call.resume_playout()
    reply = await m.reply_text(f"{emoji.PLAY_OR_PAUSE_BUTTON} 继续播放",
                               quote=False)
    if mp.msg.get('pause') is not None:
        await mp.msg['pause'].delete()
    await m.delete()
    await _delay_delete_messages((reply,), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!clean$"))
async def clean_raw_pcm(client, m: Message):
    download_dir = os.path.join(client.workdir, DEFAULT_DOWNLOAD_DIR)
    all_fn: list[str] = os.listdir(download_dir)
    for track in mp.playlist[:2]:
        track_fn = f"{track.audio.file_unique_id}.raw"
        if track_fn in all_fn:
            all_fn.remove(track_fn)
    count = 0
    if all_fn:
        for fn in all_fn:
            if fn.endswith(".raw"):
                count += 1
                os.remove(os.path.join(download_dir, fn))
    reply = await m.reply_text(f"{emoji.WASTEBASKET} 清除了 {count} 个文件")
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!mute$"))
async def mute(_, m: Message):
    group_call = mp.group_call
    await group_call.set_is_mute(True)
    reply = await m.reply_text(f"{emoji.MUTED_SPEAKER} 已禁音")
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & self_or_contact_filter
                   & current_vc
                   & filters.regex("^!unmute$"))
async def unmute(_, m: Message):
    group_call = mp.group_call
    await group_call.set_is_mute(False)
    reply = await m.reply_text(f"{emoji.SPEAKER_MEDIUM_VOLUME} 已解除禁音")
    await _delay_delete_messages((reply, m), DELETE_DELAY)


@Client.on_message(main_filter
                   & current_vc
                   & filters.regex("^(\\/|!)repo$"))
async def show_repository(_, m: Message):
    if mp.msg.get('repo') is not None:
        await mp.msg['repo'].delete()
    mp.msg['repo'] = await m.reply_text(
        USERBOT_REPO,
        disable_web_page_preview=True,
        quote=False
    )
    await m.delete()


# - Other functions


async def send_text(text):
    group_call = mp.group_call
    client = group_call.client
    chat_id = mp.chat_id
    message = await client.send_message(
        chat_id,
        text,
        disable_web_page_preview=True,
        disable_notification=True
    )
    return message


async def skip_current_playing():
    group_call = mp.group_call
    playlist = mp.playlist
    if not playlist:
        return
    if len(playlist) == 1:
        await mp.update_start_time()
        return
    client = group_call.client
    download_dir = os.path.join(client.workdir, DEFAULT_DOWNLOAD_DIR)
    group_call.input_filename = os.path.join(
        download_dir,
        f"{playlist[1].audio.file_unique_id}.raw"
    )
    await mp.update_start_time()
    # remove old track from playlist
    old_track = playlist.pop(0)
    print(f"- START PLAYING: {playlist[0].audio.title}")
    await mp.send_playlist()
    os.remove(os.path.join(
        download_dir,
        f"{old_track.audio.file_unique_id}.raw")
    )
    if len(playlist) == 1:
        return
    await download_audio(playlist[1])


async def download_audio(m: Message):
    group_call = mp.group_call
    client = group_call.client
    raw_file = os.path.join(client.workdir, DEFAULT_DOWNLOAD_DIR,
                            f"{m.audio.file_unique_id}.raw")
    if not os.path.isfile(raw_file):
        original_file = await m.download()
        ffmpeg.input(original_file).output(
            raw_file,
            format='s16le',
            acodec='pcm_s16le',
            ac=2,
            ar='48k',
            loglevel='error'
        ).overwrite_output().run()
        os.remove(original_file)


async def _delay_delete_messages(messages: tuple, delay: int):
    await asyncio.sleep(delay)
    for m in messages:
        await m.delete()
