# main.py (CLEANED)
# Credit: Tg - @Tushar0125
# Ask Doubt on telegram @Tushar0125

import os
import re
import sys
import json
import time
import logging
import random
import requests
import asyncio
import cloudscraper
from typing import Dict, List, Tuple

# Third-party libs used by the bot
import m3u8
import ffmpeg  # keep if used by helper functions
import yt_dlp
from yt_dlp import YoutubeDL
from pytube import YouTube, Playlist

# aiohttp and pyrogram
from aiohttp import ClientSession
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait

# Local imports (keep as-is if these exist in your repo)
from core import *  # careful: wildcard import; kept for backward compatibility
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN

# --- Basic config / logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment / constants
COOKIES_FILE_PATH = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")
OWNER_ID = 5663132413
SUDO_USERS = [5663132413]
AUTH_CHANNELS = [-100339820439]

# Helper: authorization check
def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS or user_id in AUTH_CHANNELS

# Pyrogram bot client
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Inline keyboard for /start
keyboard = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("🇮🇳 ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ 🇮🇳", url="https://t.me/Tushar0125")],
        [InlineKeyboardButton("🔔 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 🔔", url="https://t.me/TxtToVideoUpdateChannel")],
        [InlineKeyboardButton("🦋 ғᴏʟʟᴏᴡ ᴜs 🦋", url="https://t.me/TxtToVideoUpdateChannel")]
    ]
)

# Some images for start message (kept as a small list)
IMAGE_URLS = [
    "https://graph.org/file/996d4fc24564509244988-a7d93d020c96973ba8.jpg",
    "https://graph.org/file/96d25730136a3ea7e48de-b0a87a529feb485c8f.jpg",
]
RANDOM_IMAGE_URL = random.choice(IMAGE_URLS)
DEFAULT_CREDIT = "[𝗧𝘂𝘀𝗵𝗮𝗿](https://t.me/Tushar0125)"

# simple utility: reply with random emoji
async def show_random_emojis(message: Message):
    emojis = ['🎊', '🔮', '😎', '⚡️', '🚀', '✨', '💥', '🎉', '🥂', '🍾', '🤖', '❤️‍🔥', '🕊️', '💃', '🥳']
    return await message.reply_text(random.choice(emojis))

# ------------------------
# Basic commands
# ------------------------

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    caption = (
        "**ʜᴇʟʟᴏ👋**\n\n"
        "➠ **ɪ ᴀᴍ ᴛxᴛ ᴛᴏ ᴠɪᴅᴇᴏ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ.**\n"
        "➠ **ғᴏʀ ᴜsᴇ ᴍᴇ sᴇɴᴅ /tushar.**\n"
        "➠ **ғᴏʀ ɢᴜɪᴅᴇ sᴇɴᴅ /help.**"
    )
    try:
        await client.send_photo(chat_id=message.chat.id, photo=RANDOM_IMAGE_URL, caption=caption, reply_markup=keyboard)
    except Exception:
        # fallback text
        await message.reply_text("Hello! Use /help to see commands.")

@bot.on_message(filters.command("stop"))
async def stop_handler(_, m: Message):
    await m.reply_text("**Stopped** 🚦", quote=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("restart"))
async def restart_handler(_, m: Message):
    if not is_authorized(m.from_user.id):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("🔮 Restarting...", quote=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

# ------------------------
# Cookie upload command
# ------------------------

@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    if not is_authorized(m.from_user.id):
        await m.reply_text("🚫 You are not authorized to use this command.")
        return

    await m.reply_text("Please upload cookies file (.txt).", quote=True)
    try:
        uploaded: Message = await client.listen(m.chat.id)
        if not uploaded.document or not uploaded.document.file_name.endswith(".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return
        path = await uploaded.download()
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(COOKIES_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        await m.reply_text("✅ Cookies updated and saved.")
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")

# ------------------------
# e2t command (edit text file)
# ------------------------

@bot.on_message(filters.command("e2t"))
async def edit_txt(client: Client, message: Message):
    """
    Ask user to upload a .txt with lines like:
    Title: url
    - topic
    This endpoint sorts and returns a cleaned .txt file
    """
    await message.reply_text("Send your `.txt` file containing subjects, links, and topics.")
    try:
        uploaded: Message = await bot.listen(message.chat.id)
        if not uploaded.document or not uploaded.document.file_name.lower().endswith(".txt"):
            await message.reply_text("Please upload a valid .txt file.")
            return
        # Save file in working dir (or /tmp)
        saved_path = await uploaded.download()
        with open(saved_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        subjects: Dict[str, Dict[str, List[str]]] = {}
        current = None
        for raw in lines:
            ln = raw.strip()
            if not ln:
                continue
            if ":" in ln:
                title, url = ln.split(":", 1)
                title = title.strip()
                url = url.strip()
                if title not in subjects:
                    subjects[title] = {"links": [], "topics": []}
                subjects[title]["links"].append(url)
                current = title
            elif ln.startswith("-") and current:
                subjects[current]["topics"].append(ln.lstrip("- ").strip())

        # Sort subjects and topics
        sorted_items = sorted(subjects.items())
        for _, data in sorted_items:
            data["topics"].sort()

        out_name = "edited_output.txt"
        with open(out_name, "w", encoding="utf-8") as out:
            for title, data in sorted_items:
                for link in data["links"]:
                    out.write(f"{title}:{link}\n")
                for topic in data["topics"]:
                    out.write(f"- {topic}\n")

        await message.reply_document(document=out_name, caption="Edited file")
        # cleanup
        try:
            os.remove(saved_path)
        except Exception:
            pass
        try:
            os.remove(out_name)
        except Exception:
            pass
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# ------------------------
# yt2txt (owner only)
# ------------------------

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_videos_with_ytdlp(url: str) -> Tuple[str, dict]:
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                title = result.get('title', 'Unknown_Playlist')
                videos = {}
                for entry in result['entries']:
                    video_url = entry.get('url') or entry.get('webpage_url')
                    video_title = entry.get('title') or "Unknown Title"
                    if video_url:
                        videos[video_title] = video_url
                return title, videos
    except Exception as e:
        logging.warning("ytdlp error: %s", e)
    return None, None

def save_to_file(videos: dict, name: str) -> str:
    filename = f"{sanitize_filename(name)}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for t, u in videos.items():
            f.write(f"{t}: {u}\n")
    return filename

@bot.on_message(filters.command("yt2txt"))
async def yt2txt_handler(client: Client, message: Message):
    if message.chat.id != OWNER_ID:
        await message.reply_text("This command is owner-only.")
        return
    await message.delete()
    prompt = await message.reply_text("Send YouTube playlist/channel URL:")
    try:
        input_msg = await client.listen(prompt.chat.id)
        url = input_msg.text.strip()
        await input_msg.delete()
        await prompt.delete()
        title, videos = get_videos_with_ytdlp(url)
        if videos:
            fname = save_to_file(videos, title or "playlist")
            await message.reply_document(document=fname, caption=f"`{title}`")
            try:
                os.remove(fname)
            except Exception:
                pass
        else:
            await message.reply_text("Unable to retrieve videos. Check URL.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# ------------------------
# userlist and help
# ------------------------

@bot.on_message(filters.command("userlist") & filters.user(SUDO_USERS))
async def list_users(client: Client, msg: Message):
    if SUDO_USERS:
        users_list = "\n".join([f"User ID : `{u}`" for u in SUDO_USERS])
        await msg.reply_text(f"SUDO_USERS :\n{users_list}")
    else:
        await msg.reply_text("No sudo users.")

@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot\n"
        "`/tushar` - Download & upload files (sudo)\n"
        "`/restart` - Restart the bot\n"
        "`/stop` - Stop bot\n"
        "`/cookies` - Upload cookies file\n"
        "`/e2t` - Edit txt file\n"
        "`/yt2txt` - Create txt of yt playlist (owner)\n"
        "`/sudo add <id>` - Add sudo (owner)\n"
        "`/sudo remove <id>` - Remove sudo (owner)\n"
        "`/userlist` - List sudo users\n"
    )
    await msg.reply_text(help_text)

# ------------------------
# /tushar: main uploader command (cleaned and simplified)
# ------------------------

# Use a safe tmp dir for file downloads
TMP_DIR = "/tmp/bot_files"
os.makedirs(TMP_DIR, exist_ok=True)

@bot.on_message(filters.command("tushar"))
async def upload_handler(bot_client: Client, m: Message):
    if not is_authorized(m.chat.id):
        await m.reply_text("🚫 You are not authorized to use this bot.")
        return

    editable = await m.reply_text("⚡ SEND TXT FILE")
    try:
        input_msg: Message = await bot.listen(editable.chat.id)
        if not input_msg.document:
            await editable.edit("Invalid input: please send a .txt file with URLs.")
            return
        # download the .txt
        downloaded_path = await input_msg.download(file_name=os.path.join(TMP_DIR, input_msg.document.file_name))
        await input_msg.delete(True)

        # read file and collect links
        with open(downloaded_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]

        links = []
        for ln in lines:
            # naive url extraction: keep full line
            links.append(ln)

        await editable.edit(f"Found {len(links)} links. Send starting index (1 for start):")
        start_msg: Message = await bot.listen(editable.chat.id)
        try:
            start_idx = int(start_msg.text.strip())
            if start_idx < 1:
                start_idx = 1
        except Exception:
            start_idx = 1
        await start_msg.delete(True)

        await editable.edit("Enter batch name (or send 1 to use default):")
        batch_msg: Message = await bot.listen(editable.chat.id)
        batch_name = batch_msg.text.strip()
        if batch_name == "1":
            batch_name = os.path.splitext(os.path.basename(downloaded_path))[0]
        await batch_msg.delete(True)

        await editable.edit("Enter resolution limit (e.g., 720) or send 0 for auto:")
        res_msg: Message = await bot.listen(editable.chat.id)
        try:
            max_height = int(res_msg.text.strip())
        except Exception:
            max_height = 0
        await res_msg.delete(True)

        await editable.edit("Enter credit (format: Name URL) or send 1 for default:")
        credit_msg: Message = await bot.listen(editable.chat.id)
        credit_input = credit_msg.text.strip()
        if credit_input == "1":
            credit_markdown = DEFAULT_CREDIT
        else:
            # try to parse "Name URL"
            parts = credit_input.split(None, 1)
            if len(parts) == 2:
                text, link = parts
                credit_markdown = f"[{text}]({link})"
            else:
                credit_markdown = credit_input or DEFAULT_CREDIT
        await credit_msg.delete(True)

        await editable.edit("Enter PW token or send 3 for none:")
        token_msg: Message = await bot.listen(editable.chat.id)
        token_input = token_msg.text.strip()
        if token_input == "3":
            token_input = None
        await token_msg.delete(True)

        await editable.edit("Send thumbnail URL or 'no' to skip:")
        thumb_msg: Message = await bot.listen(editable.chat.id)
        thumb_input = (thumb_msg.text or "").strip()
        await thumb_msg.delete(True)

        if thumb_input.lower() == "no" or not thumb_input:
            thumb = None
        else:
            thumb = thumb_input

        await editable.edit("Starting downloads...")

        # iterate links
        failed_count = 0
        index = start_idx
        total_links = len(links)
        for raw in links[start_idx - 1:]:
            name_safe = sanitize_filename(raw)[:60] or f"item_{index}"
            # Determine type
            lower = raw.lower()
            try:
                if any(lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                    # download image
                    scraper = cloudscraper.create_scraper()
                    resp = scraper.get(raw, timeout=30)
                    if resp.status_code == 200:
                        fname = os.path.join(TMP_DIR, f"{name_safe}.jpg")
                        with open(fname, "wb") as fh:
                            fh.write(resp.content)
                        await bot_client.send_photo(chat_id=m.chat.id, photo=fname,
                                                    caption=f"Image: {name_safe}\nBatch: {batch_name}\nCredit: {credit_markdown}")
                        try:
                            os.remove(fname)
                        except Exception:
                            pass
                        index += 1
                    else:
                        await bot_client.send_message(chat_id=m.chat.id, text=f"Failed to download image: {raw}")
                        failed_count += 1
                        index += 1
                elif any(lower.endswith(ext) for ext in [".pdf", ".zip"]):
                    # Use requests to download
                    resp = requests.get(raw, stream=True, timeout=30)
                    if resp.status_code == 200:
                        ext = ".pdf" if ".pdf" in lower else ".zip"
                        fname = os.path.join(TMP_DIR, f"{name_safe}{ext}")
                        with open(fname, "wb") as fh:
                            for chunk in resp.iter_content(chunk_size=8192):
                                fh.write(chunk)
                        await bot_client.send_document(chat_id=m.chat.id, document=fname,
                                                       caption=f"File: {name_safe}{ext}\nBatch: {batch_name}\nCredit: {credit_markdown}")
                        try:
                            os.remove(fname)
                        except Exception:
                            pass
                        index += 1
                    else:
                        await bot_client.send_message(chat_id=m.chat.id, text=f"Failed to download file: {raw}")
                        failed_count += 1
                        index += 1
                else:
                    # assume video or playlist URL -> use yt-dlp
                    # build format string based on max_height
                    if max_height and max_height > 0:
                        fmt = f"b[height<={max_height}][ext=mp4]/bv[height<={max_height}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
                    else:
                        fmt = "bestvideo+bestaudio/best"
                    out_name = os.path.join(TMP_DIR, f"{name_safe}.%(ext)s")
                    ytdl_cmd = [
                        "yt-dlp",
                        "-f", fmt,
                        "-o", out_name,
                        raw
                    ]
                    # use cookies if present
                    if os.path.exists(COOKIES_FILE_PATH):
                        ytdl_cmd[1:1] = ["--cookies", COOKIES_FILE_PATH]  # insert after command
                    # Run yt-dlp as subprocess (blocking, but okay here)
                    proc_cmd = " ".join(ytdl_cmd)
                    # try to download
                    os.system(proc_cmd)
                    # find downloaded file (approx)
                    found = None
                    for f in os.listdir(TMP_DIR):
                        if f.startswith(name_safe):
                            found = os.path.join(TMP_DIR, f)
                            break
                    if found:
                        try:
                            # Prefer sending as document to preserve video
                            await bot_client.send_document(chat_id=m.chat.id, document=found,
                                                           caption=f"Video: {name_safe}\nBatch: {batch_name}\nCredit: {credit_markdown}")
                        except Exception:
                            # fallback to send message with link
                            await bot_client.send_message(chat_id=m.chat.id,
                                                          text=f"Downloaded: {found}\nUnable to send via API.")
                        try:
                            os.remove(found)
                        except Exception:
                            pass
                        index += 1
                    else:
                        await bot_client.send_message(chat_id=m.chat.id, text=f"Failed to download video: {raw}")
                        failed_count += 1
                        index += 1
            except FloodWait as e:
                await bot_client.send_message(chat_id=m.chat.id, text=f"FloodWait: sleeping {e.x}s")
                await asyncio.sleep(e.x)
                continue
            except Exception as e:
                await bot_client.send_message(chat_id=m.chat.id, text=f"Error processing {raw}: {e}")
                failed_count += 1
                index += 1
                continue

        # final summary
        await bot_client.send_message(
            chat_id=m.chat.id,
            text=(
                f"Batch done ✅\nBatch: {batch_name}\nTotal links: {total_links}\n"
                f"Failed: {failed_count}\nCredit: {credit_markdown}"
            )
        )

        # cleanup input txt
        try:
            os.remove(downloaded_path)
        except Exception:
            pass

    except Exception as e:
        await editable.edit(f"Error: {e}")
        try:
            os.remove(downloaded_path)
        except Exception:
            pass

# ------------------------
# Sudo management command (add/remove)
# ------------------------

@bot.on_message(filters.command("sudo"))
async def sudo_command(bot_c: Client, message: Message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        await message.reply_text("You are not authorized.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 3:
            await message.reply_text("Usage: /sudo add <id> or /sudo remove <id>")
            return
        action = parts[1].lower()
        target = int(parts[2])
        if action == "add":
            if target not in SUDO_USERS:
                SUDO_USERS.append(target)
                await message.reply_text(f"Added {target} to sudo list.")
            else:
                await message.reply_text(f"{target} already in sudo list.")
        elif action == "remove":
            if target == OWNER_ID:
                await message.reply_text("Owner cannot be removed.")
            elif target in SUDO_USERS:
                SUDO_USERS.remove(target)
                await message.reply_text(f"Removed {target} from sudo.")
            else:
                await message.reply_text("User not in sudo list.")
        else:
            await message.reply_text("Unknown action.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# ------------------------
# Final entry point
# ------------------------

if __name__ == "__main__":
    # Running via bot.run() is recommended for pyrogram
    bot.run()
