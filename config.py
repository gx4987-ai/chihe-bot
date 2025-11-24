# config.py
import os
from zoneinfo import ZoneInfo

# Discord Bot Token（放在 Railway 的環境變數）
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 每日訊息要送出的頻道
DAILY_MESSAGE_CHANNEL_ID = 901501574105399396

# 時區設定（台灣）
TAIWAN_TZ = ZoneInfo("Asia/Taipei")

# 訊息檔案路徑
MESSAGE_JSON_PATH = "messages.json"

