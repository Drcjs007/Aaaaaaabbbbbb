import os
import subprocess
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
import logging

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

# Function to download and decrypt MPD links
def download_and_decrypt(mpd_url, output_dir, keys):
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
        '--save-name', 'MENSTRUAL CYCLE-BASIC EXPLANATION'
    ]

    for kid, key in keys.items():
        download_cmd.extend(['--key', f'{kid}:{key}'])

    logger.info(f"Running download command: {' '.join(download_cmd)}")

    # Execute the download command
    subprocess.run(download_cmd, check=True)

    # Return the path to the downloaded file
    return os.path.join(output_dir, 'MENSTRUAL CYCLE-BASIC EXPLANATION.mp4')

# Bot command handlers
def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    update.message.reply_text('Hello! Send me an MPD URL to download and decrypt with keys in the format: mpd_url, key1, key2, key3, key4')

def help_command(update: Update, context: CallbackContext):
    logger.info("Received /help command")
    help_text = (
        "Welcome to the MPD Downloader and Decrypter Bot!\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Send an MPD URL followed by four keys to download and decrypt the video.\n"
        "Example:\n"
        "mpd_url key1 key2 key3 key4"
    )
    update.message.reply_text(help_text)

def handle_message(update: Update, context: CallbackContext):
    logger.info(f"Received message: {update.message.text}")
    try:
        # Parse the user input
        user_input = update.message.text.split()
        if len(user_input) != 5:
            update.message.reply_text("Please provide the MPD URL followed by four keys.")
            return

        mpd_url, key1, key2, key3, key4 = user_input
        keys = {
            'd45285545e4d525fb95c06b24a6f0bd3': key1,
            '09c9f7c69d0b5077915804658fb26384': key2,
            '48c36ec752b05716a8d7939aabbc9487': key3,
            'feeb78d1c10959b4ac50e2db4accdc9c': key4,
        }

        output_dir = 'output_directory'

        result_file = download_and_decrypt(mpd_url, output_dir, keys)
        update.message.reply_text("Download and decryption completed. Uploading the file...")
        with open(result_file, 'rb') as video:
            update.message.reply_video(video)
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
