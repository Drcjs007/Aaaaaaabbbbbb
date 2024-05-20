import os
import subprocess
import time
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
import logging
from telegram.error import TimedOut, NetworkError, RetryAfter

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
PORT = int(os.getenv("PORT", 8443))
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Function to download and decrypt MPD links
def download_and_decrypt(mpd_url, output_dir, file_name, keys):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Path to N_m3u8DL-RE executable
    nm3u8dl_re_path = './N_m3u8DL-RE_Beta_linux-arm64/N_m3u8DL-RE'

    # Construct the download command with keys
    download_cmd = [
        nm3u8dl_re_path,
        mpd_url,
        '-M', 'format=mp4',
        '-sv', "id='2'",
        '-sa', 'best',
        '--save-name', file_name
    ]

    for kid, key in keys.items():
        download_cmd.extend(['--key', f'{kid}:{key}'])

    logger.info(f"Running download command: {' '.join(download_cmd)}")

    # Execute the download command
    process = subprocess.Popen(download_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return process

# Bot command handlers
def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    update.message.reply_text('Hello! Send me an MPD URL to download and decrypt with keys in the format: mpd_url file_name key1 key2 key3 key4')

def help_command(update: Update, context: CallbackContext):
    logger.info("Received /help command")
    help_text = (
        "Welcome to the MPD Downloader and Decrypter Bot!\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Send an MPD URL followed by a file name and four keys to download and decrypt the video.\n"
        "Example:\n"
        "mpd_url file_name key1 key2 key3 key4"
    )
    update.message.reply_text(help_text)

def handle_message(update: Update, context: CallbackContext):
    logger.info(f"Received message: {update.message.text}")
    try:
        # Parse the user input
        user_input = update.message.text.split()
        if len(user_input) != 6:
            update.message.reply_text("Please provide the MPD URL, file name, and four keys.")
            return

        mpd_url, file_name, key1, key2, key3, key4 = user_input
        keys = {
            '82ccbe35c90f55dab55e2562bf3f257f': key1,
            '0573c70291ca5b27ad1ffedfe463102d': key2,
            '283e00573562584ebaed3742ade268ce': key3,
            'f4edff4e747c586486ef5f5c8a7423e2': key4,
        }

        output_dir = 'output_directory'
        update.message.reply_text("Starting download and decryption process...")

        process = download_and_decrypt(mpd_url, output_dir, file_name, keys)

        while process.poll() is None:
            update.message.reply_text("Download in progress...")
            time.sleep(5)

        stdout, stderr = process.communicate()
        if process.returncode == 0:
            update.message.reply_text("Download and decryption completed. Uploading the file...")
            with open(os.path.join(output_dir, file_name), 'rb') as video:
                update.message.reply_video(video)
        else:
            update.message.reply_text(f"An error occurred: {stderr.decode('utf-8')}")

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        update.message.reply_text(f"An error occurred: {e}")

# Main function to set up the bot
def main():
    logger.info("Starting bot")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Setting webhook")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
