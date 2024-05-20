import os
import subprocess
import aiohttp
import aiofiles
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from dotenv import load_dotenv
import asyncio
import time

# Load environment variables
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

BENTO4_BIN_DIR = "/app/bin"  # Path to Bento4 binaries
os.environ["PATH"] += os.pathsep + BENTO4_BIN_DIR

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

async def decrypt_mp4(input_file, output_file, key, status_message):
    command = [os.path.join(BENTO4_BIN_DIR, "mp4decrypt"), "--key", f"1:{key}", input_file, output_file]
    start_time = time.time()
    process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        elapsed_time = time.time() - start_time
        try:
            await status_message.edit_text(f"Decrypting... {elapsed_time:.2f} seconds elapsed")
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                raise
        await asyncio.sleep(5)
        if process.returncode is not None:
            break
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        return stdout.decode(), None
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
    stdout, stderr = await decrypt_mp4(input_file, output_file, key, status_message)
    if stderr:
        await status_message.edit_text(f"Decryption failed: {stderr}")
    else:
        await status_message.edit_text("Decryption successful! Uploading the file...")
        try:
            start_time = time.time()
            await client.send_document(chat_id=message.chat.id, document=output_file)
            elapsed_time = time.time() - start_time
            speed = os.path.getsize(output_file) / elapsed_time / 1024
            await status_message.edit_text(
                f"File uploaded successfully at {speed:.2f} KB/s!"
            )
        except FloodWait as e:
            await asyncio.sleep(e.seconds)
            await client.send_document(chat_id=message.chat.id, document=output_file)
            await status_message.edit_text("File uploaded successfully!")

if __name__ == "__main__":
    app.run()
