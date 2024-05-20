import os
import subprocess
import aiohttp
import aiofiles
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from dotenv import load_dotenv
import asyncio
import time
from urllib.parse import urlparse, urljoin
from flask import Flask, request
import xml.etree.ElementTree as ET
import re

# Load environment variables
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 5000))  # Default to port 5000 if PORT is not set

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
server = Flask(__name__)

# Bento4 and FFmpeg bin directory path in the root directory
BENTO4_BIN_DIR = os.path.abspath("./bin")
FFMPEG_BIN_DIR = os.path.abspath("./ffmpeg")
os.environ["PATH"] += os.pathsep + BENTO4_BIN_DIR + os.pathsep + FFMPEG_BIN_DIR

@server.route("/")
def index():
    return "Bot is running"

@server.route("/keep_alive")
def keep_alive():
    return "Keeping the worker alive."

async def download_file(url, dest, message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded_size = 0
            start_time = time.time()
            async with aiofiles.open(dest, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        await f.write(chunk)
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        if elapsed_time >= 5:
                            speed = downloaded_size / elapsed_time / 1024
                            progress = (downloaded_size / total_size) * 100
                            try:
                                await message.edit_text(
                                    f"Downloading... {progress:.2f}% at {speed:.2f} KB/s"
                                )
                            except FloodWait as e:
                                await asyncio.sleep(e.value)
                            start_time = current_time
    return dest

async def download_mpd(url, dest_folder, status_message, video_id=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            mpd_content = await response.text()
    
    # Parse MPD file
    root = ET.fromstring(mpd_content)
    namespace = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
    base_url = urljoin(url, root.find('mpd:BaseURL', namespace).text if root.find('mpd:BaseURL', namespace) else '')
    
    segment_urls = {}
    for adaptation_set in root.findall('mpd:Period/mpd:AdaptationSet', namespace):
        for representation in adaptation_set.findall('mpd:Representation', namespace):
            mime_type = adaptation_set.get('mimeType')
            representation_id = representation.get('id')
            bandwidth = int(representation.get('bandwidth', 0))
            if representation_id not in segment_urls:
                segment_urls[representation_id] = {'mime_type': mime_type, 'bandwidth': bandwidth, 'segments': []}
            
            segment_template = representation.find('mpd:SegmentTemplate', namespace)
            if segment_template is not None:
                initialization = segment_template.get('initialization')
                media = segment_template.get('media')
                timescale = int(segment_template.get('timescale', 1))
                duration = int(segment_template.get('duration', 1))
                
                # Add initialization segment
                init_url = urljoin(base_url, initialization)
                segment_urls[representation_id]['segments'].append(init_url)
                
                # Add media segments
                for i in range(0, timescale, duration):
                    media_url = urljoin(base_url, media.replace('$Number$', str(i)))
                    segment_urls[representation_id]['segments'].append(media_url)

    # Select the best video quality or specified quality
    selected_rep_id = None
    if video_id:
        for rep_id in segment_urls.keys():
            if rep_id == video_id:
                selected_rep_id = rep_id
                break
        if not selected_rep_id:
            await status_message.edit_text("Specified video ID not found.")
            return None, None
    else:
        selected_rep_id = max(segment_urls.keys(), key=lambda rep_id: segment_urls[rep_id]['bandwidth'])

    # Download selected segments
    segment_files = []
    for i, segment_url in enumerate(segment_urls[selected_rep_id]['segments']):
        segment_file = os.path.join(dest_folder, f"segment_{i}.m4s")
        segment_files.append(segment_file)
        await download_file(segment_url, segment_file, status_message)
    
    return segment_files, selected_rep_id

async def decrypt_segments(input_files, keys, output_prefix, status_message):
    decrypted_files = []
    for i, input_file in enumerate(input_files):
        key = keys[i % len(keys)]
        output_file = f"{output_prefix}_decrypted_{i}.m4s"
        command = [os.path.join(BENTO4_BIN_DIR, "mp4decrypt"), "--key", key, input_file, output_file]
        process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            decrypted_files.append(output_file)
        else:
            return None, stderr.decode()
    return decrypted_files, None

async def combine_audio_video(audio_files, video_files, output_file, status_message):
    # Create input file lists for FFmpeg
    with open("audio_list.txt", "w") as audio_list:
        for audio_file in audio_files:
            audio_list.write(f"file '{audio_file}'\n")

    with open("video_list.txt", "w") as video_list:
        for video_file in video_files:
            video_list.write(f"file '{video_file}'\n")

    # Combine audio and video using FFmpeg
    command = [
        os.path.join(FFMPEG_BIN_DIR, "ffmpeg"),
        "-f", "concat", "-safe", "0", "-i", "video_list.txt",
        "-f", "concat", "-safe", "0", "-i", "audio_list.txt",
        "-c", "copy", output_file
    ]
    process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        return output_file, None
    else:
        return None, stderr.decode()

@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Welcome to the Decrypt MP4 Bot! Use /help to see available commands.")

@app.on_message(filters.command("help"))
def help_command(client, message):
    help_text = (
        "Here are the available commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n"
        "/download [URL] --key [KEY1:KEY2] --key [KEY3:KEY4] ... -M format=[FORMAT] -sv id=[VIDEO_ID] -sa best --save-name [NAME]\n"
        "\nExample usage:\n"
        "/download https://example.com/stream.mpd --key key1:key2 --key key3:key4 -M format=mp4 -sv id='2' -sa best --save-name 'My Video'"
    )
    message.reply_text(help_text)

@app.on_message(filters.command("download"))
async def download_and_decrypt_video(client, message):
    command_text = message.text

    # Extract URL
    url_match = re.search(r"(https?://[^\s]+)", command_text)
    if not url_match:
        await message.reply_text("Invalid URL format.")
        return
    url = url_match.group(0)

    # Extract keys
    keys = re.findall(r"--key ([a-f0-9]{32}:[a-f0-9]{32})", command_text)
    if not keys:
        await message.reply_text("No valid keys provided.")
        return

    # Extract save name
    save_name_match = re.search(r"--save-name '([^']+)'", command_text)
    save_name = save_name_match.group(1) if save_name_match else "decrypted_video"

    # Extract format (currently unused, can be extended)
    format_match = re.search(r"-M format=([a-z0-9]+)", command_text)
    format = format_match.group(1) if format_match else "mp4"

    # Extract video ID for specific quality selection
    video_id_match = re.search(r"-sv id='([^']+)'", command_text)
    video_id = video_id_match.group(1) if video_id_match else None

    dest_folder = os.path.join(os.getcwd(), "segments")
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    # Inform the user about the start of the download
    await message.reply_text("
