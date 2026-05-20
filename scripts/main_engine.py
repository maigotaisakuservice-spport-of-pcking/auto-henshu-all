import os
import gc
import json
import subprocess
import requests
import re
import datetime
import torch
import sys
import io
from huggingface_hub import hf_hub_download
from faster_whisper import WhisperModel
from llama_cpp import Llama
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy.io.wavfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account, credentials

# Windows環境での日本語出力エラー対策
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class StudioEngine:
    def __init__(self):
        self.gdrive_url = os.environ.get("GDRIVE_URL")
        raw_names = os.environ.get("REAL_NAME", "")
        self.real_names = [n.strip() for n in raw_names.split(",") if n.strip()]
        self.encode_speed = os.environ.get("ENCODE_SPEED", "veryfast")
        self.video_quality = os.environ.get("VIDEO_QUALITY", "23")
        self.target_fps = os.environ.get("TARGET_FPS", "30")
        self.target_duration = int(os.environ.get("TARGET_DURATION", "15")) * 60
        self.tone = os.environ.get("TONE", "明るい")
        self.webhook = os.environ.get("DISCORD_WEBHOOK")

        self.youtube_service_json = os.environ.get("YOUTUBE_SERVICE_ACCOUNT_JSON")
        self.youtube_client_id = os.environ.get("YOUTUBE_CLIENT_ID")
        self.youtube_client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.youtube_refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

        self.model_dir = "./models"
        self.bgm_dir = "./bgm"
        self.bgm_meta_file = os.path.join(self.bgm_dir, "metadata.json")
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.bgm_dir, exist_ok=True)

    def mask_text(self, text):
        if not isinstance(text, str): text = str(text)
        safe_msg = text
        for name in self.real_names:
            if len(name) > 1:
                masked = name[0] + "*" * (len(name)-1)
                safe_msg = safe_msg.replace(name, masked)
            else:
                safe_msg = safe_msg.replace(name, "*")
        return safe_msg

    def log(self, message, force_mask=True):
        if len(message) > 1500: message = message[:1500] + "...(truncated)"
        safe_msg = self.mask_text(message) if force_mask else message
        print(f"[Studio] {safe_msg}")
        if self.webhook:
            try: requests.post(self.webhook, json={"content": f"**[Studio]** {safe_msg}"})
            except: pass

    def download_video(self):
        self.log("Google Driveから動画をダウンロード中...")
        try:
            # 1. PowerShell でのダウンロード実行 (URLを確実に引用)
            # & export=download などが含まれるためシングルクォートで囲む
            cmd = ["powershell", "-Command", f"Invoke-WebRequest -Uri '{self.gdrive_url}' -OutFile input.mp4"]
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            if not os.path.exists("input.mp4") or os.path.getsize("input.mp4") < 1000:
                raise Exception("動画ファイルのダウンロードに失敗したか、ファイルが壊れています。URLが正しいか、権限があるか確認してください。")

            # 2. 動画時間を取得
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", "input.mp4"
            ], capture_output=True, text=True)

            duration_str = result.stdout.strip()
            if not duration_str:
                raise Exception(f"ffprobeが動画時間を取得できませんでした。stderr: {result.stderr}")

            self.duration = float(duration_str)
            self.log(f"動画時間を取得: {self.duration}秒")

        except subprocess.CalledProcessError as e:
            raise Exception(f"ダウンロード中にエラーが発生しました: {e.stderr}")

    def download_models(self):
        self.log("AIモデル(Llama-3)を取得中...")
        self.llama_path = hf_hub_download(
            repo_id="QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
            filename="Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
            local_dir=self.model_dir
        )

    def analyze_and_censor(self):
        whisper_size = "base" if self.duration > 1800 else "small"
        self.log(f"フェーズ1: 音声解析...")
        model = WhisperModel(whisper_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe("input.mp4")
        raw_data = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
        del model
        gc.collect()

        self.log("フェーズ2: 文脈解析 & 検閲...")
        llm = Llama(model_path=self.llama_path, n_ctx=8192)
        sample = " ".join([r['text'] for r in raw_data[:50]])
        mood_res = llm(f"以下の会話からこの動画のムードを単語3つで答えよ: {sample}", max_tokens=100)
        self.video_mood = mood_res['choices'][0]['text'].strip()
        self.log(f"判定されたムード: {self.video_mood}")

        chunk_size = 600
        full_decision = []
        for i in range(0, int(self.duration), chunk_size):
            chunk_data = [r for r in raw_data if i <= r['start'] < i + chunk_size]
            if not chunk_data: continue
            prompt = f"出力形式: [{{\"start\": 秒, \"end\": 秒}}, ...] のJSONのみ返せ。指示: 本名 {self.real_names} を含む箇所を除外し、採用すべき範囲のリストを作成せよ。データ: {json.dumps(chunk_data, ensure_ascii=False)}"
            res = llm(prompt, max_tokens=2048)
            try:
                json_str = re.search(r'\[\s*\{.*\}\s*\]', res['choices'][0]['text'], re.DOTALL).group()
                full_decision.extend(json.loads(json_str))
            except: full_decision.extend([{"start": r["start"], "end": r["end"]} for r in chunk_data])

        total_adopted = sum(d['end'] - d['start'] for d in full_decision)
        if total_adopted > self.target_duration:
            capped = []; cur = 0
            for d in full_decision:
                dur = d['end'] - d['start']
                if cur + dur > self.target_duration:
                    capped.append({"start": d['start'], "end": d['start'] + (self.target_duration - cur)}); break
                capped.append(d); cur += dur
            full_decision = capped

        del llm
        gc.collect()
        return full_decision

    def generate_or_select_bgm(self):
        meta = {}
        if os.path.exists(self.bgm_meta_file):
            with open(self.bgm_meta_file, "r") as f: meta = json.load(f)
        best = next((os.path.join(self.bgm_dir, f) for f, d in meta.items() if any(w in d.get("mood", "") for w in self.video_mood.split(","))), None)
        if best and len(meta) >= 50:
            self.log("ムードに合う既存のBGMを選択しました。")
            return best
        self.log(f"フェーズ3: ムード '{self.video_mood}' に合わせてBGMを生成中...")
        processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        inputs = processor(text=[f"BGM, {self.video_mood} mood, high quality, lo-fi"], padding=True, return_tensors="pt")
        audio_values = model.generate(**inputs, max_new_tokens=512)
        filename = f"bgm_{len(meta)+1}.wav"
        path = os.path.join(self.bgm_dir, filename)
        scipy.io.wavfile.write(path, rate=model.config.audio_encoder.sampling_rate, data=audio_values[0, 0].numpy())
        meta[filename] = {"mood": self.video_mood, "tone": self.tone, "created_at": str(datetime.date.today())}
        with open(self.bgm_meta_file, "w") as f: json.dump(meta, f)
        del model
        gc.collect()
        return path

    def render_video(self, decision, bgm_path):
        speed = "ultrafast" if self.duration > 1800 else self.encode_speed
        self.log(f"フェーズ4: レンダリング開始...")
        with open("join.txt", "w") as f:
            for d in decision: f.write(f"file 'input.mp4'\ninpoint {d['start']}\noutpoint {d['end']}\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "join.txt", "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]",
            "-c:v", "libx265", "-preset", speed, "-crf", self.video_quality, "-r", self.target_fps,
            "-c:a", "aac", "-b:a", "128k", "output.mp4"
        ], check=True)

    def get_youtube_client(self):
        if self.youtube_service_json:
            self.log("YouTube 認証: サービスアカウントを使用します。")
            try:
                info = json.loads(self.youtube_service_json)
                creds = service_account.Credentials.from_service_account_info(
                    info, scopes=["https://www.googleapis.com/auth/youtube.upload"]
                )
                return build("youtube", "v3", credentials=creds)
            except Exception as e:
                self.log(f"サービスアカウント認証に失敗: {str(e)}")

        if all([self.youtube_client_id, self.youtube_client_secret, self.youtube_refresh_token]):
            self.log("YouTube 認証: リフレッシュトークンを使用します。")
            try:
                creds_obj = credentials.Credentials(
                    None,
                    refresh_token=self.youtube_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.youtube_client_id,
                    client_secret=self.youtube_client_secret
                )
                return build("youtube", "v3", credentials=creds_obj)
            except Exception as e:
                self.log(f"リフレッシュトークン認証に失敗: {str(e)}")
        return None

    def upload_to_youtube(self):
        youtube = self.get_youtube_client()
        if not youtube:
            self.log("YouTube 認証情報が不足しています。アップロードをスキップ。")
            return

        self.log("フェーズ5: YouTubeへアップロード中...")
        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": f"Production {datetime.date.today()}", "description": f"Mood: {self.video_mood}", "categoryId": "22"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("output.mp4", chunksize=1024*1024, resumable=True)
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status: self.log(f"Upload: {int(status.progress() * 100)}%")
            self.log(f"Done! ID: {response.get('id')}")
        except Exception as e:
            self.log(f"YouTubeエラー: {str(e)}")

if __name__ == "__main__":
    engine = StudioEngine()
    try:
        engine.download_video()
        engine.download_models()
        decision = engine.analyze_and_censor()
        bgm_path = engine.generate_or_select_bgm()
        engine.render_video(decision, bgm_path)
        engine.upload_to_youtube()
        engine.log("完了。")
    except Exception as e: engine.log(f"エラー: {str(e)}")
