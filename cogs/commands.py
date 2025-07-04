import discord
import sqlite3
from discord.ext import commands, tasks
import datetime
from datetime import timezone
import asyncio

def skip_incomplete_setup_block():
    def decorator(func):
        func._skip_incomplete_setup_block = True
        return func
    return decorator

class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.time = 0
        self.prefix = "$"
        self.db_queue = asyncio.Queue()
        self.client.loop.create_task(self.db_worker())

    async def send_embed(self, ctx, title, description, color):
        embed = discord.Embed(title=title, description=description, color=color)
        await ctx.send(embed=embed)

    async def pre_command_checks(self, ctx, task_func, *task_args):
        await ctx.message.delete()
        if ctx.author.bot:
            return
    
        connection = None
        try:
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
            guild_id = ctx.guild.id
    
            cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))
            guild_result = cursor.fetchone()
    
            cursor.execute("SELECT * FROM Users WHERE guild_id = ? AND user_id = ?", (guild_id, ctx.author.id))
            user = cursor.fetchone()
            if user is None:
                cursor.execute(
                    "INSERT INTO Users (guild_id, user_id, monthly_messages, monthly_rpxp, total_messages, total_rpxp) VALUES (?, ?, ?, ?, ?, ?)", 
                    (guild_id, ctx.author.id, 0, 0, 0, 0)
                )
                await self.send_embed(ctx, "User registered", f"{ctx.author.display_name} added to database.", discord.Color.purple())
    
            if guild_result is None:
                cursor.execute(
                    "INSERT INTO Guilds (guild_id, xppw, cooldown, level_falloff) VALUES (?, ?, ?, ?)",
                    (guild_id, 0.02, 28800, 5)
                )
                connection.commit()  # Commit early to save the new guild
    
                await self.send_embed(ctx, "Server registered.", "Server added to database with default settings.", discord.Color.purple())
    
                cursor.execute("SELECT * FROM Guilds WHERE guild_id = ?", (guild_id,))
                guild_result = cursor.fetchone()
    
            connection.commit()  # Commit user insert if any
    
            guild_staff_role = guild_result[1]
            guild_log_channel = guild_result[2]
    
        except Exception as e:
            print(f"DB error in pre_command_checks: {e}")
            return
        finally:
            if connection:
                connection.close()
    
        skip_block = getattr(task_func, "_skip_incomplete_setup_block", False)
    
        if (guild_staff_role is None or guild_log_channel is None) and not skip_block:
            await self.send_embed(ctx, "The server is not fully set up.", f"An admin must set a staff role and log channel using `{self.prefix}staff_role <role id>` and `{self.prefix}log_channel <channel id>` before the bot can be used.", discord.Color.red())
            return
    
        # Pass to the command logic task
        await self.db_queue.put((task_func, (ctx, guild_result, *task_args)))
    
    async def db_worker(self):
        while True:
            func, args = await self.db_queue.get()
            try:
                await func(*args)
            except Exception as e:
                print(f"DB Task Error: {e}")
            self.db_queue.task_done()
    
    @commands.command()
    async def boop(self, ctx):
        await self.pre_command_checks(ctx, self._boop_task)
    
    async def _boop_task(self, ctx, guild_result):
        try:
            bot_latency = round(self.client.latency * 1000)
            message = f"Hello World! {bot_latency} ms."
            await self.send_embed(ctx, "I was booped.", message, discord.Color.purple())
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def settings(self, ctx):
        await self.pre_command_checks(ctx, self._settings_task)

    @skip_incomplete_setup_block()
    async def _settings_task(self, ctx, guild_result):
        try:
            staff_role_id = guild_result[1]
            log_channel_id = guild_result[2]
            cooldown = guild_result[3]
            xppw = guild_result[4]
            falloff = guild_result[5]
    
            # Handle staff role
            if staff_role_id:
                staff_role = ctx.guild.get_role(staff_role_id)
                staff_role_mention = staff_role.mention if staff_role else f"(Role with ID {staff_role_id} not found)"
            else:
                staff_role_mention = "(Not set)"
    
            # Handle log channel
            if log_channel_id:
                log_channel = ctx.guild.get_channel(log_channel_id)
                log_channel_mention = f"<#{log_channel_id}>" if log_channel else f"(Channel with ID {log_channel_id} not found)"
            else:
                log_channel_mention = "(Not set)"
    
            # Handle cooldown
            if cooldown:
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
            else:
                time_text = "(Not set)"
    
            # XP per word
            xp_text = f"{xppw} xp" if xppw else "(Not set)"
    
            # Falloff
            falloff_text = f"{falloff}%" if falloff else "(Not set)"
    
            message = (
                f"Current server settings:\n"
                f"- **{staff_role_mention}** is the staff role.\n"
                f"- **{log_channel_mention}** is the log channel.\n"
                f"- The collection cooldown lasts for **{time_text}**.\n"
                f"- Players at level 3 gain **{xp_text}** per word roleplayed.\n"
                f"- RP XP becomes **{falloff_text}** less effective for every level beyond third."
            )
    
            embed_message = discord.Embed(title="Server settings", description=message, color=discord.Color.purple())
            if ctx.guild.icon:
                embed_message.set_thumbnail(url=ctx.guild.icon.url)
    
            await ctx.send(embed=embed_message)
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def wipe_server(self, ctx):
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
    
        cursor.execute("DELETE FROM Guilds WHERE guild_id = ?", (ctx.guild.id,))
        connection.commit()
        connection.close()
    
        await self.send_embed(ctx, "Server data deleted.", "Server data wiped from the database.", discord.Color.red())

    @commands.command()
    async def wipe_user(self, ctx):
        connection = sqlite3.connect("./RPXP_databank.db")
        cursor = connection.cursor()
    
        cursor.execute("DELETE FROM Users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
        connection.commit()
        connection.close()
    
        await self.send_embed(ctx, "User data deleted.", "User data wiped from the database for this server.", discord.Color.red())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def staff_role(self, ctx, role_id: str):
        await self.pre_command_checks(ctx, self._staff_role_task, role_id)

    @skip_incomplete_setup_block()
    async def _staff_role_task(self, ctx, guild_result, role_id):
        try:
            # Ensure role_id is an integer
            try:
                role_id = int(role_id)
            except ValueError:
                await self.send_embed(ctx, "Invalid input!", "Role ID needs to be an integer.", discord.Color.red())
                return
    
            role = ctx.guild.get_role(role_id)
            if not role:
                await self.send_embed(ctx, "Invalid input!", f"No role found with ID {role_id}.", discord.Color.red())
                return
    
            # Role exists, update database
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                cursor.execute("UPDATE Guilds SET staff_role = ? WHERE guild_id = ?", (role_id, ctx.guild.id))
                connection.commit()
    
            await self.send_embed(ctx, "Staff role saved.", f"Staff role set to {role.mention}", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def log_channel(self, ctx, channel_id: str):
        await self.pre_command_checks(ctx, self._log_channel_task, channel_id)

    @skip_incomplete_setup_block()
    async def _log_channel_task(self, ctx, guild_result, channel_id):
        try:
            # Ensure channel_id is an integer
            try:
                channel_id = int(channel_id)
            except ValueError:
                await self.send_embed(ctx, "Invalid input!", "Channel ID needs to be an integer.", discord.Color.red())
                return
    
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                await self.send_embed(ctx, "Invalid input!", f"No channel found with ID {channel_id}.", discord.Color.red())
                return
    
            # Channel exists, update database
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                cursor.execute("UPDATE Guilds SET rpxp_channel = ? WHERE guild_id = ?", (channel_id, ctx.guild.id))
                connection.commit()
    
            await self.send_embed(ctx, "Log channel saved.", f"Log channel set to {channel.mention}", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def cooldown(self, ctx, cooldown: str):
        await self.pre_command_checks(ctx, self._cooldown_task, cooldown)

    @skip_incomplete_setup_block()
    async def _cooldown_task(self, ctx, guild_result, cooldown):
        try:
            try:
                cooldown = int(cooldown)
            except ValueError:
                await self.send_embed(ctx, "Invalid input!", "Cooldown input has to be an integer.", discord.Color.red())
                return
    
            # Human-readable cooldown formatting
            if cooldown < 60:
                time_text = f"{cooldown} second{'s' if cooldown != 1 else ''}"
            elif cooldown < 3600:
                minutes = cooldown // 60
                time_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
            elif cooldown < 86400:
                hours = cooldown // 3600
                time_text = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                days = cooldown // 86400
                time_text = f"{days} day{'s' if days != 1 else ''}"
    
            # Update the database safely
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                cursor.execute("UPDATE Guilds SET cooldown = ? WHERE guild_id = ?", (cooldown, ctx.guild.id))
                connection.commit()
    
            await self.send_embed(ctx, "Cooldown saved.", f"RP XP collection cooldown set to {time_text}.", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def xp_per_word(self, ctx, xppw: str):
        await self.pre_command_checks(ctx, self._xp_per_word_task, xppw)

    @skip_incomplete_setup_block()
    async def _xp_per_word_task(self, ctx, guild_result, xppw):
        try:
            xppw = float(xppw)
        except ValueError:
            await self.send_embed(ctx, "Invalid input!", "Input has to be a number.", discord.Color.red())
            return
    
        try:
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                guild_id = ctx.guild.id
                cursor.execute("UPDATE Guilds SET xppw = ? WHERE guild_id = ?", (xppw, guild_id))
                connection.commit()
    
            await self.send_embed(ctx, "Xp per word set.", f"Players now gain **{xppw} xp** per word at level 3.", discord.Color.purple())
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def level_falloff(self, ctx, falloff: str):
        await self.pre_command_checks(ctx, self._level_falloff_task, falloff)

    @skip_incomplete_setup_block()
    async def _level_falloff_task(self, ctx, guild_result, falloff):
        try:
            falloff = int(falloff)
        except ValueError:
            await self.send_embed(ctx, "Invalid input!", "Input has to be an integer.", discord.Color.red())
            return
    
        try:
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                guild_id = ctx.guild.id
                cursor.execute("UPDATE Guilds SET level_falloff = ? WHERE guild_id = ?", (falloff, guild_id))
                connection.commit()
    
            await self.send_embed(ctx, "Level falloff set.", f"Rp xp is **{falloff}%** less effective per level gained.", discord.Color.purple())
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")
    
    @commands.command()
    async def register(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._register_task, content)

    async def _register_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
    
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
    
            staff_role = guild_result[1]
    
            # Get user's PCs
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_role = ?", 
                (guild_id, ctx.author.id, 1)
            )
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
                await self.send_embed(ctx, "Invalid input!", "Missing character name.", discord.Color.red())
                connection.close()
                return
    
            tag, rest = content.split(' ', 1)
    
            # Step 2: Get the character name in square brackets
            if not rest.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
    
            end_bracket_index = rest.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
    
            name = rest[1:end_bracket_index]
            rest = rest[end_bracket_index + 1:].strip()
    
            # Check if tag is unique or name matches
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", 
                (guild_id, ctx.author.id, tag)
            )
            check = cursor.fetchone()
    
            if check and check[2] == tag and check[3] != name:
                await self.send_embed(ctx, "Invalid input!", "Tupper tag must be unique.", discord.Color.red())
                connection.close()
                return
    
            # Step 3: Role and optional level
            if not rest:
                await self.send_embed(ctx, "Invalid input!", "Missing role.", discord.Color.red())
                connection.close()
                return
    
            parts = rest.split()
            role_raw = parts[0].upper()
            level = parts[1] if len(parts) > 1 else None
    
            if role_raw not in ["PC", "NPC"]:
                await self.send_embed(ctx, "Invalid input!", 'Role must be "PC" or "NPC" (case-insensitive).', discord.Color.red())
                connection.close()
                return
    
            role_bool = 1 if role_raw == "PC" else 0
    
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, name)
            )
            existing = cursor.fetchall()
    
            if existing:
                await self.send_embed(ctx, "Tupper of that name already registered.", f"**{name}** is being overwritten.", discord.Color.yellow())
                cursor.execute(
                    "DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                    (guild_id, ctx.author.id, name)
                )
                connection.commit()
                pc_amount -= len(existing)
    
            # PC validations
            if role_bool == 1:
                if pc_amount >= pc_allowance:
                    await self.send_embed(ctx, "Registration failed.", "You do not have any free PC slots.", discord.Color.red())
                    connection.close()
                    return
    
                if level is None:
                    await self.send_embed(ctx, "Invalid input!", "PCs require a level.", discord.Color.red())
                    connection.close()
                    return
    
                try:
                    level_int = int(level)
                except ValueError:
                    await self.send_embed(ctx, "Invalid input!", "Level must be an integer.", discord.Color.red())
                    connection.close()
                    return
    
                if level_int < 3:
                    await self.send_embed(ctx, "Invalid input!", "PCs start at level 3.", discord.Color.red())
                    connection.close()
                    return
            else:
                if level is not None:
                    await self.send_embed(ctx, "Invalid input!", "NPCs should not have a level.", discord.Color.red())
                    connection.close()
                    return
                level_int = None  # Ensure level_int is defined if NPC
    
            # Insert Tupper
            cursor.execute(
                "INSERT INTO Tuppers (guild_id, owner_id, tupper_tag, tupper_name, tupper_role, tupper_level, tupper_rpxp) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                (guild_id, ctx.author.id, tag, name, role_bool, level_int, 0)
            )

            connection.commit()
            connection.close()
    
            message = (
                f"You have successfully registered your Tupper. If any information is wrong please use the command again with the same name to overwrite the other inputs.\n"
                f"If the name is wrong use `{self.prefix}retire {name}` and try again.\n"
                f"- Tag: `{tag}`\n"
                f"- Name: `{name}`\n"
                f"- Role: `{role_raw}`\n"
                f"- Level: `{level if level else 'N/A'}`"
            )
            await self.send_embed(ctx, "Tupper Registered.", message, discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")
            await self.send_embed(ctx, "Error", "An unexpected error occurred.", discord.Color.red())

    @commands.command()
    async def alter_ego(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._alter_ego_task, content)

    async def _alter_ego_task(self, ctx, guild_result, content):    
        try:
            guild_id = guild_result[0]
    
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
    
            content = content.strip()
    
            # Step 1: Get the tag
            if ' ' not in content:
                await self.send_embed(ctx, "Invalid input!", "Missing character name.", discord.Color.red())
                connection.close()
                return
    
            tag, rest = content.split(' ', 1)
    
            # Step 2: Get the character name in square brackets
            if not rest.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
    
            end_bracket_index = rest.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
    
            name = rest[1:end_bracket_index]
            rest = rest[end_bracket_index + 1:].strip()
    
            # Check tag uniqueness (allow overwrite if name matches)
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_tag = ?", 
                (guild_id, ctx.author.id, tag)
            )
            tag_check = cursor.fetchone()
    
            if tag_check and tag_check[3] != name:
                await self.send_embed(ctx, "Invalid input!", "Tupper tag must be unique.", discord.Color.red())
                connection.close()
                return
    
            # Step 3: Get the parent name in square brackets
            if not rest.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Parent name must be in square brackets.", discord.Color.red())
                connection.close()
                return
    
            end_bracket_index = rest.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for parent name is missing.", discord.Color.red())
                connection.close()
                return
    
            parent = rest[1:end_bracket_index]
            rest = rest[end_bracket_index + 1:].strip()
    
            if name == parent:
                await self.send_embed(ctx, "Invalid input!", "Alter name cannot be the same as the parent's.", discord.Color.red())
                connection.close()
                return
    
            # Check parent existence and role
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, parent)
            )
            adoption = cursor.fetchone()
    
            if adoption is None:
                await self.send_embed(ctx, "Invalid input!", "Parent not found. The parent needs to be one of your PC tuppers.", discord.Color.red())
                connection.close()
                return
    
            parent_role = adoption[4]
            parent_level = adoption[5]
    
            if parent_role != 1:
                await self.send_embed(ctx, "Invalid input!", "Parent is not a PC. The parent needs to be one of your PC tuppers.", discord.Color.red())
                connection.close()
                return
    
            # Check for existing alter with same name
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, name)
            )
            existing = cursor.fetchall()
    
            if existing:
                await self.send_embed(ctx, "Tupper of that name already registered.", f"**{name}** is being overwritten.", discord.Color.yellow())
                cursor.execute(
                    "DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                    (guild_id, ctx.author.id, name)
                )
                connection.commit()
    
            # Insert new alter
            cursor.execute(
                "INSERT INTO Tuppers (guild_id, owner_id, tupper_tag, tupper_name, tupper_role, tupper_level, parent) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                (guild_id, ctx.author.id, tag, name, 2, parent_level, parent)
            )
    
            connection.commit()
            connection.close()
    
            await self.send_embed(ctx, "Alter registered.", f"{name} was registered as an alter of {parent}.", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def retire(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._retire_task, content)
        
    async def _retire_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
    
            content = content.strip()
    
            # Check for character name in square brackets
            if not content.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
    
            end_bracket_index = content.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
    
            name = content[1:end_bracket_index]
    
            # Check if tupper exists
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?",
                (guild_id, ctx.author.id, name)
            )
            result = cursor.fetchone()
    
            if result is None:
                await self.send_embed(ctx, "Invalid input!", f"You do not have a tupper named **{name}** registered", discord.Color.red())
                connection.close()
                return
    
            # Delete the tupper and all alters with this tupper as parent in one go
            cursor.execute(
                "DELETE FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND (tupper_name = ? OR parent = ?)",
                (guild_id, ctx.author.id, name, name)
            )
            connection.commit()
            connection.close()
    
            await self.send_embed(ctx, "Tupper retired.", f"**{name}** was retired.", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")
    
    @commands.command()
    async def setlevel(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._setlevel_task, content)
        
    async def _setlevel_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
    
            content = content.strip()
    
            # Check for character name in square brackets
            if not content.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
    
            end_bracket_index = content.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
    
            name = content[1:end_bracket_index]
            rest = content[end_bracket_index + 1:].strip()
    
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, name)
            )
            result = cursor.fetchone()
    
            if result is None:
                await self.send_embed(ctx, "Invalid input!", f"You do not have a tupper named **{name}** registered", discord.Color.red())
                connection.close()
                return
    
            role = result[4]  # tupper_role
            if role == 0:
                await self.send_embed(ctx, "Invalid input!", f"NPCs do not have levels.", discord.Color.red())
                connection.close()
                return
            if role == 2:
                await self.send_embed(ctx, "Invalid input!", f"An alter's level is linked to the parent.", discord.Color.red())
                connection.close()
                return
    
            try:
                level = int(rest)
            except ValueError:
                await self.send_embed(ctx, "Invalid input!", 'Level input has to be an integer.', discord.Color.red())
                connection.close()
                return
    
            if level < 3 or level > 20:
                await self.send_embed(ctx, "Invalid input!", 'Level input has to be between **3** and **20**.', discord.Color.red())
                connection.close()
                return
    
            # Update the tupper's level
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?",
                (level, guild_id, ctx.author.id, name)
            )
            # Also update alters linked to this tupper
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?",
                (level, guild_id, ctx.author.id, name)
            )
    
            connection.commit()
            connection.close()
    
            await self.send_embed(ctx, f"{ctx.author.display_name} sets the level of a tupper.", f"**{name}** was set to level **{level}**.", discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def levelup(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._levelup_task, content)
        
    async def _levelup_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
        
            content = content.strip()
        
            # Step 1: Get character name in square brackets
            if not content.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
        
            end_bracket_index = content.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
        
            name = content[1:end_bracket_index]
        
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, name)
            )
            result = cursor.fetchone()
        
            if result is None:
                await self.send_embed(ctx, "Invalid input!", f"You do not have a tupper named **{name}** registered", discord.Color.red())
                connection.close()
                return
        
            role = result[4]  # tupper_role
            level = result[5]  # tupper_level
        
            if role == 0:
                await self.send_embed(ctx, "Invalid input!", f"NPCs do not have levels.", discord.Color.red())
                connection.close()
                return
            if role == 2:
                await self.send_embed(ctx, "Invalid input!", f"An alter's level is linked to the parent.", discord.Color.red())
                connection.close()
                return
            if level >= 20:
                await self.send_embed(ctx, "Invalid input!", f"**{name}** cannot go beyond level **20**.", discord.Color.red())
                connection.close()
                return
        
            new_level = level + 1
        
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?",
                (new_level, guild_id, ctx.author.id, name)
            )
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?",
                (new_level, guild_id, ctx.author.id, name)
            )
        
            connection.commit()
            connection.close()
        
            await self.send_embed(ctx, f"{ctx.author.display_name} levels up a tupper.", f"**{name}** leveled up to level **{new_level}**.", discord.Color.purple())
        
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def leveldown(self, ctx, *, content: str):
        await self.pre_command_checks(ctx, self._leveldown_task, content)
        
    async def _leveldown_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
            connection = sqlite3.connect("./RPXP_databank.db")
            cursor = connection.cursor()
        
            content = content.strip()
        
            # Step 1: Get character name in square brackets
            if not content.startswith('['):
                await self.send_embed(ctx, "Invalid input!", "Character name must be in square brackets.", discord.Color.red())
                connection.close()
                return
        
            end_bracket_index = content.find(']')
            if end_bracket_index == -1:
                await self.send_embed(ctx, "Invalid input!", "Closing bracket for character name is missing.", discord.Color.red())
                connection.close()
                return
        
            name = content[1:end_bracket_index]
        
            cursor.execute(
                "SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?", 
                (guild_id, ctx.author.id, name)
            )
            result = cursor.fetchone()
        
            if result is None:
                await self.send_embed(ctx, "Invalid input!", f"You do not have a tupper named **{name}** registered", discord.Color.red())
                connection.close()
                return
        
            role = result[4]  # tupper_role
            level = result[5]  # tupper_level
        
            if role == 0:
                await self.send_embed(ctx, "Invalid input!", f"NPCs do not have levels.", discord.Color.red())
                connection.close()
                return
            if role == 2:
                await self.send_embed(ctx, "Invalid input!", f"An alter's level is linked to the parent.", discord.Color.red())
                connection.close()
                return
            if level <= 3:
                await self.send_embed(ctx, "Invalid input!", f"**{name}** cannot go below level **3**.", discord.Color.red())
                connection.close()
                return
        
            new_level = level - 1
        
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?",
                (new_level, guild_id, ctx.author.id, name)
            )
            cursor.execute(
                "UPDATE Tuppers SET tupper_level = ? WHERE guild_id = ? AND owner_id = ? AND parent = ?",
                (new_level, guild_id, ctx.author.id, name)
            )
        
            connection.commit()
            connection.close()
        
            await self.send_embed(ctx, f"{ctx.author.display_name} levels down a tupper.", f"**{name}** lost a level and is now at level **{new_level}**.", discord.Color.purple())
        
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def collect(self, ctx):
        await self.pre_command_checks(ctx, self._collect_task)
    
    async def _collect_task(self, ctx, guild_result):
        try:
            guild_id = guild_result[0]
            cooldown = guild_result[3]
            owner_id = ctx.author.id
    
            total_collected = 0
            pool_xp = 0
            collection_messages = []
            cooldown_ready = False
            any_rpxp_found = False
            latest_last_collection = 0
    
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
    
                cursor.execute(
                    "SELECT tupper_name, tupper_role, tupper_rpxp, last_collection FROM Tuppers WHERE guild_id = ? AND owner_id = ?",
                    (guild_id, owner_id)
                )
                tupper_data = cursor.fetchall()
    
                for name, role, rpxp, last_collection in tupper_data:
                    rpxp = round(rpxp or 0)
                    last_collection = last_collection or 0
    
                    if role == 2:
                        continue  # Skip alters
    
                    if self.time - last_collection > cooldown:
                        cooldown_ready = True
                        cursor.execute(
                            "UPDATE Tuppers SET last_collection = ? WHERE guild_id = ? AND owner_id = ? AND tupper_name = ?",
                            (self.time, guild_id, owner_id, name)
                        )
                    latest_last_collection = max(latest_last_collection, last_collection)
    
                    if rpxp > 0:
                        any_rpxp_found = True
                        total_collected += rpxp
                        if role == 1:
                            collection_messages.append(f"- **{name}** collects **{rpxp}** rp xp.")
                        else:
                            pool_xp += rpxp
    
                if pool_xp:
                    collection_messages.append(f"- **{pool_xp}** XP from your NPCs can be applied to a PC of your choice.")
    
                if not cooldown_ready:
                    await self.send_embed(ctx, "Invalid input!", f"Collection is on **cooldown**. You can collect rp xp again **<t:{latest_last_collection + cooldown}:R>**.", discord.Color.red())
                    return
    
                if not any_rpxp_found:
                    await self.send_embed(ctx, "Invalid input!", "None of your characters have **any** rp xp to collect. Please play some more and try again later.", discord.Color.red())
                    return
    
                # Update user RPXP totals
                cursor.execute(
                    "SELECT monthly_rpxp, total_rpxp FROM Users WHERE guild_id = ? AND user_id = ?",
                    (guild_id, owner_id)
                )
                user_data = cursor.fetchone()
                if user_data:
                    monthly, total = user_data
                    monthly += total_collected
                    total += total_collected
    
                    cursor.execute(
                        "UPDATE Users SET monthly_rpxp = ?, total_rpxp = ? WHERE guild_id = ? AND user_id = ?",
                        (round(monthly), round(total), guild_id, owner_id)
                    )
    
                # Reset tupper XP
                cursor.execute(
                    "UPDATE Tuppers SET tupper_rpxp = 0 WHERE guild_id = ? AND owner_id = ?",
                    (guild_id, owner_id)
                )
    
                connection.commit()
    
            message = "\n".join(collection_messages)
            await self.send_embed(ctx, f"{ctx.author.display_name} collects rp xp", message, discord.Color.purple())
    
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def list(self, ctx, content: str):
        await self.pre_command_checks(ctx, self._list_task, content)
    
    async def _list_task(self, ctx, guild_result, content):
        try:
            guild_id = guild_result[0]
            owner_id = ctx.author.id
            display_name = ctx.author.display_name
        
            if content:
                if content.lower() != "self":
                    try:
                        owner_id = int(content)
                        member = ctx.guild.get_member(owner_id) or await ctx.guild.fetch_member(owner_id)
                        display_name = member.display_name
                    except ValueError:
                        await self.send_embed(ctx, "Invalid input!", "Argument must be `self` or a valid user ID.", discord.Color.red())
                        return
                    except discord.NotFound:
                        await self.send_embed(ctx, "Invalid input!", "ID does not belong to a server member.", discord.Color.red())
                        return
        
            pcs, alters, npcs = [], [], []
        
            with sqlite3.connect("./RPXP_databank.db") as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM Tuppers WHERE guild_id = ? AND owner_id = ?", (guild_id, owner_id))
                results = cursor.fetchall()
        
            for row in results:
                tag = row[2]
                name = row[3]
                role = row[4]
                level = row[5]
                parent = row[9]
        
                if role == 1:
                    pcs.append(f"{name} {level} | `{tag}`")
                elif role == 0:
                    npcs.append(f"{name} | `{tag}`")
                elif role == 2:
                    alters.append(f"{name} | `{tag}` | Parented to: {parent}")
        
            if not (pcs or alters or npcs):
                description = f"{display_name} has no registered tuppers."
                color = discord.Color.red()
            else:
                description = f"{display_name} has the following tuppers:\n"
                if pcs:
                    description += "\n__**PCs:**__\n" + "\n".join(f"- {pc}" for pc in pcs)
                if alters:
                    description += "\n\n__**Alters:**__\n" + "\n".join(f"- {alter}" for alter in alters)
                if npcs:
                    description += "\n\n__**NPCs:**__\n" + "\n".join(f"- {npc}" for npc in npcs)
                color = discord.Color.purple()
        
            embed_message = discord.Embed(
                title=f"{display_name}'s tupper list.",
                description=description,
                color=color
            )
            embed_message.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar)
        
            await ctx.send(embed=embed_message)
        
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def helpme(self, ctx):
        await self.pre_command_checks(ctx, self._helpme_task)
        
    async def _helpme_task(self, ctx, guild_result):
        try:
            
            message = "These are all the commands and their function: \n"
    
            message += f"\n\n**`{self.prefix}settings`**: \n- Shows the current settings of the bot on this server."
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
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def msummary(self, ctx):
        try:
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
    
            total_words = round(total_words)
            total_xp = round(total_xp)
            avg_words = round(avg_words)
            avg_xp = round(avg_xp)
    
            top_user = None
            top_words = 0
    
            for row in users:
                user_id = row[1]
                user_words = row[2]
                if user_words > top_words:
                    top_words = round(user_words)
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
                    embed_message.set_author(name=f"Top User: {member.display_name} with {top_words} words", icon_url=member.display_avatar.url)
                else:
                    embed_message.set_author(name=f"Top User: <@{top_user_id}> with {top_words} XP!")
    
            if ctx.guild.icon:
                embed_message.set_image(url=ctx.guild.icon.url)
    
            await ctx.send(embed=embed_message)
            connection.close()
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @commands.command()
    async def tsummary(self, ctx):
        try:
            await ctx.message.delete()
            if ctx.author.bot:
                return
            
            #"""Manually triggers the monthly stats summary for this server."""
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
    
            total_words = int(total_words)
            total_xp = int(total_xp)
            avg_words = int(avg_words)
            avg_xp = int(avg_xp)
    
            top_user = None
            top_words = 0
    
            for row in users:
                user_id = row[1]
                user_words = row[4]
                if user_words > top_words:
                    top_words = round(user_words)
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
                    embed_message.set_author(name=f"Top User: {member.display_name} with {top_words} words", icon_url=member.display_avatar.url)
                else:
                    embed_message.set_author(name=f"Top User: <@{top_user_id}> with {top_words} words!")
    
            if ctx.guild.icon:
                embed_message.set_image(url=ctx.guild.icon.url)
    
            await ctx.send(embed=embed_message)
            connection.close()
        except Exception as e:
            print(f"Command Error in {ctx.command.name}: {e}")

    @tasks.loop(seconds=1)
    async def fetch_time(self):
        dt = datetime.datetime.now(timezone.utc) 
        utc_time = dt.replace(tzinfo=timezone.utc) 
        self.time = int(utc_time.timestamp())

    @commands.Cog.listener()
    async def on_ready(self):
        self.fetch_time.start()
        print("commands.py is ready")

async def setup(client):
    await client.add_cog(Commands(client))
