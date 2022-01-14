# import logging
from pyrogram import Client, idle

app = Client("tgvc")
# logging.basicConfig(level=logging.INFO)
app.start()
print('>>> 机器人已启动')
idle()
app.stop()
print('\n>>> 机器人已关闭')
