import json
import os
import subprocess
import random
import math
import re
import time
from mc_bridge import MinecraftBridge

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

def get_llm():
    model_path = os.environ.get("MODEL_PATH", "models/llama-3-8b-instruct.Q4_K_M.gguf")
    if not os.path.exists(model_path) or Llama is None:
        return None
    # Optimized for GitHub Actions CPU (2 cores)
    return Llama(model_path=model_path, n_ctx=512, n_threads=2, verbose=True)

def generate_bgm(output_path, duration_sec):
    """
    Generates a simple rhythmic BGM using ffmpeg's sine wave and noise filters.
    A lightweight alternative to ML-based generation that fits in 4GB RAM.
    """
    print(f"Generating algorithmic BGM ({duration_sec}s)...")

    # Create a simple beat using pulse and sine waves
    # This creates a 'gaming' style lo-fi beat
    filter_expr = (
        "sine=f=440:d={d}:b=0.5,apad=pad_len=20000[s];"
        "noise=d={d}:c=white:v=0.01[n];"
        "[s][n]amix=inputs=2[a]"
    ).format(d=duration_sec)

    # More complex: alternating frequencies for a melody
    melody = ""
    for i in range(int(duration_sec)):
        freq = random.choice([261.63, 293.66, 329.63, 349.23, 392.00]) # C4 to G4
        melody += f"sine=f={freq}:d=1,"
    melody = melody.rstrip(",") + f"[m];[m]volume=0.3[mv];"

    # Basic beat
    beat = "sine=f=60:d=0.1,adelay=500|500,aloop=loop=-1:size=22050[b];[b]volume=0.8[bv];"

    final_filter = f"{melody}{beat}[mv][bv]amix=inputs=2[out]"

    cmd = [
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex", final_filter, "-map", "[out]",
        "-t", str(duration_sec), "-c:a", "libmp3lame", output_path, "-y"
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except:
        # Fallback to simple noise if filter is too complex
        subprocess.run(["ffmpeg", "-f", "lavfi", "-i", f"noise=d={duration_sec}", "-t", str(duration_sec), output_path, "-y"], capture_output=True)

def edit_video(input_video, input_audio, output_video):
    print(f"Editing Regular Video (16:9): {output_video}")
    # Maintain original aspect ratio (16:9 720p)
    # Just merge audio and normalize volume
    cmd = [
        "ffmpeg", "-i", input_video, "-i", input_audio,
        "-filter_complex", "[1:a]volume=0.6[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-shortest", output_video, "-y"
    ]
    subprocess.run(cmd, capture_output=True)

def check_compliance(text_list, llm=None):
    # Layer 1: Rigid Keyword Check
    ng_words = [
        "死ね", "殺す", "殺戮", "虐殺", "死んじゃえ",
        "村人", "villager", "kill", "murder", "attack", "slaughter"
    ]
    for text in text_list:
        if any(ng.lower() in text.lower() for ng in ng_words):
            print(f"Rigid Compliance Failure: Keyword detected in '{text}'")
            return False

    # Layer 2: AI-Powered Deep Compliance Check
    if llm:
        combined_text = "\n".join(text_list)
        prompt = (
            "Determine if the following text contains violence, inappropriate language, "
            "or actions that involve killing peaceful NPCs (like villagers) in Minecraft. "
            "Specifically, any mention of killing 'villagers' or 'killing' in general is strictly forbidden. "
            "Return ONLY 'SAFE' or 'UNSAFE'.\n\n"
            f"Text: {combined_text}"
        )
        try:
            output = llm(f"User: {prompt}\nAssistant:", max_tokens=10, stop=["User:"])
            result = output['choices'][0]['text'].strip().upper()
            if "UNSAFE" in result:
                print(f"AI Compliance Failure: AI flagged content as UNSAFE.")
                return False
            print("AI Compliance Check: PASSED")
        except Exception as e:
            print(f"AI Compliance Error (falling back to rigid check): {e}")

    return True

def produce_batch(limit=5):
    if not os.path.exists("planning.json"): return
    with open("planning.json", "r", encoding="utf-8") as f: plan = json.load(f)

    llm = get_llm()
    processed = 0
    for entry in plan:
        if entry["status"] != "pending" or processed >= limit: continue

        print(f"Processing Week {entry['week']}")
        if not check_compliance([entry['title'], entry['description'], entry['ai_instructions']], llm):
            entry['status'] = 'rejected'
            continue

        raw_video = f"raw_{entry['week']}.mp4"

        # 1. AI Minecraft Recording
        bridge = MinecraftBridge()
        bridge.start_display()
        bridge.start_minecraft()

        # Wait for Minecraft to boot and load (Crucial for headless)
        print("Waiting for Minecraft to initialize (90s)...")
        time.sleep(90)

        bridge.start_recording(raw_video)

        # 1-1. Preparation phase (Gamerules, WorldEdit, etc.)
        setup_cmds = entry.get("setup_commands", [])
        for cmd in setup_cmds:
            print(f"Executing Setup Command: {cmd}")
            bridge.send_baritone_command(cmd)
            time.sleep(2) # Short gap between setup commands

        # 1-2. Main Action phase
        action_cmds = entry.get("action_commands", [])
        for cmd in action_cmds:
            print(f"Executing Action Command: {cmd}")
            bridge.send_baritone_command(cmd)

        # Record for 60 seconds of action
        time.sleep(60)

        bridge.stop_all()

        bgm_file = f"bgm_{entry['week']}.mp3"
        generate_bgm(bgm_file, 60)

        final_video = f"final_{entry['week']}.mp4"
        edit_video(raw_video, bgm_file, final_video)

        entry["status"] = "produced"
        entry["video_path"] = os.path.abspath(final_video)
        processed += 1

        if os.path.exists(raw_video): os.remove(raw_video)
        if os.path.exists(bgm_file): os.remove(bgm_file)

    with open("planning.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    produce_batch()
