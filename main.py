import os
import discord
from discord.ext import commands
import yt_dlp
from datetime import datetime
import asyncio

from myserver import server_on

MAIN_CHANNEL_ID = 1414923035864993884
ADMIN_IDS = [1424617349306253414, 1252736935680540695, 1290736050204835913]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ 🎵 CONFIG ------------------

ytdl_format_options = {
    'format': 'bestaudio',
    'quiet': True
}

ffmpeg_options = {
    'options': '-vn',
    'executable': "C:/Users/acer/Downloads/ffmpeg-8.1-essentials_build/ffmpeg-8.1-essentials_build/bin/ffmpeg.exe"
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# ------------------ 🎶 MUSIC QUEUE ------------------

music_queue = []
is_playing = False

async def play_next(ctx):
    global is_playing

    if len(music_queue) == 0:
        is_playing = False
        return

    is_playing = True
    url = music_queue.pop(0)

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    if 'url' not in info:
        await ctx.send("❌ โหลดเพลงไม่ได้")
        return

    stream_url = info['url']

    vc = ctx.voice_client

    def after_play(error):
        if error:
            print(error)
        fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        try:
            fut.result()
        except:
            pass

    vc.play(discord.FFmpegPCMAudio(stream_url, **ffmpeg_options), after=after_play)

# ------------------ 💬 COOLDOWN ------------------

last_reply = {}

def can_reply(user_id, cooldown=5):
    now = datetime.now().timestamp()
    if user_id not in last_reply or now - last_reply[user_id] > cooldown:
        last_reply[user_id] = now
        return True
    return False

# ------------------ 📊 INVITE SYSTEM ------------------

invites_cache = {}
invite_counts = {}
joined_users = {}

# ------------------ READY ------------------

@bot.event
async def on_ready():
    print(f"ล็อกอินแล้ว: {bot.user}")

    for guild in bot.guilds:
        invites = await guild.invites()
        invites_cache[guild.id] = {invite.code: invite.uses for invite in invites}

# ------------------ MESSAGE ------------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 🎵 ตรวจลิงก์ youtube
    if "youtube.com/watch" in message.content or "youtu.be/" in message.content:
        if message.author.voice:
            channel = message.author.voice.channel
            vc = message.guild.voice_client

            if not vc:
                vc = await channel.connect()
            elif vc.channel != channel:
                await vc.move_to(channel)

            music_queue.append(message.content)

            if not vc.is_playing() and not is_playing:
                await play_next(message.channel)
            else:
                await message.channel.send("➕ เพิ่มเพลงเข้าคิวแล้ว")

        else:
            await message.channel.send("❌ เข้า VC ก่อน")

    # 💬 คำพูดเล่น (มี cooldown)
    if "ลูคัส" in message.content:
        if can_reply(message.author.id):
            await message.channel.send("ครับ")

    if "สบายดีไหม" in message.content:
        if can_reply(message.author.id):
            await message.channel.send("สบายดีครับ")

    await bot.process_commands(message)

# ------------------ 👋 JOIN ------------------

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(MAIN_CHANNEL_ID)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    await channel.send(f"👋 ยินดีต้อนรับ {member.mention} ถึงนิว")

    inviter = None

    try:
        new_invites = await member.guild.invites()
        old_invites = invites_cache.get(member.guild.id, {})

        for invite in new_invites:
            if invite.code in old_invites:
                if invite.uses > old_invites[invite.code]:
                    inviter = invite.inviter
                    break

        invites_cache[member.guild.id] = {invite.code: invite.uses for invite in new_invites}

    except Exception as e:
        print(e)

    inviter_name = inviter.name if inviter else "ไม่ทราบ"

    if inviter:
        invite_counts[inviter.id] = invite_counts.get(inviter.id, 0) + 1
        joined_users[member.id] = inviter.id

    # ✅ ลดการยิง API
    for admin_id in ADMIN_IDS:
        user = bot.get_user(admin_id)
        if not user:
            try:
                user = await bot.fetch_user(admin_id)
            except:
                continue

        try:
            await user.send(
                f"📥 มีคนเข้าใหม่\n"
                f"👤 ชื่อ: {member.name}\n"
                f"🔗 เชิญโดย: {inviter_name}\n"
                f"⏰ เวลา: {now}"
            )
        except:
            pass

# ------------------ ❌ LEAVE ------------------

@bot.event
async def on_member_remove(member):
    inviter_id = joined_users.get(member.id)

    if inviter_id:
        invite_counts[inviter_id] = max(invite_counts.get(inviter_id, 1) - 1, 0)
        del joined_users[member.id]

# ------------------ 🏆 COMMAND ------------------

@bot.command()
async def invites(ctx):
    if not invite_counts:
        await ctx.send("ยังไม่มีข้อมูล")
        return

    sorted_invites = sorted(invite_counts.items(), key=lambda x: x[1], reverse=True)

    text = "🏆 อันดับคนเชิญ:\n"
    for i, (user_id, count) in enumerate(sorted_invites[:10], start=1):
        user = bot.get_user(user_id)
        if not user:
            user = await bot.fetch_user(user_id)

        text += f"{i}. {user.name} - {count} คน\n"

    await ctx.send(text)

# ------------------ START ------------------

server_on()
bot.run(os.getenv('TOKEN'))
