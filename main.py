import os
import subprocess
import aiohttp
import aiofiles
from pyrogram import Client, filters
from dotenv import load_dotenv
import asyncio
import time

# Load environment variables
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

BENTO4_BIN_DIR = "/usr/local/bin"  # Path to Bento4 binaries
os.environ["PATH"] += os.pathsep + BENTO4_BIN_DIR

async def download_file(url, dest, message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded_size = 0
            last_update_time = time.time()
            async with aiofiles.open(dest, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        await f.write(chunk)
                        current_time = time.time()
                        if total_size and current_time - last_update_time >= 10:
                            progress = (downloaded_size / total_size) * 100
                            await message.edit_text(f"Downloading... {progress:.2f}%")
                            last_update_time = current_time
    return dest

def decrypt_mp4(input_file, output_file, key):
    command = [os.path.join(BENTO4_BIN_DIR, "mp4decrypt"), "--key", f"1:{key}", input_file, output_file]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.decode()

@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Welcome to the Decrypt MP4 Bot! Use /help to see available commands.")

@app.on_message(filters.command("help"))
def help_command(client, message):
    help_text = (
        "Here are the available commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n"
        "/download [URL] [KEY] - Download and decrypt a video using the provided URL and key\n"
        "\nExample usage:\n"
        "/download http://example.com/video.mp4 your_decryption_key"
    )
    message.reply_text(help_text)

@app.on_message(filters.command("download"))
async def download_and_decrypt_video(client, message):
    args = message.text.split(" ")
    if len(args) < 3:
        await message.reply_text("Usage: /download [URL] [KEY]")
        return

    url = args[1]
    key = args[2]
    input_file = "downloaded.mp4"
    output_file = "decrypted.mp4"

    # Inform the user about the start of the download
    status_message = await message.reply_text("Starting download...")

    # Download the file
    try:
        await download_file(url, input_file, status_message)
        await status_message.edit_text("Download completed.")
    except Exception as e:
        await status_message.edit_text(f"Failed to download the file: {e}")
        return

    # Decrypt the file
    await status_message.edit_text("Decrypting the file...")
    stdout, stderr = decrypt_mp4(input_file, output_file, key)
    if stderr:
        await status_message.edit_text(f"Decryption failed: {stderr}")
    else:
        await status_message.edit_text("Decryption successful! Uploading the file...")
        await client.send_document(chat_id=message.chat.id, document=output_file)
        await status_message.edit_text("File uploaded successfully!")

if __name__ == "__main__":
    app.run()
