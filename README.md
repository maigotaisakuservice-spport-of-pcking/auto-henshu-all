# Minecraft Shorts AI Automation System

このシステムは、GitHub Actions (標準Runner) 上で動作し、マインクラフトの操作、録画、編集、BGM生成、そしてYouTube（Shorts）への予約投稿をすべて自動で行うフルオートメーションシステムです。

## システム概要
1.  **企画生成:** ローカルLLM (Llama-3) を使用して、1年分（52週間分）の投稿企画（タイトル、概要、マイクラへの指示）を一括生成します。
    - **初回特別動画:** 企画生成の最初に、必ず「THE IMPOSSIBLE DROP (不可能への挑戦)」という特別動画が生成されるようになっています。この動画は非公開設定でアップロードされます。
2.  **デイリー処理:** 毎日5本ずつ動画を生成・予約投稿します。
    - APIクォータ制限（1日5本程度）を考慮し、11日間かけて1年分の予約を完了させます。
3.  **マイクラ操作:** Forge 1.12.2 と Baritone Mod を使用し、AIがヘッドレス環境でマイクラを操作します。
4.  **動画編集:** 録画データを自動で 9:16 (Shorts) 形式にクロップし、独自生成したBGMと合成します。
5.  **コンプラチェック:** 不適切なワードや行動を自動でフィルタリングします。

## セットアップ手順

### 1. YouTube サービスアカウントの設定
1.  [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成します。
2.  YouTube Data API v3 を有効にします。
3.  「認証情報」から「サービスアカウント」を作成し、キー（JSON形式）をダウンロードします。
4.  **重要:** 作成したサービスアカウントのメールアドレスを、YouTubeのブランドアカウントの管理者（または編集者）として追加してください。

### 2. GitHub Secrets の設定
リポジトリの `Settings > Secrets and variables > Actions` に以下を登録します。
- `YOUTUBE_SERVICE_ACCOUNT_JSON`: ダウンロードしたサービスアカウントのJSONファイルの中身をそのまま貼り付けてください。

### 3. LLMモデルの準備
- `models/` ディレクトリに、Llama-3-8B などの GGUF 形式のモデルを配置してください。
- ファイル名は `scripts/generate_plan.py` 内の設定に合わせてください（デフォルト: `llama-3-8b-instruct.Q4_K_M.gguf`）。

## 使い方

1.  **企画の作成:**
    - GitHub Actions の `Generate 52-Week Plan` ワークフローを手動で実行（workflow_dispatch）します。
    - `planning.json` がリポジトリに生成されます。

2.  **自動運用:**
    - `Daily Video Production` ワークフローが毎日自動的に起動します。
    - 毎日5本ずつ動画が作成され、YouTubeに指定したスケジュールで予約投稿されます。
    - 進捗は `planning.json` 内の `status` フィールドで確認できます。

## ディレクトリ構造
- `scripts/`: メインロジック（企画生成、動画制作、アップロード）
- `.github/workflows/`: 自動実行設定
- `minecraft/`: マイクラの実行環境（実行時に構築）
- `planning.json`: 1年分の進捗管理ファイル

## コンプライアンスについて
`scripts/produce_video.py` 内の `ng_words` リストを編集することで、フィルタリングする単語を追加できます。
デフォルトでは「死ね」「殺す」「殺戮」などが設定されています。

## 注意事項
- 標準Runnerの制限時間（6時間）に収まるよう、1日5本に制限しています。
- YouTube APIの制限により、1日に投稿できる本数はアカウントの状態に依存します。
