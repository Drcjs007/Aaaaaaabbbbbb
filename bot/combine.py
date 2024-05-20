import os
import asyncio

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
        os.path.join("ffmpeg", "ffmpeg"),
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
