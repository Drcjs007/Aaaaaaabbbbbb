import os
import subprocess
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
PORT = int(os.getenv("PORT", 8443))

# Function to download and decrypt MPD links
def download_and_decrypt(mpd_url, output_dir, key_file):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Path to N_m3u8DL-RE and mp4decrypt executables
    nm3u8dl_re_path = './N_m3u8DL-RE_Beta_linux-arm64/N_m3u8DL-RE'
    mp4decrypt_path = './Bento4/Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt'

    # Download segments using nm3u8dl
    download_cmd = [
        nm3u8dl_re_path,
        mpd_url,
        '--workDir', output_dir,
        '--saveName', 'output'
    ]
    subprocess.run(download_cmd, check=True)

    # Decrypt segments using mp4decrypt
    encrypted_video = os.path.join(output_dir, 'output.mp4')
    decrypted_video = os.path.join(output_dir, 'decrypted_output.mp4')
    decrypt_cmd = [
        mp4decrypt_path,
        '--key', f'1:{key_file}',  # Replace '1' with the correct KID if needed
        encrypted_video,
        decrypted_video
    ]
    subprocess.run(decrypt_cmd, check=True)

    # Merge audio and video using ffmpeg
    merged_output = os.path.join(output_dir, 'merged_output.mp4')
    merge_cmd = [
        'ffmpeg',
        '-i', decrypted_video,
        '-i', os.path.join(output_dir, 'output_audio.mp4'),  # Adjust if audio is downloaded separately
        '-c', 'copy',
        merged_output
    ]
    subprocess.run(merge_cmd, check=True)

    return merged_output

# Bot command handlers
def start(update, context):
    update.message.reply_text('Hello! Send me an MPD URL to download and decrypt.')

def handle_message(update, context):
    mpd_url = update.message.text
    output_dir = 'output_directory'
    key_file = 'decryption_key'  # Provide the path to your key file

    try:
        result_file = download_and_decrypt(mpd_url, output_dir, key_file)
        update.message.reply_text(f"Download and decryption completed. File saved at {result_file}")
    except Exception as e:
        update.message.reply_text(f"An error occurred: {e}")

# Main function to set up the bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook(f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/{TOKEN}")

    updater.idle()

if __name__ == "__main__":
    main()

