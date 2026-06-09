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

    # 0. Special Initial Video: THE IMPOSSIBLE DROP
    plan.append({
        "week": 0,
        "title": "THE IMPOSSIBLE DROP (不可能への挑戦)",
        "description": "高度10,000ブロックからの水バケツ着地への挑戦！ #Minecraft #Shorts #ImpossibleDrop",
        "hashtags": ["Minecraft", "Shorts", "ImpossibleDrop", "MLG"],
        "scheduled_at": None, # No public schedule
        "privacy": "private",
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
                "You are a viral Minecraft YouTuber expert at YouTube Shorts. "
                "Generate a high-engagement, clickbaity title and description for a 60-second Short. "
                "The content must be mind-blowing or intense. "
                "Use emojis and relate hashtags to the content. "
                "Provide Baritone AI instructions for the action."
            )
            prompt = (
                f"{system_prompt}\n\n"
                f"Week: {i}\n"
                f"Theme: {theme}\n"
                "Task: Create a unique, non-repetitive, and extremely engaging Minecraft Shorts plan. "
                "The title should be a 'Hook' that stops people from scrolling (like 'Impossible' or 'Secret'). "
                "The description should be punchy with emojis and related hashtags. "
                "The instructions should be clear Baritone commands.\n"
                "Constraints: Use Japanese for title/description. Ensure this week's content is distinct and highest quality.\n"
                "Format: JSON ONLY with keys 'title', 'description', 'instructions', 'hashtags' (list)."
            )
            print(f"Inference starting for Week {i}...")
            output = llm(f"User: {prompt}\nAssistant:", max_tokens=512, stop=["User:"])
            print(f"Inference finished for Week {i}.")
            data = robust_json_parse(output['choices'][0]['text'])
            if data:
                title = data.get("title", title)
                desc = data.get("description", desc)
                instr = data.get("instructions", instr)

        week_hashtags = ["Minecraft", "Shorts", theme]
        if llm and data and "hashtags" in data:
            week_hashtags = data["hashtags"]

        plan.append({
            "week": i,
            "title": title,
            "description": desc,
            "hashtags": week_hashtags,
            "scheduled_at": (start_date + datetime.timedelta(weeks=i)).isoformat(),
            "ai_instructions": instr,
            "status": "pending",
            "video_path": None,
            "youtube_id": None
        })

    with open("planning.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    generate_plan()
