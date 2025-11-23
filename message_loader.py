# message_loader.py
import os
import json

# 專案根目錄：和 bot.py 在同一層
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 你的檔案路徑：love_reminder_bot/message/messages.json
MESSAGE_FILE = "./messages.json"

def load_messages():
    with open("messages.json", "r", encoding="utf-8") as f:
    # 處理訊息

        return json.load(f)



def load_messages():
    """
    讀取 messages.json
    回傳格式： { "YYYY-MM-DD": "當天要發的文字", ... }
    """
    if not os.path.exists(MESSAGE_FILE):
        print(f"[message_loader] 找不到訊息檔案：{MESSAGE_FILE}")
        return {}

    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages_by_date = {}
    for item in data:
        date = item.get("date")
        content = item.get("content")
        if date and content:
            messages_by_date[date] = content

    return messages_by_date
