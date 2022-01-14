# 电报语音聊天用户机器人

用于在语音聊天中播放音频的 Telegram UserBot。

这也是用于播放 [VC DJ/Live Sets](https://t.me/VCSets) 中的 DJ/Live Sets 音乐的 userbot 的源代码。

使用 [tgcalls](https://github.com/MarshalX/tgcalls) 和 [Pyrogram Smart Plugin](https://docs.pyrogram.org/topics/smart-plugins) 制作

建议将 [tgmusicbot](https://github.com/callsmusic/tgmusicbot) 与此用户机器人一起使用。

## 部署到 Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/callsmusic/tgvc-userbot/tree/dev)

- 会话字符串可以使用 Pyrogram 导出
   ```
   # pip install Pyrogram TgCrypto
   from pyrogram import Client

  api_id = 1234567
  api_hash = "0123456789abcdef0123456789abcdef"

  with Client(":memory:", api_id, api_hash) as app, open("session.txt", "w+") as s_file:
      session_string = app.export_session_string()
      s_file.write(session_string)
      print("Session string has been saved to session.txt")
      print(session_string)
   ```
- 将项目部署到 Heroku 后启用工作人员
- 从用户机器人帐户本身或其联系人发送“！加入”到启用语音聊天的群聊
- 使用 `/play` 回复音频以开始在语音聊天中播放，组中的每个成员
   现在可以使用 `!play` 和其他常用命令，查看 `!help` 了解更多命令

其他插件还有一些其他分支，
您也可以在此处按“部署到 Heroku”按钮来部署它。
## 介绍

**特色**

- 播放列表，队列
- 当播放列表中只有一首曲目时循环播放一首曲目
- 自动下载播放列表中前两首曲目的音频
   确保流畅播放
- 自动固定当前播放曲目
- 显示音频的当前播放位置

**播放插件怎么使用**

1. 启动机器人
2. 从用户机器人帐户本身发送`!join`到启用语音聊天的群聊
    或其联系人，请务必将机器人帐户设置为组管理员，并且
    至少给它以下权限：
- 删除消息
    - 管理语音聊天（可选）
3. 使用 `/play` 回复音频以开始在语音聊天中播放，每个
    群组成员现在可以使用常用命令，例如`/play`、`/current`和`!help`。
4. 查看 `!help` 获取更多命令
5. 
**命令**

主要插件是`vc.player`，它具有以下命令命令和管理命令。
启动机器人后，从 userbot 帐户发送 `!join` 到启用语音聊天的群聊
它自己或它的联系人，然后像`/play`和`/current`这样的常用命令将可用
给群内的每一位成员。发送 `!help` 以检查更多命令。

- 常用命令，可供当前语音聊天的群组成员使用
- 以 /（斜线）或 ! （感叹号）开始

| 常用命令 | 说明 |
|-----------------|------------------------------- --------------------------|
| /play | 回复音频以播放/queue，或显示播放列表 |
| /current | 显示当前曲目的当前播放时间 |
| /repo | 显示用户机器人的 git 存储库 |
| !help | 显示命令帮助 |

- 管理员命令，可供用户机器人帐户本身及其联系人使用
- 以!开始 （感叹号）

| 管理命令 | 说明 |
|----------------|-------------------------------- --|
| !skip [n] ... | 跳过当前或 n 其中 n >= 2 |
| !join | 加入当前群组的语音聊天 |
| !leave | 离开当前语音聊天 |
| !vc | 检查加入了哪个VC |
| !stop | 停止播放|
| !replay | 从头开始玩|
| !clean | 删除未使用的 RAW PCM 文件 |
| !pause | 暂停播放 |
| !resume | 继续播放|
| !mute | 使 VC 用户机器人静音 |
| !unmute | 取消静音 VC 用户机器人 |

- 来自其他插件的命令，仅对 userbot 帐户本身可用

| 插件 | 命令 | 说明 |
|---------|---------|---------|
| ping | !ping | 显示 ping 时间 |
| uptime | !uptime | 显示用户机器人正常运行时间 |
| sysinfo | !sysinfo | 显示系统信息 |

＃＃ 要求

- Python 3.6 或更高版本
- [Telegram API 密钥](https://docs.pyrogram.org/intro/quickstart#enjoy-the-api) 和 Telegram 帐户
- 选择你需要的插件，安装上面列出的依赖项并运行`pip install -U -r requirements.txt`来安装python包依赖项
- [FFmpeg](https://www.ffmpeg.org/)

＃＃ 运行

选择两种方法之一并运行用户机器人
`python3 userbot.py`，用 <kbd>CTRL+c</kbd> 停止。下面的例子
假设你要使用 `vc.player` 和 `ping` 插件，替换
`api_id`, `api_hash` 到你自己的值。

### 方法一：使用config.ini

创建一个`config.ini`文件

```
[pyrogram]
api_id = 1234567
api_hash = 0123456789abcdef0123456789abcdef

[plugins]
root = plugins
include =
    vc.player
    ping
    sysinfo
```

### 方法2：自己写一个userbot.py

替换`userbot.py`的文件内容

```
from pyrogram import Client, idle

api_id = 1234567
api_hash = "0123456789abcdef0123456789abcdef"

plugins = dict(
    root="plugins",
    include=[
        "vc.player",
        "ping"
    ]
)

app = Client("tgvc", api_id, api_hash, plugins=plugins)
app.start()
print('>>> 机器人已启动')
idle()
app.stop()
print('\n>>> 机器人已停止')
```

## 备注

- 阅读您将要使用的 [plugins/](plugins) 的模块文档字符串
  额外注释的文件开头

＃ 执照

AGPL-3.0 或更高版本
