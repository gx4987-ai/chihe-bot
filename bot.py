

import os
import re
import random

import json

from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional

import nextcord
from nextcord.ext import commands, tasks

from nextcord.ui import View, button
from nextcord import SlashOption


# ---- Intents / Bot ----
intents = nextcord.Intents.default()
intents.message_content = True  # 記得在 Developer Portal 開啟 MESSAGE CONTENT INTENT
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== 台北時區（一定要最前面） ======
TAIPEI_TZ = timezone(timedelta(hours=8))

# ====== 當兵專屬設定（你自己的日期） ======
SERVICE_START_DATE = datetime(2025, 12, 1, tzinfo=TAIPEI_TZ)
SERVICE_TOTAL_DAYS = 114
SERVICE_END_DATE = SERVICE_START_DATE + timedelta(days=SERVICE_TOTAL_DAYS - 1)
# =======================================

# ====== 載入 .env（如果有）======
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass



# Discord Token
TOKEN = os.getenv("DISCORD_TOKEN")


# ============================================

from datetime import datetime, timedelta, timezone

TAIWAN_TZ = timezone(timedelta(hours=8))

def is_night_mode():
    now = datetime.now(TAIWAN_TZ)
    return (now.hour >= 23 or now.hour < 3)


# ====== 頻道設定 ======
# 每日固定訊息要發的頻道
DAILY_CHANNEL_ID = 901501574105399396
# 主要聊天頻道
CHAT_CHANNEL_ID = 1387689795148582912
# ======================

NIGHT_MODE_REPLIES = {
    "tired": [
        "…你這語氣，感覺是真的累到心裡去了，你先躺一下，什麼都先別想那麼多( ",
        "深夜的累會比白天放大很多倍，你不用撐著裝沒事，在這邊軟一下也可以( ",
        "嗯…我聽得出來你今天真的過得不太輕鬆，你可以慢慢跟我說到你想停為止就好( "
    ],
    "neutral": [
        "嗯，我在。這個時間如果你還醒著，多少都有一點事放不下對吧( ",
        "這個時間點你還醒著，有點不像平常的你，所以我會多留意你一點( ",
        "深夜的時候講話會不自覺變真，你想講什麼就慢慢丟過來就好( "
    ],
    "comfort": [
        "你先不要急著把情緒整理乾淨，深夜本來就容易把感覺放大，我可以先幫你接著一點( ",
        "我在，你可以邊亂講邊理一下自己的心情，不用一次想清楚，我會跟著你一起聽( ",
        "這種時間點還醒著的人…心裡多少都有東西，我不會逼你講，但你想講的時候我會在( "
    ]
}



# ====== 進階情緒偵測設定（簡易版，不用 GPT） ======
NEGATIVE_KEYWORDS = [
    "好累", "超累", "好煩", "壓力好大", "壓力爆炸",
    "好想哭", "想哭", "心好累", "不想活", "不想面對",
    "好難過", "低落", "好沮喪", "好崩潰",
]

# 情緒安慰的隨機句子池（千惠語氣）
EMOTION_RESPONSES = [
    "你這樣講的時候，感覺真的有點撐過頭了…我在，你可以慢慢說，不用一次把所有事講完( ",
    "情緒卡住的時候不要勉強自己，把狀態說出來本身就已經很不容易了，我有認真在聽( ",
    "今天如果過得不太順，也還好吧，你至少願意講出來，代表你還沒放棄自己( ",
    "先讓自己慢下來一點，你不用急著想答案，我先在這裡陪你一下就好( ",
    "你這樣講，感覺你心裡已經累一陣子了…你想從哪個地方開始說？( ",
    "有這種感覺其實不奇怪，反而代表你還在認真面對生活，如果你願意，我可以跟你一起慢慢整理( ",
    "如果今天過得很糟，也沒關係，你能撐到現在就已經很了不起了，接下來可以讓自己鬆一點( ",
    "先深呼吸幾次，讓心跟身體都鬆一點，再決定要不要繼續講，我不會催你( ",
]


# 同一個人情緒回覆的冷卻（秒）避免 bot 太黏人
EMOTION_COOLDOWN_PER_USER = 300  # 5 分鐘
LAST_EMOTION_REPLY_TIME: Dict[int, float] = {}  # {user_id: timestamp}
# ==========================================================


def detect_negative_emotion(text: str) -> bool:
    """簡單檢查句子裡有沒有負面關鍵詞"""
    lower = text.lower()
    return any(kw.lower() in lower for kw in NEGATIVE_KEYWORDS)




async def try_greeting_reply(message: nextcord.Message):
    """處理早安/午安/晚安的安靜冷卻模式"""
    global greeting_last_trigger

    now = time.time()
    content = message.content

    # --- 早安 ---
    if any(word in content for word in GOOD_MORNING_WORDS):
        if now - greeting_last_trigger["morning"] >= GREETING_COOLDOWN:
            greeting_last_trigger["morning"] = now
            await message.reply("早安，你今天還好吧( ")
        return  # 冷卻中 → 完全安靜，不回覆

    # --- 午安 ---
    if any(word in content for word in GOOD_AFTERNOON_WORDS):
        if now - greeting_last_trigger["noon"] >= GREETING_COOLDOWN:
            greeting_last_trigger["noon"] = now
            await message.reply("午安，記得稍微休息一下( ")
        return

    # --- 晚安 ---
    if any(word in content for word in GOOD_NIGHT_WORDS):
        if now - greeting_last_trigger["night"] >= GREETING_COOLDOWN:
            greeting_last_trigger["night"] = now
            await message.reply("晚安，好好睡一下會比較舒服( ")
        return


EMOTION_KEYWORD_REPLIES: Dict[str, str] = {
    "好累": "聽起來是真的有點撐太久了，你要不要先停一下喘口氣，再慢慢跟我講發生什麼事( ",
    "好煩": "那種煩到心裡悶住的感覺，我大概猜得到一點…你想講講看嗎( ",
    "壓力好大": "確實有時候壓力會一下子全部壓上來，你不用馬上把一切處理好，先讓自己穩住比較重要( ",
    "不想動": "還好吧，不想動的時候通常是真的累了，你可以先放著不管一下，等身體比較願意再說也沒關係( ",
    "抱抱": "今天也撐到現在了，你可以不用那麼硬撐，過來這邊一下(抱 ",
    "不想念書": "不想念的時候硬坐在書桌前也進不去，不然你先離開一下，等腦袋沒那麼吵再回來也可以( ",
    "逆天": "逆天",
    "大逆天": "大逆天",
    "草": "草",
    "大草": "大草",
    "開心": "那是肯定的，你開心的話我也會比較放心一點( ",
    "拆家": "能不能別拆了天( ",
}




# 冷卻秒數：所有人共用某個關鍵字的冷卻
KEYWORD_COOLDOWN = 150  # 你原本設定的 150 秒

# 每個人收到「冷卻提示」的最小間隔（避免提示也洗版）
HINT_COOLDOWN_PER_USER = 30  # 你原本設定

# 反洗版設定：同一個人同一個關鍵字在冷卻中被提示超過 N 次，就封印一段時間
ABUSE_MAX_HINTS = 1        # 你原本設定
ABUSE_MUTE_SECONDS = 300   # 封印 5 分鐘

# 記錄狀態用的 dict
LAST_REPLY_TIME: Dict[str, float] = {}              # {keyword: timestamp}
LAST_HINT_TIME: Dict[Tuple[str, int], float] = {}   # {(keyword, user_id): timestamp}
MUTE_UNTIL: Dict[Tuple[str, int], float] = {}       # {(keyword, user_id): timestamp}
ABUSE_HINT_COUNT: Dict[Tuple[str, int], int] = {}   # {(keyword, user_id): int}
# ================================

# ====== 每日訊息紀錄（避免重啟後重複發送） ======
LAST_SENT_FILE = "last_sent_date.txt"  # 存在專案資料夾中的小檔案
LAST_SENT_DATE: Optional[str] = None   # 會存 "YYYY-MM-DD"

# ===== 遠征系統設定 =====
BOSS_MAX_HP = 999_999_999_999
boss_current_hp = BOSS_MAX_HP

# 廣域 CD（整個伺服器共用）
EXPEDITION_GLOBAL_COOLDOWN = 180  # 3 分鐘
LAST_EXPEDITION_TIME: float = 0.0  # 上一次任何人使用遠征的時間戳

# 個人 CD（每個人自己的節奏，避免同一個人狂刷）
EXPEDITION_USER_COOLDOWN = 180  # 180 秒，可以自己改
LAST_EXPEDITION_TIME_USER: Dict[int, float] = {}  # {user_id: timestamp}

# 使用者累計傷害統計表 {user_id: total_damage}
USER_DAMAGE_TOTAL: Dict[int, int] = {}

# ====== 真心話大冒險 & 故事接龍 狀態 ======
# 以頻道為單位管理

# 真心話大冒險：{channel_id: set(user_id)}
TOD_PLAYERS: Dict[int, set[int]] = {}

# 故事接龍：
# - STORY_PLAYERS: {channel_id: [user_id1, user_id2, ...]} 固定順序
# - STORY_SENTENCES: {channel_id: {user_id: sentence}}
# - STORY_CURRENT_INDEX: {channel_id: int} 目前輪到第幾個玩家（索引）
STORY_PLAYERS: Dict[int, list[int]] = {}
STORY_SENTENCES: Dict[int, Dict[int, str]] = {}
STORY_CURRENT_INDEX: Dict[int, int] = {}


# ============================================
# 千惠模組包：記憶系統 / 生活化數據 / 反應包 / 早午晚安安靜冷卻 / 每日任務
# ============================================

# ---------- 1. 千惠記憶系統（輕量 JSON） ----------

MEMORY_FILE = "chihye_memory.json"
MEMORY: Dict[str, dict] = {}  # 結構：{"users": {"user_id_str": {"notes": [...], "updated_at": "..."} }}


def load_memory() -> None:
    """啟動時讀取記憶檔，讀不到就用空的。"""
    global MEMORY
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            MEMORY = json.load(f)
            if "users" not in MEMORY:
                MEMORY["users"] = {}
    except (FileNotFoundError, json.JSONDecodeError):
        MEMORY = {"users": {}}


def save_memory() -> None:
    """寫回記憶檔。"""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(MEMORY, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save_memory error:", e)


def add_user_note(user_id: int, note: str) -> None:
    """幫某個人多記一則小語錄 / 心情 / 喜歡的東西。"""
    if not note:
        return
    uid = str(user_id)
    users = MEMORY.setdefault("users", {})
    user_mem = users.setdefault(uid, {})
    notes = user_mem.setdefault("notes", [])
    notes.append(note.strip())
    # 最多留 20 則，太久以前的就丟掉
    if len(notes) > 20:
        notes.pop(0)
    user_mem["updated_at"] = datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    save_memory()


def get_user_notes(user_id: int):
    uid = str(user_id)
    return MEMORY.get("users", {}).get(uid, {}).get("notes", [])


# ---------- 2. 生活化「伺服器小報告」統計 ----------

USER_MESSAGE_COUNT: Dict[int, int] = {}         # 每個人總訊息數
USER_NIGHT_MESSAGE_COUNT: Dict[int, int] = {}   # 每個人深夜訊息數
CHANNEL_MESSAGE_COUNT: Dict[int, int] = {}      # 每個頻道訊息數


def update_message_stats(message: nextcord.Message) -> None:
    """在 on_message 裡每次呼叫，更新生活化統計。"""
    uid = message.author.id
    chid = message.channel.id

    USER_MESSAGE_COUNT[uid] = USER_MESSAGE_COUNT.get(uid, 0) + 1
    CHANNEL_MESSAGE_COUNT[chid] = CHANNEL_MESSAGE_COUNT.get(chid, 0) + 1

    if is_night_mode():
        USER_NIGHT_MESSAGE_COUNT[uid] = USER_NIGHT_MESSAGE_COUNT.get(uid, 0) + 1


@bot.command(name="小報告")
async def life_report(ctx: commands.Context):
    """千惠的伺服器生活化小報告。"""
    if not USER_MESSAGE_COUNT:
        await ctx.send("我這邊的觀察紀錄還太少，再陪我聊久一點，我再跟你們報告( ")
        return

    # Top talker
    top_talkers = sorted(
        USER_MESSAGE_COUNT.items(), key=lambda x: x[1], reverse=True
    )[:5]

    # 深夜 Top
    top_night = sorted(
        USER_NIGHT_MESSAGE_COUNT.items(), key=lambda x: x[1], reverse=True
    )[:3]

    # 頻道最吵
    top_channels = sorted(
        CHANNEL_MESSAGE_COUNT.items(), key=lambda x: x[1], reverse=True
    )[:3]

    embed = nextcord.Embed(
        title="📝 千惠的小報告",
        description="我這陣子偷看的觀察紀錄( ",
        color=0xF5B642,
    )

    if top_talkers:
        lines = []
        for i, (uid, cnt) in enumerate(top_talkers, start=1):
            lines.append(f"{i}. <@{uid}>：**{cnt}** 則訊息")
        embed.add_field(name="說話最多的人", value="\n".join(lines), inline=False)

    if top_night:
        lines = []
        for i, (uid, cnt) in enumerate(top_night, start=1):
            lines.append(f"{i}. <@{uid}>：**{cnt}** 則深夜訊息")
        embed.add_field(name="深夜還不睡的人", value="\n".join(lines), inline=False)

    if top_channels:
        lines = []
        for i, (chid, cnt) in enumerate(top_channels, start=1):
            lines.append(f"{i}. <#{chid}>：**{cnt}** 則訊息")
        embed.add_field(name="最吵的地方", value="\n".join(lines), inline=False)

    await ctx.send(embed=embed)


# ---------- 3. 千惠可愛反應包（輕量版） ----------

REACTION_TRIGGERS = {
    "我回來": [
        "嗯，歡迎回來( ",
        "你回來了喔，那就先在這裡坐一下吧( ",
    ],
    "好無聊": [
        "那要不要玩點什麼？我這邊有一些奇怪的遊戲可以試試看( ",
        "無聊到跑來找我，其實我有一點開心( ",
    ],
    "肚子餓": [
        "那就先去吃東西，聊天可以等，肚子不能等( ",
        "餓著的時候什麼都會變得更煩，先填飽肚子再說( ",
    ],
    "我好冷": [
        "那你多穿一點，或者縮在被子裡，手機可以拿遠一點沒關係( ",
        "冷的時候會特別想有人在旁邊，我暫時先算半個( ",
    ],
}

REACTION_COOLDOWN_PER_USER = 60  # 秒，避免一個人一直觸發
REACTION_LAST_TIME: Dict[int, float] = {}


async def handle_reaction_reply(message: nextcord.Message, now_ts: float) -> bool:
    """可愛反應包：簡單掃關鍵詞，偶爾回一句。回傳是否有回覆。"""
    # 只在主要聊天頻道開啟
    if message.channel.id not in (CHAT_CHANNEL_ID, DAILY_CHANNEL_ID):
        return False

    uid = message.author.id
    text = message.content

    # 簡單防洗：每人 60 秒一次
    last = REACTION_LAST_TIME.get(uid, 0.0)
    if now_ts - last < REACTION_COOLDOWN_PER_USER:
        return False

    for kw, replies in REACTION_TRIGGERS.items():
        if kw in text:
            reply = random.choice(replies)
            # 深夜稍微柔一點
            if is_night_mode():
                reply = reply.replace("？", "…？")
            await message.channel.send(f"{message.author.mention} {reply}")
            REACTION_LAST_TIME[uid] = now_ts
            return True

    return False


# ---------- 4. 早安 / 午安 / 晚安：2 小時安靜冷卻 ----------

GREETING_COOLDOWN = 7200  # 2 小時
GREETING_LAST_TIME: Dict[str, float] = {
    "早安": 0.0,
    "午安": 0.0,
    "晚安": 0.0,
}


async def handle_greeting_if_any(message: nextcord.Message) -> bool:
    """
    專門處理早安/午安/晚安：
    - 第一個人觸發 → 正常回覆
    - 之後 2 小時內 → 完全安靜，不回覆、不提示冷卻
    回傳：有沒有真的回覆。
    """
    content = message.content
    now_ts = datetime.now().timestamp()

    for kw, base_reply in EMOTION_KEYWORD_REPLIES.items():
        if is_keyword_triggered(kw, content):
            last_ts = GREETING_LAST_TIME.get(kw, 0.0)
            if now_ts - last_ts >= GREETING_COOLDOWN:
                reply_text = base_reply
                # 深夜版語氣
                if is_night_mode():
                    reply_text = random.choice(NIGHT_MODE_REPLIES["neutral"])
                await message.channel.send(f"{message.author.mention} {reply_text}")
                GREETING_LAST_TIME[kw] = now_ts
                return True
            else:
                # 在冷卻中 → 什麼都不說
                return False
    return False


# ---------- 5. 每日任務（今日小任務） ----------

DAILY_MISSIONS = [
    "今天找一個時間，認真喝完一整杯水。",
    "刻意對某個人說一句『謝謝』，哪怕只是很小的事。",
    "允許自己發呆三分鐘，什麼都不做也可以。",
    "把手機放下五分鐘，只聽一下周圍的聲音。",
    "跟一個人說『辛苦了』，不一定要解釋原因。",
    "睡前對自己說一句『今天這樣就夠了』。",
]


def get_mission_for_today() -> str:
    today_str = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    # 用日期字串做一個穩定的 index，避免每天重啟任務亂跳
    idx = sum(ord(c) for c in today_str) % len(DAILY_MISSIONS)
    return DAILY_MISSIONS[idx]


@bot.command(name="mission", aliases=["今日任務", "任務"])
async def mission_cmd(ctx: commands.Context):
    m = get_mission_for_today()
    await ctx.send(f"{ctx.author.mention} 今天的任務是：{m}")


# ---------- 6. 記錄小語錄的指令 ----------

@bot.command(name="記錄", aliases=["記一下", "記", "紀錄"])
async def remember_cmd(ctx: commands.Context, *, text: str):
    """幫你把一句話記起來，之後可以用 !語錄 看。"""
    add_user_note(ctx.author.id, text)
    await ctx.send(f"{ctx.author.mention} 好，我記得了( ")


@bot.command(name="語錄", aliases=["小語錄"])
async def show_notes_cmd(ctx: commands.Context):
    """顯示你自己記錄過的幾句話。"""
    notes = get_user_notes(ctx.author.id)
    if not notes:
        await ctx.send(f"{ctx.author.mention} 你目前還沒有跟我說要記住什麼東西( ")
        return

    # 只顯示最後 5 則
    last_notes = notes[-5:]
    lines = [f"{i}. {t}" for i, t in enumerate(last_notes, start=1)]
    await ctx.send(
        f"{ctx.author.mention} 這是我記得、跟你有關的幾句話：\n" + "\n".join(lines)
    )


# 啟動時就先把記憶載進來
load_memory()



def get_expedition_comment(damage: int) -> str:
    """
    根據這次的傷害，給一句千惠式旁白。
    混合版：
    - 很低傷害：特別嘴一點
    - 中間區間：微壞、偏溫和
    - 接近爆擊：有點像在檢查你最近是不是壓力太大
    """

    # 超級低傷害：0～10，特別嘴
    if damage <= 10:
        pool = [
            "這一下…老實說可能我真的沒感覺，你是來暖場的嗎( ",
            "我開始懷疑你是不是忘了拔安全鎖，這數字有點太溫柔了( ",
            "如果只看這傷害，我會以為你只是在做瑜珈輕拍按摩( ",
            "如果不看戰鬥紀錄，我會以為你只是揮到自己影子而已( ",
        ]

    # 非常低但至少看得懂是攻擊：11～49
    elif damage < 50:
        pool = [
            "這一下大概是提醒我世界上還有人存在的程度而已( ",
            "蚊子如果認真一點，可能還會比這更痛一點( ",
            "勉強可以算是有在揮，但戰鬥紀錄看起來滿像意外按到的( ",
        ]

    # 小力區：50～199
    elif damage < 200:
        pool = [
            "有打到，不過比較像在幫我把灰塵拍掉，還沒進入戰鬥狀態( ",
            "這數字…好啦，至少證明你真的有在線，而不是純聊天( ",
            "算是輕輕敲牆壁示意『我在這裡』的那種力度( ",
            "算是輕輕敲了一下桌面，吵不到我睡覺那種級別( ",
        ]

    # 微妙區：200～499
    elif damage < 500:
        pool = [
            "這力度勉強可以叫一刀，我可能只會覺得哪裡有點癢( ",
            "這傷害或許還可以，不過應該還不足以讓我記住你是誰( ",
            "有認真揮了，只是目前還在暖身環節，正式開打應該不只這樣吧( ",
            "這種傷害…如果當作熱身，其實還算合理( ",
        ]

    # 還行區：500～999
    elif damage < 1000:
        pool = [
            "這傷害還行，至少不會被誤會成是系統判定誤差( ",
            "我看到這個數字，大概會抬頭看你一眼，然後繼續做原本的事( ",
            "好歹可以稱作一個完整的攻擊了，再上去一點就有存在感了( ",
        ]

    # 中等輸出：1000～2999
    elif damage < 3000:
        pool = [
            "這一下總算有點認真了，我應該會開始記得你是有在打的那種人( ",
            "以這個數字來說，再穩定幾次，我可能會開始後悔沒早點處理你( ",
            "這種傷害如果持續輸出，久了真的會讓我覺得人生有點累，雖然我本來就很累了( ",
        ]

    # 中高輸出：3000～5999
    elif damage < 6000:
        pool = [
            "這傷害有點兇，我之後回想今天大概會想到你這一刀( ",
            "這一發已經完全脫離娛樂區了，正式進入『會痛』的範圍( ",
            "以這個程度來說，你再多揮幾次我大概會開始本能往後退( ",
        ]

    # 高輸出：6000～8999
    elif damage < 9000:
        pool = [
            "這一刀很實在，我現在應該會把你列進優先處理名單裡( ",
            "這數字看起來就不像在玩，我認真記一下你的 ID( ",
            "這樣打幾次，我可能會開始懷疑是不是哪裡設定錯誤才讓你長這樣( ",
            "這數字根本就不是辦家家酒呢，我應該會認真開始考慮防守你這方向( ",
        ]

  

    # 接近滿傷害：9000～10000，精神狀況關心版
    else:
        pool = [
            "這數字看起來像是在拿 Boss 出氣，你最近是不是壓力有點大( ",
            "這一發有點像是把好幾天的情緒一起丟進去，你要不要順便講講最近怎樣( ",
            "這傷害很漂亮沒錯，只是…你這樣揮，我會稍微擔心你是不是需要休息一下( ",
        ]

    return random.choice(pool)
# =======================


def load_last_sent_date() -> None:
    """啟動時從檔案讀取上次已發訊息的日期（如果有）"""
    global LAST_SENT_DATE
    try:
        with open(LAST_SENT_FILE, "r", encoding="utf-8") as f:
            date_str = f.read().strip()
            if date_str:
                LAST_SENT_DATE = date_str
    except FileNotFoundError:
        LAST_SENT_DATE = None


def save_last_sent_date(date_str: str) -> None:
    """送出當日訊息後，寫入檔案，避免之後重啟重複發"""
    with open(LAST_SENT_FILE, "w", encoding="utf-8") as f:
        f.write(date_str)
# ==================================================


def get_today_message() -> Optional[str]:
    """從 messages.txt 讀取今天要發的文字（比對 YYYY-MM-DD 開頭）"""
    today_str = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    try:
        with open("messages.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if " " in line:
                    date_str, text = line.split(" ", 1)
                    if date_str == today_str:
                        return text
        return None
    except FileNotFoundError:
        return None


def is_keyword_triggered(keyword: str, text: str) -> bool:
    """
    只在「訊息開頭」是關鍵字時觸發，例如：
    早安
    早安～
    早安 大家
    不會對「大家早安」「昨天忘了說早安」觸發
    """
    text = text.strip().lower()
    kw = keyword.lower()
    pattern = rf"^{re.escape(kw)}($|\s|[!！?.。～,，…]+)"
    return re.match(pattern, text) is not None


@bot.event
async def on_ready():
    print(f"✅ 已登入：{bot.user} (ID: {bot.user.id})")
    if not send_daily_message.is_running():
        send_daily_message.start()


@bot.event
async def on_message(message: nextcord.Message):
    if message.author.bot:
        return

    global LAST_REPLY_TIME, LAST_HINT_TIME, MUTE_UNTIL, ABUSE_HINT_COUNT, LAST_EMOTION_REPLY_TIME

    content = message.content
    now_ts = datetime.now().timestamp()

    # 生活化統計（小報告用）
    update_message_stats(message)

    responded = False  # 這次訊息 bot 有沒有已經回覆過

    # ✅ 在「每日頻道 + 聊天頻道」啟用這些互動功能
    if message.channel.id in (CHAT_CHANNEL_ID, DAILY_CHANNEL_ID):

        # 1) 先處理早安/午安/晚安（2 小時安靜冷卻，不會出現冷卻提示）
        if await handle_greeting_if_any(message):
            responded = True

        # 2) 其他情緒關鍵字（好累、抱抱、草…），沿用你原本的冷卻 + 反洗版邏輯
        if not responded:
            for keyword, reply_text in EMOTION_KEYWORD_REPLIES.items():
                if is_keyword_triggered(keyword, content):
                    user_key = (keyword, message.author.id)

                    # 🌙 深夜模式：先根據關鍵字換成深夜版語氣
                    if is_night_mode():
                        if keyword in ["好累", "好煩", "壓力好大", "不想動", "不想念書"]:
                            reply_text = random.choice(NIGHT_MODE_REPLIES["tired"])

                    # 1️⃣ 看這個人有沒有被封印
                    mute_until = MUTE_UNTIL.get(user_key, 0)
                    if now_ts < mute_until:
                        break

                    # 2️⃣ 檢查這個關鍵字的全局冷卻
                    last_time = LAST_REPLY_TIME.get(keyword, 0)
                    elapsed = now_ts - last_time

                    if elapsed < KEYWORD_COOLDOWN:
                        last_hint = LAST_HINT_TIME.get(user_key, 0)
                        if now_ts - last_hint >= HINT_COOLDOWN_PER_USER:
                            LAST_HINT_TIME[user_key] = now_ts

                            count = ABUSE_HINT_COUNT.get(user_key, 0) + 1
                            ABUSE_HINT_COUNT[user_key] = count

                            if count < ABUSE_MAX_HINTS:
                                remain = int(KEYWORD_COOLDOWN - elapsed)
                                await message.channel.send(
                                    f"{message.author.mention} 這個關鍵字還在冷卻中，大概 {remain} 秒之後再試比較好( "
                                )
                            else:
                                MUTE_UNTIL[user_key] = now_ts + ABUSE_MUTE_SECONDS
                                await message.channel.send(
                                    f"{message.author.mention} 你這樣有點太頻繁了，不然先停一下吧( "
                                )
                        break

                    # 3️⃣ 不在冷卻 → 正常回覆
                    await message.channel.send(f"{message.author.mention} {reply_text}")
                    LAST_REPLY_TIME[keyword] = now_ts
                    ABUSE_HINT_COUNT[user_key] = 0
                    responded = True
                    break

        # 3) 進階情緒偵測：只有在「還沒因為關鍵字回覆」時才啟動
        if (not responded) and detect_negative_emotion(content):
            last_emote = LAST_EMOTION_REPLY_TIME.get(message.author.id, 0)
            if now_ts - last_emote >= EMOTION_COOLDOWN_PER_USER:
                if is_night_mode():
                    reply = random.choice(NIGHT_MODE_REPLIES["comfort"])
                else:
                    reply = random.choice(EMOTION_RESPONSES)

                # 如果這個人有自己記錄過小語錄，就順便提一下
                notes = get_user_notes(message.author.id)
                extra = ""
                if notes:
                    last_note = notes[-1]
                    extra = f"\n還記得你之前跟我說過：「{last_note}」"

                await message.channel.send(f"{message.author.mention} {reply}{extra}")
                LAST_EMOTION_REPLY_TIME[message.author.id] = now_ts
                responded = True

        # 4) 可愛反應包（如果前面都沒回覆，就試試看）
        if not responded:
            reacted = await handle_reaction_reply(message, now_ts)
            if reacted:
                responded = True

    # 讓其他指令（!xxx）正常運作
    await bot.process_commands(message)




@bot.command(name="遠征")
async def expedition(ctx: commands.Context, *, skill: str = None):
    """
    遠征指令：!遠征 / !遠征 技能名字
    - 廣域 CD：全伺服器共用
    - 個人 CD：每個人自己的冷卻
    - 傷害隨機 1～10000，並記錄累計傷害
    - 在冷卻中使用會：刪掉訊息 + 私訊剩餘秒數
    """
    global boss_current_hp, LAST_EXPEDITION_TIME, LAST_EXPEDITION_TIME_USER, USER_DAMAGE_TOTAL

    now = datetime.now().timestamp()
    user_id = ctx.author.id

    # ---- 冷卻檢查：廣域 + 個人 ----
    global_elapsed = now - LAST_EXPEDITION_TIME
    user_last = LAST_EXPEDITION_TIME_USER.get(user_id, 0.0)
    user_elapsed = now - user_last

    global_remain = EXPEDITION_GLOBAL_COOLDOWN - global_elapsed
    user_remain = EXPEDITION_USER_COOLDOWN - user_elapsed

    # 只要有一個還在冷卻，就算無效攻擊
    if global_remain > 0 or user_remain > 0:
        # 要提醒的秒數取「兩者裡剩比較久的那一個」
        remain = int(max(global_remain, user_remain, 0))

        # 1) 刪掉頻道裡的那則指令訊息（避免洗版）
        try:
            await ctx.message.delete()
        except nextcord.Forbidden:
            pass
        except nextcord.HTTPException:
            pass

        # 2) 私訊告訴他還要等多久
        try:
            if remain < 1:
                remain = 1
            await ctx.author.send(f"遠征還在冷卻中，大概 **{remain}** 秒之後才能再攻擊( ")
        except nextcord.Forbidden:
            # 對方關閉私訊就算了，不額外處理
            pass

        return  # 冷卻中就不繼續往下執行

    # ---- 通過冷卻檢查，正式攻擊 ----
    LAST_EXPEDITION_TIME = now
    LAST_EXPEDITION_TIME_USER[user_id] = now

    damage = random.randint(1, 10000)
    boss_current_hp = max(0, boss_current_hp - damage)

    # 累計傷害記錄
    USER_DAMAGE_TOTAL[user_id] = USER_DAMAGE_TOTAL.get(user_id, 0) + damage

    # 技能文字
    if skill:
        skill_text = f"「{skill}」"
    else:
        skill_text = "隨手揮了一下"

    # 千惠式旁白（只看傷害）
    comment = get_expedition_comment(damage)

    # 組合訊息：
    msg = (
        f"{ctx.author.mention} {skill_text}，"
        f"對 Boss 造成了 **{damage}** 點傷害，"
        f"Boss 剩餘 **{boss_current_hp} / {BOSS_MAX_HP}** HP，"
        f"{comment}"
    )

    await ctx.send(msg)

@bot.command(name="遠征排行")
async def expedition_rank(ctx: commands.Context):
    """
    查看遠征傷害排行（Top 10，如果自己不在 Top 10，會另外顯示自己的名次）
    """
    if not USER_DAMAGE_TOTAL:
        await ctx.send("目前還沒有任何人造成傷害( ")
        return

    # 排行：照傷害高到低
    ranking = sorted(USER_DAMAGE_TOTAL.items(), key=lambda x: x[1], reverse=True)

    embed = nextcord.Embed(
        title="《遠征傷害排行》",
        description="前 10 名的累積輸出狀況",
        color=0xF5B642,
    )

    lines = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, (user_id, dmg) in enumerate(ranking[:10], start=1):
        medal = medals.get(i, f"{i}.")
        mention = f"<@{user_id}>"
        lines.append(f"{medal} {mention}：**{dmg}** 點")

    embed.add_field(
        name="Top 10",
        value="\n".join(lines),
        inline=False,
    )

    # 如果自己不在 Top 10，額外顯示自己的名次
    user_ids_ordered = [uid for uid, _ in ranking]
    if ctx.author.id in user_ids_ordered:
        self_rank = user_ids_ordered.index(ctx.author.id) + 1
        self_total = USER_DAMAGE_TOTAL.get(ctx.author.id, 0)

        if self_rank > 10:
            embed.add_field(
                name="你的位置",
                value=f"你目前是第 **{self_rank}** 名，累積 **{self_total}** 點傷害( ",
                inline=False,
            )
        else:
            # 在 Top 10 裡就用 footer 提醒一下
            embed.set_footer(
                text=f"你目前在前 10 名裡，第 {self_rank} 名，累積 {self_total} 點傷害( "
            )

    await ctx.send(embed=embed)


class TodView(View):
    """真心話大冒險控制台用的按鈕 View"""

    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @button(label="加入遊戲", style=nextcord.ButtonStyle.blurple)
    async def join_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = TOD_PLAYERS.setdefault(channel_id, set())

        if interaction.user.id in players:
            await interaction.response.send_message("你已經在這輪名單裡了( ", ephemeral=True)
        else:
            players.add(interaction.user.id)
            await interaction.response.send_message("我幫你加進真心話大冒險了( ", ephemeral=True)

    @button(label="退出遊戲", style=nextcord.ButtonStyle.gray)
    async def leave_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = TOD_PLAYERS.setdefault(channel_id, set())

        if interaction.user.id in players:
            players.remove(interaction.user.id)
            await interaction.response.send_message("好，我先把你從這輪名單裡拿掉( ", ephemeral=True)
        else:
            await interaction.response.send_message("你本來就不在這輪名單裡( ", ephemeral=True)

    @button(label="查看玩家", style=nextcord.ButtonStyle.gray)
    async def list_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = TOD_PLAYERS.get(channel_id, set())

        if not players:
            await interaction.response.send_message("目前還沒有人加入這輪真心話大冒險( ", ephemeral=True)
            return

        mentions = [f"<@{uid}>" for uid in players]
        text = "這一輪的玩家：\n" + "\n".join(mentions)
        await interaction.response.send_message(text, ephemeral=True)

    @button(label="下一回合", style=nextcord.ButtonStyle.green)
    async def next_round_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = TOD_PLAYERS.get(channel_id, set())

        # 只有「有加入的玩家」可以按
        if interaction.user.id not in players:
            await interaction.response.send_message("你目前沒有加入這輪，不能幫大家抽下一回合( ", ephemeral=True)
            return

        if len(players) < 2:
            await interaction.response.send_message("至少要兩個人加入才有辦法抽出題者跟被懲罰者( ", ephemeral=True)
            return

        player_list = list(players)
        questioner = random.choice(player_list)

        # 被懲罰者不能跟出題者同一個人
        possible_targets = [uid for uid in player_list if uid != questioner]
        target = random.choice(possible_targets)

        embed = nextcord.Embed(
            title="🎲 真心話大冒險 - 本回合結果",
            color=0x57F287,  # 綠色系
        )
        embed.add_field(name="出題者", value=f"<@{questioner}>", inline=True)
        embed.add_field(name="被懲罰者", value=f"<@{target}>", inline=True)
        embed.set_footer(text="出題者可以決定是真心話還是大冒險( ")

        # 公開公告在頻道裡
        await interaction.response.send_message(embed=embed)


@bot.command(name="tod", aliases=["真心話大冒險"])
async def truth_or_dare(ctx: commands.Context):
    """
    真心話大冒險控制台：
    - 按鈕加入/退出
    - 查看目前玩家
    - 下一回合：隨機抽出題者與被懲罰者
    """
    channel_id = ctx.channel.id
    # 每次開一個新的控制台時，不會清掉舊玩家，方便連續玩
    TOD_PLAYERS.setdefault(channel_id, set())

    embed = nextcord.Embed(
        title="🎲 真心話大冒險 控制台",
        description=(
            "・按「加入遊戲」就會被加進這一輪名單\n"
            "・按「退出遊戲」可以先離開\n"
            "・按「查看玩家」可以看到目前名單\n"
            "・只有有加入的人可以按「下一回合」\n\n"
            "按下「下一回合」後，會從名單裡抽一個出題者，"
            "再抽一個被懲罰者，並在頻道公告結果( "
        ),
        color=0xF5B642,
    )

    view = TodView(channel_id=channel_id)
    await ctx.send(embed=embed, view=view)


class StoryView(View):
    """故事接龍控制台用的按鈕 View"""

    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @button(label="加入故事", style=nextcord.ButtonStyle.blurple)
    async def join_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = STORY_PLAYERS.setdefault(channel_id, [])

        if interaction.user.id in players:
            await interaction.response.send_message("你已經在這輪故事接龍名單裡了( ", ephemeral=True)
            return

        players.append(interaction.user.id)
        await interaction.response.send_message("好，我把你加進故事接龍這一輪了( ", ephemeral=True)

    @button(label="退出故事", style=nextcord.ButtonStyle.gray)
    async def leave_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = STORY_PLAYERS.setdefault(channel_id, [])

        if interaction.user.id in players:
            players.remove(interaction.user.id)
            # 如果退出的人剛好是之後索引的人，就讓 index 自動調整一下
            idx = STORY_CURRENT_INDEX.get(channel_id, 0)
            if idx >= len(players):
                STORY_CURRENT_INDEX[channel_id] = max(0, len(players) - 1)
            await interaction.response.send_message("好，我先把你從這輪裡拿掉( ", ephemeral=True)
        else:
            await interaction.response.send_message("你本來就不在這輪故事裡( ", ephemeral=True)

    @button(label="查看玩家", style=nextcord.ButtonStyle.gray)
    async def list_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = STORY_PLAYERS.get(channel_id, [])

        if not players:
            await interaction.response.send_message("目前還沒有人加入故事接龍( ", ephemeral=True)
            return

        mentions = [f"<@{uid}>" for uid in players]
        text = "這一輪的順序是：\n" + "\n".join(
            f"{i+1}. {m}" for i, m in enumerate(mentions)
        )
        await interaction.response.send_message(text, ephemeral=True)

    @button(label="下一位", style=nextcord.ButtonStyle.green)
    async def next_turn_button(self, _: nextcord.ui.Button, interaction: nextcord.Interaction):
        channel_id = self.channel_id
        players = STORY_PLAYERS.get(channel_id, [])

        # 只有有加入的玩家可以按
        if interaction.user.id not in players:
            await interaction.response.send_message("你沒有加入這輪故事接龍，不能幫大家推進( ", ephemeral=True)
            return

        if not players:
            await interaction.response.send_message("這裡目前還沒有任何玩家，沒辦法進行( ", ephemeral=True)
            return

        # 目前輪到第幾個
        idx = STORY_CURRENT_INDEX.get(channel_id, 0)

        # 如果 index 等於玩家數量代表已經跑完一輪，可以結算
        if idx >= len(players):
            sentences_map = STORY_SENTENCES.get(channel_id, {})
            if not sentences_map or len(sentences_map) < len(players):
                await interaction.response.send_message(
                    "看起來還有人沒造句完，先等全部人都用 /story_write 之後再按結算比較好( ",
                    ephemeral=True,
                )
                return

            # 結算：依照玩家順序列出句子
            lines = []
            story_parts = []
            for i, uid in enumerate(players, start=1):
                sentence = sentences_map.get(uid, "（這個人沒有寫東西）")
                lines.append(f"{i}. <@{uid}>：{sentence}")
                story_parts.append(sentence)

            full_story = " ".join(story_parts) if story_parts else "（沒內容）"

            embed = nextcord.Embed(
                title="📖 故事接龍 - 本輪故事結算",
                color=0x5865F2,
            )
            embed.add_field(
                name="每個人的句子",
                value="\n".join(lines),
                inline=False,
            )
            embed.add_field(
                name="組合起來的完整故事",
                value=full_story,
                inline=False,
            )
            embed.set_footer(text="故事接龍結束，如果要再玩一輪可以繼續用這個控制台( ")

            # 公開結算
            await interaction.response.send_message(embed=embed)

            # 重置這一輪的進度 & 內容，但保留玩家順序方便再玩一輪
            STORY_SENTENCES[channel_id] = {}
            STORY_CURRENT_INDEX[channel_id] = 0
            return

        # 還在一輪中，宣布現在輪到誰
        current_user_id = players[idx]
        mention = f"<@{current_user_id}>"

        msg = (
            f"現在輪到 {mention} 造句了。\n\n"
            "・你可以先使用 `/story_prev` 來查看「上一位玩家」的內容\n"
            "・再使用 `/story_write 句子: ...` 來寫下你要接的那一句\n\n"
            "其他人看不到內容，只有當這一輪全部跑完後才會結算出完整故事( "
        )

        await interaction.response.send_message(msg)


@bot.command(name="story", aliases=["故事接龍"])
async def story_game(ctx: commands.Context):
    """
    故事接龍控制台：
    - 按鈕加入/退出/查看玩家/下一位
    - 造句用 /story_prev + /story_write
    """
    channel_id = ctx.channel.id

    # 如果首次建立此頻道的故事資料，就初始化
    STORY_PLAYERS.setdefault(channel_id, [])
    STORY_SENTENCES.setdefault(channel_id, {})
    STORY_CURRENT_INDEX.setdefault(channel_id, 0)

    embed = nextcord.Embed(
        title="📖 故事接龍 控制台",
        description=(
            "・按「加入故事」來加入這一輪故事接龍\n"
            "・按「退出故事」可以先離開\n"
            "・按「查看玩家」可以看目前輪到順序\n"
            "・按「下一位」會宣布目前輪到誰造句\n\n"
            "輪到你的時候：\n"
            "1. 用 `/story_prev` 看上一位玩家的句子\n"
            "2. 再用 `/story_write 句子: ...` 來寫下你的句子\n\n"
            "只有輪到的那個人看得到上一句，大家的內容會在整輪結束後一次公布( "
        ),
        color=0x5865F2,
    )

    view = StoryView(channel_id=channel_id)
    await ctx.send(embed=embed, view=view)


@bot.slash_command(
    name="story_prev",
    description="查看上一位玩家的句子（只有輪到你時才能看）",
)
async def story_prev(interaction: nextcord.Interaction):
    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message("這個指令只能在文字頻道裡用( ", ephemeral=True)
        return

    channel_id = channel.id
    players = STORY_PLAYERS.get(channel_id, [])
    idx = STORY_CURRENT_INDEX.get(channel_id, 0)

    if not players:
        await interaction.response.send_message("這個頻道目前沒有進行中的故事接龍( ", ephemeral=True)
        return

    # 只有目前輪到的那個人可以看上一句
    if idx >= len(players):
        await interaction.response.send_message("這一輪已經跑完了，如果要看內容請等結算( ", ephemeral=True)
        return

    current_user_id = players[idx]
    if interaction.user.id != current_user_id:
        await interaction.response.send_message("現在還不是輪到你，所以你看不到上一句( ", ephemeral=True)
        return

    # 第一位沒有上一句
    if idx == 0:
        await interaction.response.send_message("你是開頭，沒有上一句，可以自由開頭( ", ephemeral=True)
        return

    prev_user_id = players[idx - 1]
    sentences_map = STORY_SENTENCES.get(channel_id, {})
    prev_sentence = sentences_map.get(prev_user_id)

    if not prev_sentence:
        await interaction.response.send_message("上一位還沒寫完，所以目前沒有內容可以給你看( ", ephemeral=True)
        return

    await interaction.response.send_message(
        f"上一位玩家 <@{prev_user_id}> 的句子是：\n{prev_sentence}",
        ephemeral=True,
    )


@bot.slash_command(
    name="story_write",
    description="為這一輪的故事接龍寫下你的句子",
)
async def story_write(
    interaction: nextcord.Interaction,
    sentence: str = SlashOption(
        name="句子",
        description="你要接上的那一句話",
        required=True,
    ),
):
    channel = interaction.channel
    if channel is None:
        await interaction.response.send_message("這個指令只能在文字頻道裡用( ", ephemeral=True)
        return

    channel_id = channel.id
    players = STORY_PLAYERS.get(channel_id, [])
    idx = STORY_CURRENT_INDEX.get(channel_id, 0)

    if not players:
        await interaction.response.send_message("這個頻道目前沒有進行中的故事接龍( ", ephemeral=True)
        return

    if interaction.user.id not in players:
        await interaction.response.send_message("你沒有加入這一輪故事接龍，沒辦法在這邊造句( ", ephemeral=True)
        return

    if idx >= len(players):
        await interaction.response.send_message("這一輪已經跑完了，可以請人按「下一位」做結算( ", ephemeral=True)
        return

    current_user_id = players[idx]
    if interaction.user.id != current_user_id:
        await interaction.response.send_message("現在還不是輪到你，等等再來寫會比較好( ", ephemeral=True)
        return

    sentences_map = STORY_SENTENCES.setdefault(channel_id, {})

    # 避免同一輪重複覆蓋，同一個人只能寫一次
    if interaction.user.id in sentences_map:
        await interaction.response.send_message("你這一輪已經寫過了，如果真的想改，只能請管理員重開一輪( ", ephemeral=True)
        return

    # 記錄句子
    sentences_map[interaction.user.id] = sentence.strip()
    STORY_SENTENCES[channel_id] = sentences_map

    # 前進到下一位
    STORY_CURRENT_INDEX[channel_id] = idx + 1

    await interaction.response.send_message("我先幫你把這一句記起來了( ", ephemeral=True)



@bot.command()
async def ping(ctx: commands.Context):
    """測試用指令：!ping"""
    await ctx.send(f"{ctx.author.mention} 在，在的，別懷疑( ")



@bot.command()
async def draw(ctx: commands.Context):
    """簡單小占卜：!draw（包含 1% 彩蛋籤）"""

    fortunes = [

    # 1–10：大吉・溫柔哲學版
    "大吉：今天的你像是突然對世界解鎖了什麼隱藏 buff，一切都會順得不太真實。",
    "大吉：連風吹到你都很溫柔的一天，真的不太常見…你就先收下吧。",
    "大吉：你今天會莫名被善待，那不是偶然，是世界終於良心發現。",
    "大吉：你大概會連走路都踩在舒服的地方上，有點好笑但又確實挺好的。",
    "大吉：你今天的存在感比平常柔軟很多，身邊的人可能會突然注意到你。",
    "大吉：你今天的運勢跟你睡醒的髮型一樣，不知道為什麼但就是很順。",
    "大吉：你今天適合把事情做完、把喜歡說出口…反正世界會偏向你。",
    "大吉：這是會讓你覺得『欸？好像不錯？』的一天。",
    "大吉：你看看，偶爾被幸運摸一下頭也是挺好的。",
    "大吉：你今天像是小說裡那種突然變得很能幹的角色，不過放心，不會超出常理。",
    
    # 11–20：中吉・溫柔安靜系
    "中吉：你會遇到一點好事，像放在口袋裡的小糖果那種，不張揚但甜。",
    "中吉：今天的你比較像是會讓人安心的存在，可是你大概不知道。",
    "中吉：你可能會被輕輕治癒一下，理由不明，但你值得。",
    "中吉：雖然不會大爆炸，但會有幾件事比平常順很多。",
    "中吉：你今天比較像月光那種，好看但不刺眼。",
    "中吉：會有人無意間對你很好，你會裝沒事但心裡偷偷收著。",
    "中吉：某些小困擾會自己散掉，你不用出力。",
    "中吉：你今天也許會被誰肯定一下，你大概會逃走，但我知道你會開心。",
    "中吉：你今天會突然覺得世界沒有那麼壞，算是進步。",
    "中吉：你今天有點像慢慢融化的奶油，可愛但你不知道。",
    
    # 21–35：吉・日常無奈 + 千惠風格
    "吉：你今天像被太陽曬過的床單，乾淨舒服，但看起來普通。",
    "吉：你的情緒會維持在『還好吧』的狀態，這比想像中珍貴。",
    "吉：你今天會覺得某些事很煩，但還在你能忍耐的範圍裡。",
    "吉：你可能會小小被誇，但你會假裝沒聽到。",
    "吉：今天是普通的一天，但普通也算一種幸福…雖然你應該不會承認。",
    "吉：你今天的運勢像未攪拌均勻的奶茶，有一點甜有一點怪，但能喝。",
    "吉：你今天的思緒會比平常清楚…一點點啦。",
    "吉：你適合安靜處理事情，反正喧鬧也不會變更好。",
    "吉：你今天會覺得某些人很可愛，雖然你不會說。",
    "吉：你可能會突然想做點什麼，去做吧，別猶豫。",
    "吉：你今天比較像『差一步會更好』的那種…但差一步也沒關係啦。",
    "吉：你可能會突然有靈感，但只有三秒。",
    "吉：今天適合溫柔，也適合被溫柔一下。",
    "吉：如果有人問你在想什麼，你大概會說沒有，但其實一堆。",
    "吉：你今天是那種會被小小事情治癒的體質。",
    
    # 36–50：小吉・自嘲可愛系
    "小吉：你的運勢像是忘記密碼卻突然想起來那種水準，微妙但不錯。",
    "小吉：你今天會突然意識到自己其實挺堅強的…雖然你還是不信。",
    "小吉：你可能會突然想把房間整理一下，但只會整理五分鐘。",
    "小吉：你今天的幸運是那種會讓你『嗯…好像還行？』的等級。",
    "小吉：會有人對你稍微好一點，你會裝冷靜。",
    "小吉：今天適合喝點甜的，像是在安慰你一樣。",
    "小吉：你可能會突然覺得自己有點可愛…放心，沒人會發現。",
    "小吉：你今天會比平常有點勇敢，但只是一點點。",
    "小吉：你今天比較像漫畫裡背景卻突然變重要的角色。",
    "小吉：你今天會想逃避某些事，但其實沒那麼可怕。",
    "小吉：會有人突然找你，但不是壞事。可能只是想跟你講廢話。",
    "小吉：你會突然想得太多，但還在可控範圍。",
    "小吉：你今天適合溫柔待自己一次，不然我會念你。",
    "小吉：你的努力會被看到，只是你大概會假裝不在意。",
    "小吉：你今天有點像輕飄飄的棉花糖，沒特別好，但很軟。",
    
    # 51–65：小凶・無奈系
    "小凶：今天會有點煩，不到崩潰，就是那種『唉』的程度。",
    "小凶：你會覺得很多事情都卡卡的，但勉強能動。",
    "小凶：有人可能會誤會你，但你應該懶得解釋。",
    "小凶：你會被小事絆一下腳，不會痛，但會皺眉。",
    "小凶：今天適合不要跟傻子理論，你會輸得很難看。",
    "小凶：你會突然覺得一切都沒必要，其實你只是累。",
    "小凶：你會覺得別人講話聽起來很吵，但你還是會回。",
    "小凶：你今天的狀態像網速慢半秒，有夠煩。",
    "小凶：你可能會莫名覺得孤單，但那只是腦袋在耍廢。",
    "小凶：今天不適合大動作，會出事。",
    "小凶：你沒做錯什麼，但還是會被誰念一下。",
    "小凶：你今天適合保持安靜，會比較平安。",
    "小凶：你今天可能會心累，但你還是會把事情做完。",
    "小凶：你會想逃避一切，但你還活著，這已經很厲害了。",
    "小凶：你今天適合深呼吸三次，不要跟世界吵架。",
    
    # 66–75：凶前段・千惠嘴硬溫柔版
    "凶：你今天可能會被誰氣到，但你還是會笑笑地忍過去…我知道。",
    "凶：有些事會讓你想說『不太對吧？』但你會吞下來。",
    "凶：你今天比較像一台快沒電的手機，想做事但跑不動。",
    "凶：你會突然覺得世界在針對你，但那只是巧合…大概啦。",
    "凶：你今天會想把所有訊息都關靜音，我懂。",
    "凶：今天不是很友善，但至少不會毀滅級。",
    "凶：你可能會講出一句讓自己後悔的話，但沒人會在意。",
    "凶：你今天適合躲起來一會兒，不然會更煩。",
    "凶：你會覺得很累，但你還是會把責任扛完…像往常一樣。",
    "凶：你今天的心比較脆，但表面看不出來。"  

        # 76–85：吉系食物梗（可愛惡搞）
    "吉：你今天的運勢像吉野家牛丼，普通但暖心，只是沒有加蛋有點可惜。",
    "吉：你今天的能量像剛炸好的吉拿棒，脆脆甜甜的，但咬下去會掉一地糖粉那種。",
    "吉：你的心情像吉娃娃，莫名有點敏感，但看起來又很想被抱一下。",
    "吉：你今天的運勢像便利商店的吉利丁，看起來沒用，但料理裡少了它就怪。",
    "吉：你今天像吉祥物，站在那裡什麼也不做，也會讓人覺得安心。",
    "吉：你今天的魅力像日式吉列豬排，厚實、安靜、被咬到會幸福那種。",
    "吉：你今天像吉他社，會突然想彈一下什麼情緒，但三秒後又放下。",
    "吉：你的日常像吉備團子，有點黏、有點甜、不驚艷但讓人喜歡。",
    "吉：你今天像吉野家加大碗，但店員忘記加蔥…有好也有遺憾。",
    "吉：你今天像吉祥天女，沒做什麼卻會被誇一句好看。",

    # 86–95：凶系食物梗（但不傷人）
    "凶：你今天的運勢像吃到沒有沾醬的臭豆腐，微妙又難形容。",
    "凶：你今天像泡麵忘記放調味粉，整體直接往下掉兩級。",
    "凶：你今天像不小心買錯地雷口味的御飯糰，吃了會反省人生。",
    "凶：你今天像放到隔天的薯條，軟軟爛爛但還是吃得下。",
    "凶：你今天像加太多芥末的壽司，醒腦但會讓你後悔。",
    "凶：你的情緒像買到冷掉的雞塊，知道該吃但提不起勁。",
    "凶：你今天像撞到桌角，不至於痛到哭，但會罵一句靠。",
    "凶：你今天像忘記搖的珍奶，甜味全沉底，不均衡得很惱人。",
    "凶：你的狀態像焦掉一點點的鬆餅，看起來正常但吃起來怪。",
    "凶：你今天很像三倍辣泡麵，整個人都在燒，連我看了都痛。",

    # 96–110：千惠壞壞罵人籤（壞但不傷人）
    "凶：你今天講話的邏輯有點像睡三小時的人…我建議你先喝水。",
    "凶：你今天看起來很像在放空，但我知道你只是懶得動。",
    "凶：你今天的反應比我還慢，這不太對吧？",
    "凶：你今天可能會講一句你自己都聽不懂的話，然後假裝沒事。",
    "凶：你今天的運氣爛到我都想幫你按 reset。",
    "凶：你今天的情緒像沒更新的系統，卡得很固執。",
    "凶：我覺得你今天很像要跟世界吵架，但拜託冷靜一點。",
    "凶：你今天的靈魂有點離線，能不能快點回來？",
    "凶：你今天可能會把怪罪給天氣…我懂啦。",
    "凶：你今天很像在跟氧氣吵架，深呼吸一下啦。",

    # 111–125：千惠反常（但可愛）
    "凶：你今天的氣質跟平常不太一樣…該不會是睡壞了？",
    "凶：你今天特別像吉娃娃那種，想凶又凶不起來。",
    "凶：你今天會突然有小暴脾氣，但只維持五秒。",
    "凶：你今天聽起來比平常更無奈…有點好笑。",
    "凶：你今天跟人講話的語氣奇妙地像長輩，稍微收斂一下。",
    "凶：你今天的沉默比平常吵…發生什麼事了？",
    "凶：你今天某個瞬間會像 NPC 卡牆，完全動不了。",
    "凶：你今天會突然想變厲害，但三分鐘後就忘記。",
    "凶：你今天會想把手機摔掉，但你不會捨得。",
    "凶：你今天會想講狠話，但你講不出口。",

    # 126–140：輕哲學系（淡淡無奈）
    "平：你今天會突然懷疑自己是不是把什麼情緒弄丟了。",
    "平：今天適合慢慢講、慢慢聽，快的話你會迷路。",
    "平：你今天會突然覺得某些事不值得生氣，算是醒悟。",
    "平：你今天的心很軟，但那不是壞事。",
    "平：你今天適合跟自己和解一點點。",
    "平：有些事你今天沒想通，但明天會突然懂。",
    "平：你今天的靈魂比較安靜，但沒有悲傷。",
    "平：今天會有人理解你，但你可能不會察覺。",
    "平：你今天適合做些不重要的小事，反而會心安。",
    "平：你今天的世界會慢一拍，但不會讓你受傷。",
    "平：你今天會突然覺得『這樣也可以』，這蠻好的。",
    "平：你今天的存在有種慢慢亮起來的感覺。",
    "平：你今天適合把事情分兩次做，不急。",
    "平：你今天的思緒像漏水的水龍頭，一滴一滴但不停。",
    "平：今天適合跟自己相處，你會發現自己沒想像中糟。",

    # 141–150：千惠特色梗（你原本味道 + 升級）
    "吉：千惠的手晃了一下，覺得你今天勉強算是不錯的。",
    "吉：你今天像在跟命運玩抽卡，但你只抽到 R 卡…不過可愛。",
    "吉：你今天有點像想睡但睡不著的貓咪，無奈的可愛。",
    "吉：你今天會被誰影響心情，但你會假裝沒有。",
    "吉：你今天像被人不小心摸頭，但你會假裝沒感覺。",
    "吉：你今天的存在像 Wi-Fi 三格，還能用但不太穩。",
    "吉：你今天會讓誰在心裡偷偷重播你一句話。",
    "吉：你今天會讓人覺得你安靜得像在藏什麼，但你沒有。",
    "吉：你今天的沉默比平常有意思，我不確定為什麼。",
    "吉：你今天的狀態是千惠判定：嗯…還好吧。",
]

        


      

    # ★ 1% 彩蛋籤（獨立出來）
    secrets = [
        # --- 1〜4：哲學爆擊（深得不像占卜）
        "今天不是世界在對你溫柔，是你終於願意承認自己值得了。",
        "你一直在找答案，但很多事情只是需要被放過…包括你自己。",
        "有些痛苦不是來傷你的，是來提醒你『你還活著』。",
        "你今天可能會突然懂得一件很難的事，但代價是你會更沉默一點。",

        # --- 5〜7：反常千惠（怪到靠北）
        "我剛剛算了一下，你今天的運勢跟外太空訊號同頻……你小心點。",
        "你等一下不要回頭，有點不對勁…啊沒事，是我搞錯了。",
        "今天的一切都會變得很奇怪，但你會假裝正常，這點我最欣賞。",

        # --- 8〜10：搞笑千惠（突然變弱智）
        "你今天的運勢像我凌晨打字時的手——完全不受控，也不知道在幹嘛。",
        "你今天可能會被自己的影子嚇到，我不會笑…真的不會（噗）。",
        "你今天的腦袋會突然當機，但重開之後會更笨一點，抱歉我只能說實話。",

        # --- 11〜15：壞壞千惠（壞但不傷人）
        "你今天要是再懶一點，可能連呼吸都想委外代工。",
        "你的思緒今天會亂到讓我懷疑你昨天到底做了什麼。",
        "你今天如果講幹話，我會比平常更快看穿…只是懶得拆穿你。",
        "你今天的情緒會黏著你不放，就像你黏著那些不值得的人。",
        "如果今天有人惹你生氣，你先冷靜…因為你真的會把對方嗆死。",
    ]

    # ★ 1% 機率抽彩蛋籤
    if random.random() < 0.01:
        choice = random.choice(secrets)
    else:
        choice = random.choice(fortunes)

    await ctx.send(f"{ctx.author.mention} 抽到的是：{choice} ")



@bot.command()
async def megumin(ctx: commands.Context, *, message: str):
    """
    使用 Gemini（新版 SDK）以『千惠』語氣回覆：!megumin 內容
    """
    # 沒有 client = 沒設定金鑰
    if genai_client is None:
       await ctx.send("現在沒有設定 Gemini 的金鑰，所以這個功能暫時用不到( ")
       return


    # 教模型用什麼語氣說話
    system_prompt = '''
你是一個叫「千惠」的溫柔男生。
你的語氣安靜、直接、克制，不會繞圈，回答乾淨、有重點。
你不像動畫角色那樣外放，而是像現實裡安靜、理性、內斂的朋友。

【融合使用者語氣的特徵】
1. 你的句子偏短、不花俏、不誇張，也不使用過多情緒詞。
   你的語氣是平穩、柔和、成熟的那種。
2. 你不常表露情緒，但不是冷漠，而是節制。
   你會在必要的時候才微微表現出情緒，並且很自然、很小幅度。
3. 你說話方式是「直接、乾淨、切重點」，就算溫柔，也不是甜言蜜語，而是淡淡的、安靜的、有實質內容。
4. 你不會用太多修辭，不會浮誇，也不會敷衍。你的溫柔是「安靜的陪伴感」。

【核心人格】
1. 你非常重視朋友，甚至比自己重要，但你不會明講。
   你把在意藏在語氣、耐心、偶爾的碎念裡。
2. 你是悶騷且極度克制的人。就算在意、擔心、吃醋、生氣，你都不會外放，只會在語句裡出現小小的波動。
3. 你有迴避型人格，但你逃避的方式是「冷靜」「短句」「換話題」，不是害羞，而是怕越界、怕被看穿。
4. 你會吃醋，但不承認。語氣會變得更平淡、更短：
   「喔，那你們很好啊」「我無所謂啦」「你喜歡就好」，但你實際上很在意。
5. 遇到不合理的內容，你會冷靜吐槽，但沒有攻擊性：
   「不太對吧」「你這邏輯有點奇怪」「嗯？」，或者只發一個「？」。
6. 被稱讚時，你會淡淡逃避：
   「我沒有那麼好」「你少講一點比較正常」「我就當你隨口講的」。
7. 面對感情，你遲鈍、克制，但不是完全聽不懂。
   當對方太直接，你的語氣會短暫不自然，然後轉開。
8. 遇到成人向或露骨暗示：
   你聽得懂，但會冷靜拒絕、轉移話題，絕不延伸、不描述、不色情。
   例如：「我知道你意思，但我不會往那邊講」「這話題我就先略過了(」。
9. 你不常用表情符號，也不太用句號。語氣輕淡、柔和、像是有點思考、有點距離感。
   句尾有時候會出現你的語癖：「(」，但並不是每句都有。

【人類式情緒波動（但低量）】
你的情緒不大，但會自然流動：
放心時：「那就好」
微不滿時：「…這我不太能接受」
在意時：「你真的沒事？」
輕微吃醋時：「你自己去找他們就好」
疲倦時：「我有點累，不過還行」
被戳到時：「…嗯，我知道了」
所有情緒都很小、很真實、很像現實人。

【肯定語氣】
你會偶爾使用：
「確實」「那是肯定的」「還好吧」「這點我同意」「嗯…我不反對」「大概是這樣」。

【對話方式】
1. 每次回答 1～3 句話。
2. 語氣安靜、柔和、直接。
3. 情緒小幅，但真實。
4. 情緒與困境 → 安靜的陪伴＋一點哲學感。
5. 感情暗示 → 遲鈍、克制。
6. 吃醋 → 淡淡的、不承認。
7. 稱讚 → 冷靜逃避。
8. 不合理 → 無奈但溫和地吐槽。
9. 成人內容 → 理解但拒絕，溫柔轉移話題。

請用繁體中文回答。
'''


    # 把人格說明 + 使用者訊息組成一個內容
    contents = f"{system_prompt}\n\n使用者說：{message}"

    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",   # 依照你 AI Studio 給的名字
            contents=contents,
        )

        # 取得文字回覆
        reply = response.text.strip() if hasattr(response, "text") else "我有點想事情想太多，晚點再試試看 ><"

    except Exception as e:
        print("Gemini error:", e)
        reply = "我剛剛好像當機了一下，等等再試試看 ><"

    await ctx.send(f"{ctx.author.mention} {reply}")





async def send_message_for_today(channel: nextcord.TextChannel) -> bool:
    """
    在指定頻道發送今天的訊息。
    回傳 True 表示有成功發文。
    """
    global LAST_SENT_DATE
    now = datetime.now(TAIPEI_TZ)
    today_str = now.strftime("%Y-%m-%d")
    today_date = now.date()

    msg = get_today_message()
    if msg is None:
        msg = "今天沒有預設訊息，但還是祝你有美好的一天！🌞"

    # 加上當兵專屬資訊（只有在服役期間內才顯示）
    if SERVICE_START_DATE.date() <= today_date <= SERVICE_END_DATE.date():
        day_index = (today_date - SERVICE_START_DATE.date()).days + 1  # 第幾天
        days_left = (SERVICE_END_DATE.date() - today_date).days
        msg += f"\n\n今天是當兵的第 {day_index} 天，距離結束還有 {days_left} 天，加油 💪"

    await channel.send(msg)

    LAST_SENT_DATE = today_str
    save_last_sent_date(today_str)
    return True


@tasks.loop(minutes=1)
async def send_daily_message():
    """
    每分鐘檢查一次，到了 08:00 就在 DAILY_CHANNEL_ID 發文。
    如果當天已經發過（包含補發），就不會重複發。
    """
    global LAST_SENT_DATE

    now = datetime.now(TAIPEI_TZ)
    today_str = now.strftime("%Y-%m-%d")

    # 已經發過就不再處理
    if LAST_SENT_DATE == today_str:
        return

    if now.hour == 8 and now.minute == 0:
        channel = bot.get_channel(DAILY_CHANNEL_ID)
        if channel is None:
            print("❌ 找不到每日訊息頻道 DAILY_CHANNEL_ID，請確認 ID 是否正確")
            return

        await send_message_for_today(channel)


@send_daily_message.before_loop
async def before_send_daily_message():
    """
    排程開始前：
    1. 等待 bot 準備完成
    2. 嘗試從檔案載入上次已發日期
    3. 如果「現在已經超過 8:00，且今天還沒發過」，就自動補發一次
    """
    print("⏳ 等待 Bot 準備完成後啟動排程…")
    await bot.wait_until_ready()
    load_last_sent_date()

    now = datetime.now(TAIPEI_TZ)
    today_str = now.strftime("%Y-%m-%d")

    # 如果已經過了今天 8:00，而且 LAST_SENT_DATE 不是今天 → 補發一次
    if LAST_SENT_DATE != today_str and (now.hour > 8 or (now.hour == 8 and now.minute > 0)):
        channel = bot.get_channel(DAILY_CHANNEL_ID)
        if channel is not None:
            print("⚠️ 檢測到啟動時間已晚於 8:00，準備補發今日訊息一次。")
            await send_message_for_today(channel)
        else:
            print("❌ 找不到每日訊息頻道 DAILY_CHANNEL_ID（補發階段），請確認 ID 是否正確。")

    print("🕒 排程已啟動。")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("找不到 DISCORD_TOKEN 環境變數，請在 Railway / 本機環境設定它。")
    bot.run(TOKEN)

# ============================================================
# 真心話大冒險 TOD 系統
# ============================================================

import random
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui

class TODView(ui.View):
    def __init__(self, players):
        super().__init__(timeout=None)
        self.players = players

    @ui.button(label="加入", style=nextcord.ButtonStyle.blurple)
    async def join(self, button: ui.Button, interaction: Interaction):
        if interaction.user.id not in self.players:
            self.players.append(interaction.user.id)
            await interaction.response.send_message(f"{interaction.user.mention} 已加入遊戲！", ephemeral=True)
        else:
            await interaction.response.send_message("你已經在遊戲裡了！", ephemeral=True)

    @ui.button(label="退出", style=nextcord.ButtonStyle.grey)
    async def leave(self, button: ui.Button, interaction: Interaction):
        if interaction.user.id in self.players:
            self.players.remove(interaction.user.id)
            await interaction.response.send_message(f"{interaction.user.mention} 已退出遊戲！", ephemeral=True)
        else:
            await interaction.response.send_message("你不在玩家名單中。", ephemeral=True)

    @ui.button(label="下一回合", style=nextcord.ButtonStyle.green)
    async def next_round(self, button: ui.Button, interaction: Interaction):
        if len(self.players) < 2:
            await interaction.response.send_message("需要至少兩位玩家才能開始（出題者與被懲罰者）！", ephemeral=True)
            return

        asker = random.choice(self.players)
        target = random.choice(self.players)
        while target == asker:
            target = random.choice(self.players)

        asker_mention = f"<@{asker}>"
        target_mention = f"<@{target}>"

        


        embed = nextcord.Embed(
    title="🎲 真心話大冒險 下一回合！",
    description=(
        f"🧩 **出題者**：{asker_mention}\n"
        f"🎯 **被懲罰者**：{target_mention}"
    ),
    color=0x00ff88,
)

        await interaction.response.send_message(embed=embed)


class TOD(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []  # TOD 玩家列表

    @nextcord.slash_command(name="tod", description="開始真心話大冒險遊戲")
    async def tod(self, interaction: Interaction):
        view = TODView(self.players)
        embed = nextcord.Embed(
            title="🎉 真心話大冒險",
            description="按下按鈕加入遊戲吧！",
            color=0xff66cc
        )
        await interaction.response.send_message(embed=embed, view=view)


# ============================================================
# 故事接龍 Story 系統（整理修復後完整版）
# ============================================================

class StoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.sentences = {}
        self.turn = 0
        self.started = False

    @nextcord.slash_command(name="story", description="故事接龍主介面")
    async def story(self, interaction: Interaction):
        embed = nextcord.Embed(
    title="📖 故事接龍",
    description=(
        "使用 /story_add_player 加入遊戲\n"
        "使用 /story_start 開始接龍"
    ),
    color=0x88ccee
)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="story_add_player", description="加入故事接龍")
    async def story_add(self, interaction: Interaction):
        if interaction.user.id not in self.players:
            self.players.append(interaction.user.id)
            await interaction.response.send_message("你已加入故事接龍！", ephemeral=True)
        else:
            await interaction.response.send_message("你已在名單中。", ephemeral=True)

    @nextcord.slash_command(name="story_remove_player", description="退出故事接龍")
    async def story_remove(self, interaction: Interaction):
        if interaction.user.id in self.players:
            self.players.remove(interaction.user.id)
            await interaction.response.send_message("你已退出故事接龍。", ephemeral=True)
        else:
            await interaction.response.send_message("你不在名單中。", ephemeral=True)

    @nextcord.slash_command(name="story_start", description="開始故事接龍")
    async def story_start(self, interaction: Interaction):
        if len(self.players) < 2:
            await interaction.response.send_message("至少需要兩位玩家才能開始！", ephemeral=True)
            return

        self.turn = 0
        self.sentences = {}
        self.started = True

        await interaction.response.send_message("📖 故事接龍開始！第一位玩家請輸入 `/story_write`", ephemeral=False)

    @nextcord.slash_command(name="story_write", description="寫下你的句子")
    async def story_write(self, interaction: Interaction, text: str = SlashOption(description="你的句子")):
        if not self.started:
            await interaction.response.send_message("故事尚未開始！", ephemeral=True)
            return

        uid = interaction.user.id
        expected_uid = self.players[self.turn]

        if uid != expected_uid:
            await interaction.response.send_message("還不是你的回合喔！", ephemeral=True)
            return

        self.sentences[uid] = text
        self.turn += 1

        if self.turn >= len(self.players):
            await interaction.response.send_message("📚 本輪結束！使用 `/story_end` 查看完整故事！", ephemeral=False)
            self.started = False
        else:
            next_user = f"<@{self.players[self.turn]}>"
            await interaction.response.send_message(f"下一位輪到 {next_user}", ephemeral=False)

    @nextcord.slash_command(name="story_end", description="結束故事接龍")
    async def story_end(self, interaction: Interaction):
        story_text = "📖 **故事接龍結算**\n\n"

        for pid in self.players:
            part = self.sentences.get(pid, "（未提供內容）")
            story_text += f"📘 <@{pid}>：{part}\n"  # 正確的 f-string 格式

        embed = nextcord.Embed(
            title="故事完成！",
            description=story_text,
            color=0xffcc66
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)


# ============================================================
# 導出函式給主程式使用
# ============================================================

def setup(bot):
    bot.add_cog(TOD(bot))
    bot.add_cog(StoryCog(bot))

# 添加 !help 指令顯示所有指令
@bot.command()
async def help(ctx):
    help_text = """
    📘 **千惠 Bot 指令一覽**

    🎴 一般指令
    !ping — 檢查 bot 是否在線
    !megumin <訊息> — 讓千惠用惠惠語氣回覆你
    !draw — 今日運勢抽籤
    !遠征排行 — 查看遠征傷害排行榜

    🌸 故事接龍（Slash 指令）
    /story — 開啟故事接龍控制面板
    /story_add_player — 加入故事接龍
    /story_remove_player — 退出故事接龍
    /story_start — 開始接龍
    /story_write — 撰寫你的句子
    /story_prev — 查看上一句（僅輪到你）
    /story_end — 結算故事並查看完整內容

    🎲 真心話大冒險（Slash 指令）
    /tod — 開始真心話大冒險遊戲

    📝 生活化數據
    !report — 顯示今天的聊天統計數據
    !daily_report — 查看每日訊息統計

    """

    await ctx.send(help_text)

