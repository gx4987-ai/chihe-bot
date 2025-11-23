# daily_job.py
import asyncio
from datetime import datetime
import nextcord
from config import DAILY_MESSAGE_CHANNEL_ID, TAIWAN_TZ
from message_loader import get_message_by_day

class DailyMessageJob:
    def __init__(self, bot):
        self.bot = bot
        self.day_counter = 1  # 從第 1 天開始

    async def start(self):
        """啟動每日訊息排程"""
        await self.bot.wait_until_ready()
        print("DailyMessageJob 啟動")

        while not self.bot.is_closed():
            now = datetime.now(TAIWAN_TZ)
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)

            # 若今天已過 8 點 → 指向隔天
            if now >= target:
                target = target.replace(day=now.day + 1)

            wait_seconds = (target - now).total_seconds()
            print(f"距離下一次發送還有 {wait_seconds/3600:.2f} 小時")

            await asyncio.sleep(wait_seconds)

            await self.send_daily_message()
            self.day_counter += 1

    async def send_daily_message(self):
        channel = self.bot.get_channel(DAILY_MESSAGE_CHANNEL_ID)
        if channel is None:
            print("找不到頻道，無法發送每日訊息")
            return

        msg = get_message_by_day(self.day_counter)
        title = msg["title"]
        content = msg["content"]

        embed = nextcord.Embed(
            title=title,
            description=content,
            color=0x88ccff
        )

        await channel.send(embed=embed)
        print(f"[每日訊息] Day {self.day_counter} 已發送")
