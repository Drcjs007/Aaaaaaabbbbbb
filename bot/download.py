import os
import re
import aiohttp
import aiofiles
import time
import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from pyrogram.errors import FloodWait
from .decrypt import decrypt_segments
from .combine import combine_audio_video

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
    await message.reply_text("Starting download...")

    # Proceed with the download and decryption process here
    segment_files, selected_rep_id = await download_mpd(url, dest_folder, message, video_id)
    if not segment_files:
        await message.reply_text("Failed to download segments.")
        return

    decrypted_files, error = await decrypt_segments(segment_files, keys, os.path.join(dest_folder, save_name), message)
    if error:
        await message.reply_text(f"Decryption error: {error}")
        return

    audio_files = [file for file in decrypted_files if "audio" in file]
    video_files = [file for file in decrypted_files if "video" in file]

    output_file = f"{save_name}.{format}"
    result, error = await combine_audio_video(audio_files, video_files, output_file, message)
    if error:
        await message.reply_text(f"Combining error: {error}")
        return

    await message.reply_document(output_file)
