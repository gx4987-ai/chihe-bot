# message_loader.py
import json
from config import MESSAGE_JSON_PATH

def load_messages():
    """讀取 messages.json，回傳列表"""
    with open(MESSAGE_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_message_by_day(day: int):
    """直接用 day（1～120）取出對應日記"""
    msgs = load_messages()
    index = (day - 1) % len(msgs)
    return msgs[index]
