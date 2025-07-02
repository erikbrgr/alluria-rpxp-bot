import discord
import sqlite3
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import asyncio

class Statistics(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.monthly_task.start()

    def cog_unload(self):
        self.monthly_task.cancel()

    @tasks.loop(count=1)
    async def monthly_task(self):
        while True:
            now = datetime.datetime.utcnow()
            
            # Calculate first day of next month
            year = now.year + (now.month // 12)
            month = (now.month % 12) + 1
            next_month = datetime.datetime(year, month, 1, 0, 0, 0)

            delta = (next_month - now).total_seconds()
            print(f"Sleeping for {delta} seconds until next month...")

            await asyncio.sleep(delta)

            # Place your logic for new month here
            print("New month has started! Resetting stats...")

            await self.process_monthly_stats()

    async def process_monthly_stats(self, guild):
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()

        guild_id = guild.id

        cursor.execute("SELECT * FROM Users WHERE guild_id = ?", (guild_id,))
        users = cursor.fetchall()

        total_users = len(users)
        total_words = sum(row[2] for row in users)  # monthly_messages
        total_xp = sum(row[3] for row in users)     # monthly_rpxp

        avg_words = total_words / total_users if total_users > 0 else 0
        avg_xp = total_xp / total_users if total_users > 0 else 0

        top_user_id = None
        top_words = 0

        for row in users:
            user_id = row[1]
            user_words = row[3]
            if user_words > top_words:
                top_words = user_words
                top_user_id = user_id

        message = (
            f"Total Words: **{total_words}**\n"
            f"Average Words per User: **{avg_words:.2f}**\n"
            f"Total XP Collected: **{total_xp}**\n"
            f"Average XP per User: **{avg_xp:.2f}**\n"
        )

        embed_message = discord.Embed(title=f"**Monthly Statistics for {guild.name}**", description=message, color=discord.Color.purple())

        if top_user_id:
            member = guild.get_member(top_user_id)
            if member:
                embed_message.set_author(name=f"Top User: {member.display_name} with {top_words} words", icon_url=member.display_avatar.url)
            else:
                embed_message.set_author(name=f"Top User: <@{top_user_id}> with {top_words} words")

        if guild.icon:
            embed_message.set_image(url=guild.icon.url)

        # Send to system channel or fallback
        channel = guild.system_channel
        if not channel:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    channel = c
                    break

        if channel:
            await channel.send(embed=embed_message)

        # Reset monthly stats
        cursor.execute("UPDATE Users SET monthly_messages = 0, monthly_rpxp = 0")
        connection.commit()
        connection.close()

        print("Monthly stats processed and reset.")

    @commands.Cog.listener()
    async def on_ready(self):
        print("statistics.py is ready")

async def setup(client):
    await client.add_cog(Statistics(client))
