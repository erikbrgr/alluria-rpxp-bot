import discord
import sqlite3
from discord.ext import commands, tasks
import datetime
from datetime import timezone

class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.time = 0
        self.prefix = "$"

    @tasks.loop(seconds=1)
    async def fetch_time(self):
        dt = datetime.datetime.now(timezone.utc) 
        utc_time = dt.replace(tzinfo=timezone.utc) 
        self.time = int(utc_time.timestamp())

    @commands.Cog.listener()
    async def on_ready(self):
        self.fetch_time.start()
        print("commands.py is ready")

    @commands.command()
    async def boop(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        bot_latency = round(self.client.latency * 1000)

        message = f"Hello World! {bot_latency} ms."
        embed_message = discord.Embed(title="", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()
        connection.close()

        staff_role_id = result[1]
        log_channel_id = result[2]
        cooldown = result[3]
        xppw = result[4]
        falloff = result[5]

        # Get the actual Role and Channel objects
        staff_role = ctx.guild.get_role(staff_role_id)
        log_channel = ctx.guild.get_channel(log_channel_id)

        # Handle missing role or channel
        staff_role_mention = staff_role.mention if staff_role else f"(Role with ID {staff_role_id} not found)"
        log_channel_mention = f"<#{log_channel_id}>" if log_channel else f"(Channel with ID {log_channel_id} not found)"

        # Cooldown formatting
        if cooldown < 60:
            time_text = f"{cooldown} seconds"
        elif cooldown < 3600:
            minutes = cooldown // 60
            time_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif cooldown < 86400:
            hours = cooldown // 3600
            time_text = f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = cooldown // 86400
            time_text = f"{days} day{'s' if days != 1 else ''}"

        # Final message
        message = (
            f"Current server settings:\n"
            f"- **{staff_role_mention}** is the staff role.\n"
            f"- **{log_channel_mention}** is the log channel.\n"
            f"- The collection cooldown lasts for **{time_text}**.\n"
            f"- Players at level 3 gain **{xppw} xp** per word roleplayed.\n"
            f"- Rp xp becomes **{falloff}%** less effective for every level beyond third."
        )

        embed_message = discord.Embed(title="Server settings.", description=message, color=discord.Color.purple())
        if ctx.guild.icon:
            embed_message.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed_message)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            cursor.execute("INSERT INTO Guilds (guild_id, xppw) Values (?,?)", (guild_id, 0.01))
            message = "Server added to database"
            embed_message = discord.Embed(title="", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
        else:
            message = "Server already in database"
            embed_message = discord.Embed(title="", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)

        connection.commit()
        connection.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def staff_role(self, ctx, staff_role: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        try:
            staff_role = int(staff_role)
        except ValueError:
            message = "Role ID needs to be an integer."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            return
        role = ctx.guild.get_role(staff_role)
        if role:
            message = f"Staff role set to {role.mention}"
            embed_message = discord.Embed(title="Staff role saved.", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
        else:
            message = f"No role found with ID {staff_role}."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("UPDATE Guilds SET staff_role = ? WHERE guild_id = ?", (staff_role, guild_id))

        connection.commit()
        connection.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def log_channel(self, ctx, log_channel: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        try:
            log_channel = int(log_channel)
        except ValueError:
            message = "Channel ID needs to be an integer."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            return
        role = ctx.guild.get_channel(log_channel)
        if role:
            message = f"Log channel set to <#{log_channel}>"
            embed_message = discord.Embed(title="Staff role saved.", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
        else:
            message = f"No channel found with ID {log_channel}."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("UPDATE Guilds SET rpxp_channel = ? WHERE guild_id = ?", (log_channel, guild_id))

        connection.commit()
        connection.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def cooldown(self, ctx, cooldown: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        try:
            cooldown = int(cooldown)
            if cooldown < 60:
                time_text = f"{cooldown} seconds"
            elif cooldown < 3600:
                minutes = cooldown // 60
                time_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
            elif cooldown < 86400:
                hours = cooldown // 3600
                time_text = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                days = cooldown // 86400
                time_text = f"{days} day{'s' if days != 1 else ''}"
            message = f"RP XP collection cooldown set to {time_text}."
            embed_message = discord.Embed(title="Cooldown saved.", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)

        except ValueError:
            message = 'Cooldown input has to be an integer.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("UPDATE Guilds SET cooldown = ? WHERE guild_id = ?", (cooldown, guild_id))

        connection.commit()
        connection.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def xp_per_word(self, ctx, xppw: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        try:
            xppw = float(xppw)
        except ValueError:
            message = 'Input has to be a number.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("UPDATE Guilds SET xppw = ? WHERE guild_id = ?", (xppw, guild_id))

        message = f'Players now gain **{xppw} xp** per word at level 3'
        embed_message = discord.Embed(title="Xp per word set.", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)

        connection.commit()
        connection.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def level_falloff(self, ctx, falloff: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        try:
            falloff = int(falloff)
        except ValueError:
            message = 'Input has to be an integer.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("UPDATE Guilds SET level_falloff = ? WHERE guild_id = ?", (falloff, guild_id))

        message = f'Rp xp is **{falloff}%** less effective per level gained.'
        embed_message = discord.Embed(title="Level falloff set.", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)

        connection.commit()
        connection.close()
    
    @commands.command()
    async def register(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        # Get guild settings
        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))
        guild_result = cursor.fetchone()

        if guild_result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed=embed_message)
            connection.close()
            return

        staff_role = guild_result[1]

        # Get user's PCs
        cursor.execute(
            "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_role = ?", (guild_id, ctx.author.id, 1))
        tupper_results = cursor.fetchall()

        pc_amount = len(tupper_results)
        pc_allowance = 2

        if any(row[5] >= 10 for row in tupper_results):
            pc_allowance += 1

        if any(role.id == staff_role for role in ctx.author.roles):
            pc_allowance += 1

        content = content.strip()

        # Step 1: Get the tag
        if ' ' not in content:
            message = "Missing character name."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        tag, rest = content.split(' ', 1)

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", (guild_id, ctx.author.id, tag))
        tag_check = cursor.fetchone()

        if tag_check:
            message = 'Tupper tag must be unique.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        # Step 2: Get the character name in quotes
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index]
        rest = rest[end_bracket_index + 1:].strip()

        # Step 3: Get the role and optional level
        if not rest:
            message = 'Missing role.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        parts = rest.split()

        role_raw = parts[0].upper()  # Case-insensitive
        level = parts[1] if len(parts) > 1 else None

        if role_raw not in ["PC", "NPC"]:
            message = 'Role must be "PC" or "NPC" (case-insensitive).'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        # Step 4: Convert role to bool (1 = PC, 0 = NPC)
        role_bool = 1 if role_raw == "PC" else 0

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        result = cursor.fetchall()

        if result:
            message= (f"**{name}** is being overwritten.")
            embed_message = discord.Embed(title="Tupper of that name already registered.", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            cursor.execute("DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
            connection.commit()
            pc_amount -= len(result)
            

        if role_bool == 1:
            if pc_amount >= pc_allowance:
                message = "You do not have any free PC slots."
                embed_message = discord.Embed(title="Registration failed.", description=message, color=discord.Color.purple())
                await ctx.send(embed = embed_message)
                connection.close()
                return
            if level is None:
                message = 'PCs require a level.'
                embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple())
                await ctx.send(embed = embed_message)
                connection.close()
                return
            if int(level) < 3:
                message = "PCs start at level 3"
                embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple())
                await ctx.send(embed = embed_message)
                connection.close()
                return

        if role_bool == 0 and level is not None:
            message = 'NPCs should not have a level.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple())
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        cursor.execute("INSERT INTO Tuppers (guild_id, owner_id, tupper_tag, tupper_name, tupper_role, tupper_level, tupper_rpxp) Values (?,?,?,?,?,?,?)", (guild_id, ctx.author.id, tag, name, role_bool, level, 0))

        cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, ctx.author.id))
        user = cursor.fetchone()
        if user is None:
            cursor.execute("INSERT INTO Users (guild_id, user_id, monthly_messages, monthly_rpxp, total_messages, total_rpxp) VALUES (?, ?, ?, ?, ?, ?)", (guild_id, ctx.author.id, 0, 0, 0, 0))
            connection.commit()  # Commit after insert

        connection.commit()
        connection.close()

        message = f"You have successfully registered your Tupper. If any information is wrong please use the command again with the same name to overwrite the other imputs. \nIf the name is wrong use `{self.prefix}retire {name}` and try again.\n- Tag: `{tag}`\n- Name: `{name}`\n- Role: `{role_raw}`\n- Level: `{level if level else 'N/A'}`"
        embed_message = discord.Embed(title="Tupper Registered.", description=message, color=discord.Color.purple())
        await ctx.send(embed = embed_message)

    @commands.command()
    async def alter_ego(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        content = content.strip()

        # Step 1: Get the tag
        if ' ' not in content:
            message = "Missing character name."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        tag, rest = content.split(' ', 1)

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", (guild_id, ctx.author.id, tag))
        tag_check = cursor.fetchone()

        if tag_check:
            message = 'Tupper tag must be unique.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        rest = rest.strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index]
        rest = rest[end_bracket_index + 1:].strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Parent name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for parent name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        parent = rest[1:end_bracket_index]
        rest = rest[end_bracket_index + 1:].strip()

        if name == parent:
            message = "Alter name cannot be the same as the parent's."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, parent))

        adoption = cursor.fetchone()
        parent_role = adoption[4]
        parent_level = adoption[5]

        if adoption is None:
            message = 'Parent not found. The parent needs to be one of your PC tuppers.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        if parent_role != 1:
            message = 'Parent is not a PC. The parent needs to be one of your PC tuppers.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        cursor.execute("INSERT INTO Tuppers (guild_id, owner_id, tupper_tag, tupper_name, tupper_role, tupper_level, parent) Values (?,?,?,?,?,?,?)", (guild_id, ctx.author.id, tag, name, 2, parent_level, parent))

        cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, ctx.author.id))
        user = cursor.fetchone()
        if user is None:
            cursor.execute("INSERT INTO Users (guild_id, user_id, monthly_messages, monthly_rpxp, total_messages, total_rpxp) VALUES (?, ?, ?, ?, ?, ?)", (guild_id, ctx.author.id, 0, 0, 0, 0))
            connection.commit()  # Commit after insert

        connection.commit()
        connection.close()

        message = f"{name} was registered as an alter of {parent}."
        embed_message = discord.Embed(title="Alter registered.", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)

    @commands.command()
    async def retire(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        content = content.strip()

        rest = content.strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index]
        rest = rest[end_bracket_index + 1:].strip()

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        result = cursor.fetchone()

        if result is None:
            message = f"You do not have a tupper named **{name}** registered"
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
        
        cursor.execute("DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        cursor.execute("DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND parent = ?", (guild_id, ctx.author.id, name))
        connection.commit()
        connection.close

        message = f"**{name}** was retired."
        embed_message = discord.Embed(title="Tupper retired.", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)
    
    @commands.command()
    async def setlevel(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        content = content.strip()

        rest = content.strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index]
        rest = rest[end_bracket_index + 1:].strip()        

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        result = cursor.fetchone()

        if result is None:
            message = f"You do not have a tupper named **{name}** registered"
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 0:
            message = f"NPCs do not have levels."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 2:
            message = f"Alter's levels are dependant on the parent."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        try:
            level = int(rest)
        except ValueError:
            message = 'Level input has to be an integer.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        if (level < 3) or (level > 20):
            message = 'Level input has to be between **3** and **20**.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
        
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (level, guild_id, ctx.author.id, name))
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?", (level, guild_id, ctx.author.id, name))

        connection.commit()
        connection.close()
        
        message = f"`{name}` was set to level {level}."
        embed_message = discord.Embed(title=f"{ctx.author.display_name} sets the level of a tupper.", description=message, color=discord.Color.purple()) 
        await ctx.send(embed = embed_message)
        connection.close()

    @commands.command()
    async def levelup(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        content = content.strip()

        rest = content.strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index] 

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        result = cursor.fetchone()
        level = result[5]

        if result is None:
            message = f"You do not have a tupper named **{name}** registered"
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 0:
            message = f"NPCs do not have levels."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 2:
            message = f"Alter's levels are dependant on the parent."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if level >= 20:
            message = f"**{name}** cannot go beyond level **20**."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (level + 1, guild_id, ctx.author.id, name))
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?", (level + 1, guild_id, ctx.author.id, name))

        connection.commit()
        connection.close()
        
        message = f"**{name}** leveled up to level **{level + 1}**."
        embed_message = discord.Embed(title=f"{ctx.author.display_name} levels up a tupper.", description=message, color=discord.Color.purple())
        await ctx.send(embed = embed_message)

    @commands.command()
    async def leveldown(self, ctx, *, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        content = content.strip()

        rest = content.strip()

        # Step 2: Get the character name in square brackets
        if not rest.startswith('['):
            message = 'Character name must be in square brackets.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        end_bracket_index = rest.find(']', 1)
        if end_bracket_index == -1:
            message = 'Closing bracket for character name is missing.'
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return

        name = rest[1:end_bracket_index] 

        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (guild_id, ctx.author.id, name))
        result = cursor.fetchone()
        level = result[5]

        if result is None:
            message = f"You do not have a tupper named **{name}** registered"
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 0:
            message = f"NPCs do not have levels."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if result[4] == 2:
            message = f"Alter's levels are dependant on the parent."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        if level <= 3:
            message = f"**{name}** cannot go below level **3**."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close
            return
        
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", (level - 1, guild_id, ctx.author.id, name))
        cursor.execute("UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?", (level - 1, guild_id, ctx.author.id, name))

        connection.commit()
        connection.close()
        
        message = f"**{name}** lost a level and is now at level **{level - 1}**."
        embed_message = discord.Embed(title=f"{ctx.author.display_name} levels down a tupper.", description=message, color=discord.Color.purple())
        await ctx.send(embed = embed_message)

    @commands.command()
    async def collect(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id
        owner_id = ctx.author.id

        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))

        result = cursor.fetchone()

        if result is None:
            message = "This server is not set up yet."
            embed_message = discord.Embed(title="Invalid input!", description=message, color=discord.Color.purple()) 
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        cooldown = result[3]
        
        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_role = ?", (guild_id, owner_id, 1))

        results = cursor.fetchall()
        list_results = [list(row) for row in results]
        found_rpxp = False
        cooldown_done = False
        collection_messages = []
        totalcol = 0
        
        for row in list_results:
            name = row[3]
            rpxp = round(row[6])

            if row[8] is None:
                last_collection = 0
            else:
                last_collection = row[8]

            if self.time - last_collection > cooldown:
                cooldown_done = True
                cursor.execute("UPDATE Tuppers SET last_collection = ? WHERE guild_id = ? AND owner_id = ?", (self.time, guild_id, owner_id))
                connection.commit()
            if rpxp > 0:
                found_rpxp = True
                collection_messages.append(f"- **{name}** collects **{rpxp}** rp xp.")
                totalcol += rpxp
        
        if not cooldown_done:
            message = f"Collection is on **cooldown**. You can collect rp xp again **<t:{last_collection + cooldown}:R>**."
            embed_message = discord.Embed(title=f"{ctx.author.display_name} collects rp xp", description=message, color=discord.Color.purple())
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        if not found_rpxp:
            message = f"None of your characters have **any** rp xp to collect. Please play some more and try again later."
            embed_message = discord.Embed(title=f"{ctx.author.display_name} collects rp xp", description=message, color=discord.Color.purple())
            await ctx.send(embed = embed_message)
            connection.close()
            return
        
        cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, ctx.author.id))
        user = cursor.fetchone()

        monthly = user[3]
        total = user[5]

        nmonthly = monthly + totalcol
        ntotal = total + totalcol
        
        cursor.execute("UPDATE Users SET monthly_rpxp = ?, total_rpxp = ? WHERE guild_id = ? AND user_id = ?", (nmonthly, ntotal, guild_id, ctx.author.id))
        
        message = "\n".join(collection_messages)

        embed_message = discord.Embed(title=f"{ctx.author.display_name} collects rp xp", description=message, color=discord.Color.purple())
        await ctx.send(embed = embed_message)
        
        cursor.execute("UPDATE Tuppers SET tupper_rpxp = ? WHERE guild_id = ? AND owner_id = ?", (0, guild_id, owner_id))

        connection.commit()
        connection.close()

    @commands.command()
    async def list(self, ctx, content: str):
        await ctx.message.delete()
        if ctx.author.bot:
            return

        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
        guild_id = ctx.guild.id
        owner_id = ctx.author.id
        display_name = ctx.author.display_name

        if content:
            if content.lower() != "self":
                try:
                    owner_id = int(content)
                    member = ctx.guild.get_member(owner_id)
                    if member is None:
                        # Try fetching the member if not cached
                        member = await ctx.guild.fetch_member(owner_id)
                    display_name = member.display_name
                except ValueError:
                    embed_message = discord.Embed(title="Invalid input!", description="Argument must either be `self` or an integer.", color=discord.Color.purple()) 
                    await ctx.send(embed=embed_message)
                    return
                except discord.NotFound:
                    embed_message = discord.Embed(title="Invalid input!", description="ID does not belong to a server member.", color=discord.Color.purple()) 
                    await ctx.send(embed=embed_message)
                    return
        
        cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()

        if result is None:
            embed_message = discord.Embed(title="Invalid input!", description="This server is not set up yet.", color=discord.Color.purple()) 
            await ctx.send(embed=embed_message)
            connection.close()
            return
        
        cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ?", (guild_id, owner_id))
        results = cursor.fetchall()
        connection.close()
        
        pcs = []
        alters = []
        npcs = []

        for row in results:
            tag = row[2]
            name = row[3]  # Assuming name is at index 3
            role_bool = row[4]  # 1 = PC, 0 = NPC
            level = row[5]
            parent = row[9]

            if role_bool == 1:
                pcs.append(f"{name} {level} | `{tag}`")
            elif role_bool == 0:
                npcs.append(f"{name} | `{tag}`")
            elif role_bool == 2:
                alters.append(f"{name} | `{tag}` | Parented to: {parent}")

        if not pcs and not alters and not npcs:
            message = f"{display_name} has no registered tuppers."
            embed_message = discord.Embed(title=f"{display_name}'s tupper list.", description=message, color=discord.Color.purple())
            embed_message.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar)
            await ctx.send(embed = embed_message)
            return

        message = f"{display_name} has the following tuppers:\n"

        if pcs:
            message += "\n__**PCs:**__\n"
            for pc in pcs:
                message += f"- {pc}\n"

        if alters:
            message += "\n__**Alters:**__\n"
            for alter in alters:
                message += f"- {alter}\n"

        if npcs:
            message += "\n__**NPCs:**__\n"
            for npc in npcs:
                message += f"- {npc}\n"

        embed_message = discord.Embed(title=f"{display_name}'s tupper list.", description=message, color=discord.Color.purple())
        embed_message.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar)
        await ctx.send(embed = embed_message)

    @commands.command()
    async def helpme(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        
        message = "These are all the commands and their function: \n"

        message += f"\n\n**`{self.prefix}settings`**: \n- Shows the current settings of the bot on this server."
        message += f"\n\n**`{self.prefix}setup`**: \n- Makes the bot add the server to its database. Essential for all other functions!"
        message += f"\n\n**`{self.prefix}staff_role <role_id>`**: \n- Sets the staff role so the bot can recognise staff members."
        message += f"\n\n**`{self.prefix}log_channel <channel_id>`**: \n- Sets the where the bot sends automatic log messages."
        message += f"\n\n**`{self.prefix}cooldown <seconds>`**: \n- Sets the cooldown duration for the `{self.prefix}collect` command."
        message += f"\n\n**`{self.prefix}xp_per_word <amount>`**: \n- Sets the amount of xp that players receive per word (Standard is 0.01)."
        message += f"\n\n**`{self.prefix}level_falloff <amount>`**: \n- Sets the percentage of xp deduction for every level after third."
        message += f"\n\n**`{self.prefix}register <tag> <[Character Name]> <role> <level>`**: \n- Allows you to register one of your tuppers. Role is either PC or NPC. When you make an NPC do not add the level at the end.\n- Entering the command again with a character name you already have overwrites that tupper."
        message += f"\n\n**`{self.prefix}alter_ego <tag> <[Character Name]> <[Parent Name]>`**: \n- Alters are tuppers which belong to a PC, such as a familiar or alternative appearance. When you roleplay with them, the rp xp is collected by the parent character."
        message += f"\n\n**`{self.prefix}retire <[Character Name]>`**: \n- Deletes the tupper from the database. This is irreversible."
        message += f"\n\n**`{self.prefix}setlevel <[Character Name] <level>`**: \n- Sets the tupper's level to the specified amount."
        message += f"\n\n**`{self.prefix}levelup <[Character Name]`**: \n- Increases the level of the tupper by one."
        message += f"\n\n**`{self.prefix}leveldown <[Character Name]`**: \n- Decreases the level of the tupper by one."
        message += f"\n\n**`{self.prefix}collect`**: \n- Collects all the accumulated rp xp for all your PC tuppers"
        message += f"\n\n**`{self.prefix}list <target>`**: \n- Shows you all the tuppers of the user with the target ID. Alternatively you can look at your own with `{self.prefix}list self`."
        message += f"\n\n**`{self.prefix}msummary`**: \n- Gives server statistics based on this month's data."
        message += f"\n\n**`{self.prefix}tsummary`**: \n- Gives server statistics based on all data."

        embed_message = discord.Embed(title=f"Rp xp Bot commands.", description=message, color=discord.Color.purple())
        embed_message.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar)
        await ctx.send(embed = embed_message)

    @commands.command()
    async def msummary(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        
        """Manually triggers the monthly stats summary for this server."""
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()

        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Users WHERE guild_id = ?", (guild_id,))
        users = cursor.fetchall()

        total_users = len(users)
        total_words = sum(row[2] for row in users)  # monthly_messages
        total_xp = sum(row[3] for row in users)     # monthly_rpxp

        avg_words = total_words / total_users if total_users > 0 else 0
        avg_xp = total_xp / total_users if total_users > 0 else 0

        top_user = None
        top_xp = 0

        for row in users:
            user_id = row[1]
            user_xp = row[3]
            if user_xp > top_xp:
                top_xp = user_xp
                top_user_id = user_id

        message = (
            f"Total Words: **{total_words}**\n"
            f"Average Words per User: **{avg_words:.2f}**\n"
            f"Total XP Collected: **{total_xp}**\n"
            f"Average XP per User: **{avg_xp:.2f}**\n"
        )

        embed_message = discord.Embed(title=f"**Monthly Statistics for {ctx.guild.name}**", description=message, color=discord.Color.purple())

        if top_user_id:
            member = ctx.guild.get_member(top_user_id)
            if member:
                embed_message.set_author(name=f"Top User: {member.display_name} with {top_xp} XP", icon_url=member.display_avatar.url)
            else:
                embed_message.set_author(name=f"Top User: <@{top_user_id}> with {top_xp} XP!")

        if ctx.guild.icon:
            embed_message.set_image(url=ctx.guild.icon.url)

        await ctx.send(embed=embed_message)
        connection.close()

    @commands.command()
    async def tsummary(self, ctx):
        await ctx.message.delete()
        if ctx.author.bot:
            return
        
        """Manually triggers the monthly stats summary for this server."""
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()

        guild_id = ctx.guild.id

        cursor.execute("SELECT * FROM Users WHERE guild_id = ?", (guild_id,))
        users = cursor.fetchall()

        total_users = len(users)
        total_words = sum(row[4] for row in users)  # monthly_messages
        total_xp = sum(row[5] for row in users)     # monthly_rpxp

        avg_words = total_words / total_users if total_users > 0 else 0
        avg_xp = total_xp / total_users if total_users > 0 else 0

        top_user = None
        top_xp = 0

        for row in users:
            user_id = row[1]
            user_xp = row[5]
            if user_xp > top_xp:
                top_xp = user_xp
                top_user_id = user_id

        message = (
            f"Total Words: **{total_words}**\n"
            f"Average Words per User: **{avg_words:.2f}**\n"
            f"Total XP Collected: **{total_xp}**\n"
            f"Average XP per User: **{avg_xp:.2f}**\n"
        )

        embed_message = discord.Embed(title=f"**Total Statistics for {ctx.guild.name}**", description=message, color=discord.Color.purple())

        if top_user_id:
            member = ctx.guild.get_member(top_user_id)
            if member:
                embed_message.set_author(name=f"Top User: {member.display_name} with {top_xp} XP", icon_url=member.display_avatar.url)
            else:
                embed_message.set_author(name=f"Top User: <@{top_user_id}> with {top_xp} XP!")

        if ctx.guild.icon:
            embed_message.set_image(url=ctx.guild.icon.url)

        await ctx.send(embed=embed_message)
        connection.close()

async def setup(client):
    await client.add_cog(Commands(client))
