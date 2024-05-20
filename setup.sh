#!/bin/bash

# Update package lists
sudo apt update

# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
sudo apt install ffmpeg -y

# Install Bento4
sudo apt install bento4 -y

echo "Setup completed. You can now run the bot using 'python your_script.py'."
