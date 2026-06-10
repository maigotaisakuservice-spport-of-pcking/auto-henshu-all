import json
import os
import datetime
import sys
import re

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

def get_llm():
    model_path = os.environ.get("MODEL_PATH", "models/llama-3-8b-instruct.Q4_K_M.gguf")
    if not os.path.exists(model_path) or Llama is None:
        return None
    # Reduce n_ctx to save memory and use multiple threads for CPU speedup
    return Llama(model_path=model_path, n_ctx=1024, n_threads=4, verbose=True)

def robust_json_parse(text):
    try:
        # Attempt to find JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0).replace("'", "\""))
    except:
        pass
    return None

def generate_plan():
    llm = get_llm()
    plan = []

    # Mandatory core hashtags as requested by the user
    mandatory_hashtags = [
        "マインクラフト", "マイクラ", "まいくら", "minecraft",
        "実況", "実況者", "ゲーム", "ゲーム実況", "テキパキパソコン",
        "youtubevideo", "youtubevideos"
    ]

    # 0. Special Initial Video: THE IMPOSSIBLE DROP (SHORTS)
    plan.append({
        "week": 0,
        "title": "THE IMPOSSIBLE DROP (不可能への挑戦)",
        "description": "高度10,000ブロックからの水バケツ着地への挑戦！",
        "hashtags": list(set(mandatory_hashtags + ["ImpossibleDrop", "MLG", "Shorts"])),
        "tags": "Minecraft, MLG, Water Bucket, Impossible, Challenge, Shorts",
        "duration_sec": 55, # Keep it strictly under 60s for Shorts
        "is_shorts": True,
        "scheduled_at": None, # No public schedule
        "privacy": "private",
        "setup_commands": ["/tp @p 0 10000 0"],
        "action_commands": ["perform water bucket MLG at 0 60 0 surrounded by lava and obsidian"],
        "ai_instructions": "/tp @p 0 10000 0 | then perform water bucket MLG at 0 60 0 surrounded by lava and obsidian",
        "status": "pending",
        "video_path": None,
        "youtube_id": None
    })

    start_date = datetime.date.today() + datetime.timedelta(days=7)
    themes = ["Survival", "Building", "Redstone", "Discovery"]

    for i in range(1, 53):
        theme = themes[i % len(themes)]
        print(f"Planning Week {i}...")

        title, desc, instr = f"Minecraft {theme} Week {i}", f"Week {i} content", "explore"

        if llm:
            system_prompt = (
                "You are a viral Minecraft YouTuber expert. "
                "Generate a high-engagement, clickbaity title and description for a high-quality Minecraft video. "
                "The content must be mind-blowing or intense. "
                "Use emojis and relate hashtags to the content. "
                "Provide Baritone AI instructions for the action."
            )
            # Week 52 special handling (Mega Project)
            if i == 52:
                theme = "Mega Project (1 Million Subscribers Special City Build)"
                duration_prompt = "Exactly 3600 seconds (1 hour)."
            else:
                duration_prompt = "Between 600 and 900 seconds (10-15 minutes)."

            prompt = (
                f"{system_prompt}\n\n"
                f"Week: {i}\n"
                f"Theme: {theme}\n"
                "Task: Create a unique, non-repetitive, and extremely engaging Minecraft Video plan.\n"
                "Preparation: Include specific Minecraft commands for setup (gamerules, time, building structures with WorldEdit if needed).\n"
                "Action: Provide clear Baritone AI commands for the main gameplay recording.\n"
                "Metadata: Clickbaity Japanese Title, punchy description with emojis and related hashtags. "
                "Include a 'tags' field with comma-separated SEO tags for the YouTube tags section.\n"
                f"Duration: {duration_prompt}\n"
                "Format: JSON ONLY with keys 'title', 'description', 'setup_commands' (list), 'action_commands' (list), 'hashtags' (list), 'tags' (string), 'duration_sec' (int)."
            )
            print(f"Inference starting for Week {i}...")
            output = llm(f"User: {prompt}\nAssistant:", max_tokens=512, stop=["User:"])
            print(f"Inference finished for Week {i}.")
            data = robust_json_parse(output['choices'][0]['text'])
            if data:
                title = data.get("title", title)
                desc = data.get("description", desc)
                instr = data.get("instructions", instr)

        # Combine mandatory hashtags with LLM-generated ones, removing duplicates
        week_hashtags = list(set(mandatory_hashtags + [theme]))
        week_tags = "Minecraft, Gaming, Challenge"
        if llm and data:
            if "hashtags" in data:
                week_hashtags = list(set(mandatory_hashtags + data["hashtags"]))
            if "tags" in data:
                week_tags = data["tags"]

        setup_cmds = data.get("setup_commands", ["/gamerule doMobSpawning false", "/time set noon"]) if llm and data else ["/time set noon"]
        action_cmds = data.get("action_commands", [instr]) if llm and data else [instr]

        # Ensure correct defaults based on week
        if i == 52:
            default_duration = 3600
            title = data.get("title", "【100万人記念】AIが1時間で巨大都市を建設する神回") if llm and data else "【100万人記念】AIが1時間で巨大都市を建設する神回"
        else:
            default_duration = 600

        duration = data.get("duration_sec", default_duration) if llm and data else default_duration

        plan.append({
            "week": i,
            "title": title,
            "description": desc,
            "hashtags": week_hashtags,
            "tags": week_tags,
            "duration_sec": duration,
            "is_shorts": False,
            "scheduled_at": (start_date + datetime.timedelta(weeks=i)).isoformat(),
            "setup_commands": setup_cmds,
            "action_commands": action_cmds,
            "ai_instructions": " | ".join(setup_cmds + action_cmds), # Legacy support
            "status": "pending",
            "video_path": None,
            "youtube_id": None
        })

    with open("planning.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    generate_plan()
