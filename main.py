import os
import signal
import asyncio
from dotenv import load_dotenv
from bot import app as bot_app
from server import create_server

# Load environment variables
load_dotenv()

PORT = int(os.getenv("PORT", 5000))  # Default to port 5000 if PORT is not set

server = create_server()

async def main():
    await bot_app.start()
    server.run(host="0.0.0.0", port=PORT)

def shutdown(signal, frame):
    print("Received shutdown signal")
    asyncio.run(bot_app.stop())
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    asyncio.run(main())
