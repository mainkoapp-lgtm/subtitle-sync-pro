import subprocess
import os

ffprobe_p = r"d:\Project Temporary\subtitle\subtitle_development\tools\subtitle_extractor\ffmpeg\bin\ffprobe.exe"
target_dir = r"D:\Project Temporary"

print(f"Target: {target_dir}")
try:
    files = os.listdir(target_dir)
    print(f"Files found: {len(files)}")
    for f in files:
        if f.endswith(".mkv") and "Descent" in f:
            print(f"Analyzing {f}...")
            full_path = os.path.join(target_dir, f)
            cmd = [ffprobe_p, "-v", "error", "-select_streams", "s", "-show_entries", "stream=index,codec_name:stream_tags=language", "-of", "json", full_path]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print("--- RESULT START ---")
            print(res.stdout)
            print("--- RESULT END ---")
            if res.stderr:
                print(f"Error: {res.stderr}")
except Exception as e:
    print(f"Error listing dir: {e}")
