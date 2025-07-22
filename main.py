import discord
from discord.ext import commands, tasks
import asyncio
import os
from keep_alive import keep_alive
import pytchat
from datetime import datetime
import re
from rapidfuzz import fuzz

# إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ✅ السماح فقط لمن لديهم الرتبة المحددة
ALLOWED_ROLE_NAME = "admin"

# ✅ فلترة الرسائل لمنع التكرار
recent_messages = {}  # {username: [list of messages]}

# ✅ عدد البثوث التي نسمح بتخزينها مؤقتًا (جلسة واحدة)
current_session_id = None

# ✅ إعدادات الاتصال بين اليوتيوب والديسكورد
is_streaming = False
chat = None
channel = None

def is_similar(msg1, msg2):
    msg1 = re.sub(r"\W+", "", msg1.lower())
    msg2 = re.sub(r"\W+", "", msg2.lower())
    similarity = fuzz.ratio(msg1, msg2)
    return similarity > 90

async def send_to_discord(author, message, timestamp):
    global recent_messages
    if author not in recent_messages:
        recent_messages[author] = []
    for old_msg in recent_messages[author]:
        if is_similar(old_msg, message):
            return  # تجاهل الرسالة إذا كانت مشابهة جدًا
    recent_messages[author].append(message)
    if len(recent_messages[author]) > 20:
        recent_messages[author].pop(0)

    embed = discord.Embed(description=message, color=discord.Color.green())
    embed.set_author(name=author)
    embed.set_footer(text=timestamp)
    await channel.send(embed=embed)

# ✅ مهمة جلب رسائل البث
@tasks.loop(seconds=1)
async def fetch_youtube_chat():
    global chat, is_streaming, recent_messages
    try:
        if chat and chat.is_alive():
            for c in chat.get().sync_items():
                await send_to_discord(c.author.name, c.message, c.datetime)
        else:
            is_streaming = False
            fetch_youtube_chat.stop()
            recent_messages = {}  # حذف التخزين المؤقت
            await channel.send("🔴 البث تم إغلاقه. تم إيقاف إرسال الرسائل تلقائيًا.")
    except Exception as e:
        print("خطأ في جلب الشات:", e)

# ✅ أمر تشغيل البث
@bot.command()
@commands.has_role(ALLOWED_ROLE_NAME)
async def start_youtube(ctx, video_id):
    global chat, is_streaming, channel, current_session_id, recent_messages
    if is_streaming:
        await ctx.send("✅ البث يعمل بالفعل.")
        return
    try:
        chat = pytchat.create(video_id=video_id)
        is_streaming = True
        channel = ctx.channel
        current_session_id = video_id
        recent_messages = {}
        fetch_youtube_chat.start()
        await ctx.send("✅ تم بدء مراقبة البث الحي.")
    except Exception as e:
        await ctx.send(f"❌ فشل في بدء البث: {e}")

# ✅ أمر شرح الاستخدام
@bot.command()
async def explain(ctx):
    await ctx.send("""
📌 **How to use `!start_youtube`**
Use the command followed by the YouTube video URL or ID:

`!start_youtube https://www.youtube.com/watch?v=VIDEO_ID`
Or simply:
`!start_youtube VIDEO_ID`

🔍 The bot will start fetching messages from the live chat.
💡 Duplicate messages from the same person (even slightly modified) will be filtered.
🛑 When the stream ends, a message will be sent and the session cache will be cleared.
""")

# ✅ تشغيل البوت
keep_alive()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
