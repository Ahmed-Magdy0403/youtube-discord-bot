import discord
from discord.ext import commands, tasks
import asyncio
import os
from keep_alive import keep_alive
import pytchat
from datetime import datetime
import threading

# إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# متغيرات للتحكم في الشات
active_chats = {}
message_history = set()  # لتجنب الرسائل المتكررة

@bot.event
async def on_ready():
    print(f'✅ {bot.user} متصل بـ Discord!')
    print(f'🔗 البوت موجود في {len(bot.guilds)} سيرفر')
    print(f'🆔 Bot ID: {bot.user.id}')
    await bot.change_presence(activity=discord.Game(name="!commands"))

@bot.command(name='hello')
async def hello(ctx):
    await ctx.send('🎬 مرحباً! بوت YouTube Live Chat جاهز للعمل!\n'
                   'استخدم `!start_youtube VIDEO_ID` لبدء نقل الرسائل')

@bot.command(name='start_youtube')
async def start_youtube_chat(ctx, video_id: str = None):
    # ✅ منع تنفيذ الأمر في الخاص
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("❌ هذا الأمر لا يعمل في الخاص! الرجاء استخدامه في روم داخل سيرفر.")
        return
    if not video_id:
        await ctx.send('❌ يرجى إدخال كود الفيديو:\n`!start_youtube VIDEO_ID`\n'
                      'مثال: `!start_youtube dQw4w9WgXcQ`')
        return

    channel_id = ctx.channel.id

    if channel_id in active_chats:
        await ctx.send('⚠️ يوجد شات نشط بالفعل في هذه القناة! استخدم `!stop_youtube` لإيقافه أولاً')
        return

    await ctx.send(f'🔄 محاولة الاتصال بـ YouTube Live Chat...\n📺 Video ID: `{video_id}`')

    try:
        chat = pytchat.create(video_id=video_id)
        if not chat.is_alive():
            await ctx.send('❌ لا يمكن الاتصال بالشات. تأكد من أن الفيديو يحتوي على Live Chat نشط')
            return

        active_chats[channel_id] = {'chat': chat, 'running': True}

        embed = discord.Embed(
            title="✅ تم الاتصال بنجاح!",
            description=f"بدء نقل رسائل YouTube Live Chat",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="📺 Video ID", value=video_id, inline=True)
        embed.add_field(name="📍 قناة Discord", value=ctx.channel.mention, inline=True)
        embed.set_footer(text="© 2025 Ahmed Magdy", icon_url="https://cdn.discordapp.com/emojis/741243683501817978.png")
        await ctx.send(embed=embed)

        bot.loop.create_task(monitor_youtube_chat(ctx, channel_id))

    except Exception as e:
        await ctx.send(f'❌ خطأ في الاتصال: ```{str(e)}```')

async def monitor_youtube_chat(ctx, channel_id):
    global message_history  # ✅ مهم لحل المشكلة

    chat_data = active_chats.get(channel_id)
    if not chat_data:
        return

    chat = chat_data['chat']
    message_count = 0

    try:
        while chat.is_alive() and chat_data.get('running', False):
            loop = asyncio.get_event_loop()
            try:
                chat_data_result = await loop.run_in_executor(None, chat.get)
                items = chat_data_result.sync_items()
            except Exception as e:
                print(f"خطأ في قراءة الشات: {e}")
                await asyncio.sleep(5)
                continue

            for c in items:
                if not chat_data.get('running', False):
                    break

                message_content = c.message.strip() if c.message else ""
                message_key = f"{c.author.name}:{message_content}"  # ✅ حذف datetime

                # تجاهل الرسائل المتكررة
                if message_key in message_history:
                    continue

                message_history.add(message_key)

                # تقليل عدد الرسائل المحفوظة لتقليل استهلاك الذاكرة
                if len(message_history) > 300:
                    message_history = set(list(message_history)[-200:])

                # تنسيق الوقت
                try:
                    if c.datetime:
                        dt = datetime.fromisoformat(c.datetime.replace('Z', '+00:00'))
                        timestamp = dt
                except:
                    timestamp = datetime.now()

                if not message_content:
                    message_content = "*رسالة فارغة او ايموجي*"
                elif len(message_content) > 800:
                    message_content = message_content[:800] + "..."

                embed = discord.Embed(
                    title="🎬 **YouTube Live Chat**",
                    description=f"### 👤 **{c.author.name}**\n\n### 💬 {message_content}",
                    color=0xff0000,
                    timestamp=timestamp
                )

                if hasattr(c.author, 'imageUrl') and c.author.imageUrl:
                    embed.set_thumbnail(url=c.author.imageUrl)

                message_count += 1
                embed.set_footer(
                    text=f"📺 YouTube Live Chat • رسالة #{message_count} • 🔥",
                    icon_url="https://upload.wikimedia.org/wikipedia/commons/4/42/YouTube_icon_%282013-2017%29.png"
                )

                try:
                    await ctx.send(embed=embed)
                    print(f"✅ تم إرسال رسالة من {c.author.name}: {c.message[:50]}...")
                    await asyncio.sleep(0.5)
                except Exception as send_error:
                    print(f"❌ خطأ في إرسال الرسالة: {send_error}")

            await asyncio.sleep(3)

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ خطأ في مراقبة الشات",
            description=f"```{str(e)}```",
            color=0xff0000
        )
        try:
            await ctx.send(embed=error_embed)
        except:
            pass
    finally:
        if channel_id in active_chats:
            del active_chats[channel_id]

@bot.command(name='stop_youtube')
async def stop_youtube_chat(ctx):
    channel_id = ctx.channel.id

    if channel_id not in active_chats:
        await ctx.send('⚠️ لا يوجد شات YouTube نشط في هذه القناة')
        return

    active_chats[channel_id]['running'] = False
    del active_chats[channel_id]

    embed = discord.Embed(
        title="⏹️ تم إيقاف YouTube Chat",
        description="تم إيقاف نقل الرسائل بنجاح",
        color=0xffa500
    )
    embed.set_footer(text="© 2025 Ahmed Magdy", icon_url="https://cdn.discordapp.com/emojis/741243683501817978.png")
    await ctx.send(embed=embed)

@bot.command(name='status')
async def status(ctx):
    active_count = len(active_chats)

    embed = discord.Embed(
        title="📊 حالة البوت",
        color=0x00ff00 if active_count > 0 else 0x999999
    )

    embed.add_field(name="🔗 الاتصال", value="متصل ✅", inline=True)
    embed.add_field(name="📺 الشاتات النشطة", value=f"{active_count}", inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)

    if active_count > 0:
        channels = [f"<#{channel_id}>" for channel_id in active_chats.keys()]
        embed.add_field(name="📍 الرومات النشطة", value="\n".join(channels), inline=False)

    embed.set_footer(text="© 2025 Ahmed Magdy", icon_url="https://cdn.discordapp.com/emojis/741243683501817978.png")
    await ctx.send(embed=embed)

@bot.command(name='commands')
async def commands_help(ctx):
    embed = discord.Embed(
        title="🎬 YouTube Live Chat Bot - المساعدة",
        description="بوت تنظيم رسايل اللايف بتقنية بسيطة وسلسة",
        color=0x0099ff
    )

    commands_text = """
    `!start_youtube VIDEO_ID` - بدء نقل رسائل من يوتيوب لايف
    `!stop_youtube` - إيقاف النقل فوراً
    `!status` - عرض تفاصيل حالة البوت
    `!hello` - تحية البوت والترحيب
    `!commands` - عرض قائمة المساعدة الكاملة
    """

    embed.add_field(name="📋 الأوامر المتاحة", value=commands_text, inline=False)
    embed.add_field(name="💡 نصائح مهمة", 
                   value="• تأكد من أن الفيديو يحتوي على Live Chat نشط\n"
                        "• البوت يتجنب الرسائل المتكررة والسبام تلقائياً\n"
                        "• يمكن تشغيل شات واحد فقط لكل قناة Discord\n"
                        "• البوت يدعم الرسائل العربية والإنجليزية", 
                   inline=False)

    embed.set_footer(text="© 2025 Ahmed Magdy - جميع الحقوق محفوظة", 
                    icon_url="https://cdn.discordapp.com/emojis/741243683501817978.png")

    await ctx.send(embed=embed)

async def main():
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ لم يتم العثور على التوكن")
        return
    try:
        print("🚀 بدء تشغيل البوت...")
        await bot.start(token)
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    asyncio.run(main())
