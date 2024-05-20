import os
import asyncio

async def decrypt_segments(input_files, keys, output_prefix, status_message):
    decrypted_files = []
    for i, input_file in enumerate(input_files):
        key = keys[i % len(keys)]
        output_file = f"{output_prefix}_decrypted_{i}.m4s"
        command = [os.path.join("bin", "mp4decrypt"), "--key", key, input_file, output_file]
        process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            decrypted_files.append(output_file)
        else:
            return None, stderr.decode()
    return decrypted_files, None
