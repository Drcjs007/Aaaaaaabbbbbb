from pyrogram import Client, filters
from bot import app

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
