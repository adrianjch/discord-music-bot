import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get
from datetime import datetime
import voice_chat
import Music
import advanced_music
import operator

intents = discord.Intents.all()

botToken = open("data/token.txt", "r").read()
bot = commands.Bot(command_prefix='$', intents=intents)

vc = voice_chat.Helper()

def formatSeconds(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 60*60:
        return f"{int(seconds/60)}m {seconds%60}s"
    return f"{int(seconds/3600)}h {int(seconds/60)%60}m"

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(status=discord.Status.offline)
    print('Logged in')
    now = int(datetime.timestamp(datetime.now()))
    for member in bot.guilds[0].members:
        if member.voice != None and member.voice.channel != None:
            if not vc.userConnectedToday(member.id):
                vc.memberConnected(member.id)
            vc.users[member.id].lastConnected = now

@bot.listen()
async def on_voice_state_update(member, before, after):
    now = int(datetime.timestamp(datetime.now()))
    guild = member.guild
    id = member.id
    if after.channel != None:
        if not vc.userConnectedToday(id):
            vc.memberConnected(id)
        vc.updateMember(id)
    else: # Someone just disconnected
        vc.users[id].seconds += now - vc.users[id].lastConnected
        vc.users[id].lastConnected = -1
        # Check if they were forcefully disconnected by someone else
        entries = [entry async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_disconnect)]
        if vc.albertKicked(entries[0]):
            vc.increaseAlbertKick(entries[0], id)
            await bot.get_channel(818953029390303252).send(f"L'Albert ha expulsat a {member.mention} ({vc.albertKickCounter} expulsions)")

@bot.tree.command(name = "test", description = "My first application Command") #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def first_command(interaction):
    await interaction.response.send_message("Hello!")

@bot.command()
async def stats(ctx):
    # Update stats
    for member in bot.guilds[0].members:
        if member.voice != None and member.voice.channel != None:
            vc.updateMember(member.id)
    # Create and send embed
    embed = discord.Embed(title="**NOOBLY VOICE CHAT STATS**", color=0x0055ff)
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/254747098182975488/892462016ca948399dbd0b4dc001ca20.webp")
    description = ""
    leaderboard = sorted(vc.users.items(), key=lambda item: item[1].days*99999+item[1].seconds, reverse=True)
    for i, id in enumerate(leaderboard):
        user = await bot.fetch_user(id[0])
        description += f"**{i+1}.** {user.mention} | "
        description += f"{id[1].days} day{'s' if id[1].days != 1 else ''} | "
        description += formatSeconds(id[1].seconds) + "\n"
    embed.description = description
    embed.set_footer(text="stufu")
    await ctx.send(embed=embed)

@bot.command()
async def kicks(ctx):
    # Create and send embed
    embed = discord.Embed(title="**ALBERT KICK STATS**", color=0x0055ff)
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/1024825707949461595/af4591e997f889489042da806dc5f677.webp?size=100")
    description = ""
    leaderboard = sorted(vc.users.items(), key=lambda item: item[1].kickedCount, reverse=True)
    for i, id in enumerate(leaderboard):
        if id[1].kickedCount < 1:
            break
        user = await bot.fetch_user(id[0])
        description += f"**{i+1}.** {user.mention} "
        description += f"({id[1].kickedCount})\n"
    embed.description = description
    embed.set_footer(text="stufu")
    await ctx.send(embed=embed)

async def main():
    async with bot:
        await bot.add_cog(advanced_music.Music(bot))
        await bot.start(botToken)
asyncio.run(main())