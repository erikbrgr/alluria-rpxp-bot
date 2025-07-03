import discord
import re
import sqlite3
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import asyncio

class Counter(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.time = 0
        self.input_queue = asyncio.Queue()
        self.level_mults = [
            1.0,           # Level 1 → 2
            2.0,           # Level 2 → 3
            6.0,           # Level 3 → 4
            12.66,         # Level 4 → 5
            24.922,        # Level 5 → 6
            29.9064,       # Level 6 → 7
            36.4938,       # Level 7 → 8
            46.3031,       # Level 8 → 9
            52.7855,       # Level 9 → 10
            69.148,        # Level 10 → 11
            49.0941,       # Level 11 → 12
            65.2891,       # Level 12 → 13
            65.2891,       # Level 13 → 14
            81.6114,       # Level 14 → 15
            97.9337,       # Level 15 → 16
            97.9337,       # Level 16 → 17
            130.2558,      # Level 17 → 18
            130.2558,      # Level 18 → 19
            162.8197       # Level 19 → 20
        ]

    @tasks.loop(seconds=1)
    async def fetch_time(self):
        dt = datetime.datetime.now(timezone.utc) 
        utc_time = dt.replace(tzinfo=timezone.utc) 
        self.time = int(utc_time.timestamp())

    @tasks.loop(seconds=0)
    async def db_worker(self):
        while True:
            item = await self.input_queue.get()
            try:
                await self.process_message(item)
            except Exception as e:
                print(f"Error processing queued message: {e}")

            self.input_queue.task_done()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        await self.input_queue.put(message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.fetch_time.start()
        self.db_worker.start()
        print("rpxp_calculator.py is ready")

    @commands.Cog.listener()
    async def process_message(self, message: discord.Message):
        content = message.content
        guild_id = message.guild.id
        author = message.author

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()

        cursor.execute("SELECT tupper_tag FROM Tuppers WHERE guild_id = ? AND owner_id = ?", (guild_id, author.id))
        tags = [row[0] for row in cursor.fetchall()]
        
        # Build regex pattern to match any known tag at start of message
        escaped_tags = [re.escape(tag) for tag in tags]
        pattern = r'^(' + '|'.join(escaped_tags) + r')(.*)'
        
        match = re.match(pattern, content)
        if not match:
            connection.close()
            return  # No valid tag found, exit
        
        tag = match.group(1)
        message_body = match.group(2).lstrip()  # Rest of message after tag
        word_len = len(message_body.split())

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", (guild_id, author.id, tag))

        result = cursor.fetchone()

        if result is None:
            connection.close()
            return
        
        tupper_name = result[3]
        level = result[5]
        current_xp = result[6]
        last_message = result[7]
        parent = result[9]
        
        if parent:
            cursor.execute("UPDATE Tuppers SET last_message = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (self.time, guild_id, author.id, parent))
            cursor.execute("UPDATE Tuppers SET last_message = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?", (self.time, guild_id, author.id, parent))
            cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, author.id, parent))
            parent_result = cursor.fetchone()
            current_xp = parent_result[6]
            print(f"{tupper_name} sent {word_len} words. RPXP applied to parent {parent}.")
        else:
            cursor.execute("UPDATE Tuppers SET last_message = ? WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", (self.time, guild_id, author.id, tag))
            print(f"{tupper_name} sent {word_len} words.")

        # User row
        cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, author.id))
        user = cursor.fetchone()

        if user is None:
            cursor.execute("INSERT INTO Users (guild_id, user_id, monthly_messages, monthly_rpxp, total_messages, total_rpxp) VALUES (?, ?, ?, ?, ?, ?)", (guild_id, author.id, 0, 0, 0, 0))
            connection.commit()
            cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, author.id))
            user = cursor.fetchone()

        monthly = user[2]
        total = user[4]

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))
        guild_data = cursor.fetchone()
        xppw = guild_data[4]
        falloff = guild_data[5]

        rpxp = (word_len * xppw * self.level_mults[level - 1] / 6) * ((100 - falloff * (level - 3)) / 100)
        newxp = rpxp + current_xp

        nmonthly = monthly + word_len
        ntotal = total + word_len

        cursor.execute("UPDATE Users SET monthly_messages = ?, total_messages = ?, monthly_rpxp = monthly_rpxp + ?, total_rpxp = total_rpxp + ? WHERE guild_id = ? AND user_id = ?", (nmonthly, ntotal, rpxp, rpxp, guild_id, author.id))

        if parent:
            cursor.execute("UPDATE Tuppers SET tupper_rpxp = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (newxp, guild_id, author.id, parent))
        else:
            cursor.execute("UPDATE Tuppers SET tupper_rpxp = ? WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", (newxp, guild_id, author.id, tag))

        connection.commit()
        connection.close()


async def setup(client):
    await client.add_cog(Counter(client))
