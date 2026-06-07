import json
import os
import time
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_youtube_client():
    creds_json = os.environ.get("YOUTUBE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        print("YOUTUBE_SERVICE_ACCOUNT_JSON not found.")
        return None
    try:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"Failed to initialize YouTube client: {e}")
        return None

def upload_video(youtube, file_path, title, description, hashtags, scheduled_date, privacy="private"):
    if not os.path.exists(file_path):
        return None

    body = {
        'snippet': {
            'title': title[:100],
            'description': f"{description}\n\n" + " ".join([f"#{h}" for h in hashtags]),
            'tags': hashtags,
            'categoryId': '20'
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False
        }
    }

    if scheduled_date:
        # Scheduled time: Randomize time between 09:00 and 21:00 UTC to look natural
        hour = random.randint(9, 21)
        publish_at = f"{scheduled_date}T{hour:02d}:00:00Z"
        body['status']['publishAt'] = publish_at
        body['status']['privacyStatus'] = 'private'
        print(f"Uploading {file_path} (Scheduled for {publish_at})...")
    else:
        print(f"Uploading {file_path} (Privacy: {privacy})...")

    if not youtube:
        print("MOCK MODE: Skipping actual upload.")
        return "MOCK_ID"

    try:
        media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        print(f"Upload Complete! Video ID: {response.get('id')}")
        return response.get('id')
    except HttpError as e:
        print(f"An HTTP error occurred: {e.resp.status} {e.content}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def process_uploads():
    if not os.path.exists("planning.json"):
        return

    with open("planning.json", "r", encoding="utf-8") as f:
        plan = json.load(f)

    youtube = get_youtube_client()

    for entry in plan:
        if entry["status"] == "produced":
            yt_id = upload_video(
                youtube,
                entry["video_path"],
                entry["title"],
                entry["description"],
                entry["hashtags"],
                entry.get("scheduled_at"),
                entry.get("privacy", "private")
            )
            if yt_id:
                entry["status"] = "uploaded"
                entry["youtube_id"] = yt_id
                if os.path.exists(entry["video_path"]):
                    os.remove(entry["video_path"])

    with open("planning.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    process_uploads()
