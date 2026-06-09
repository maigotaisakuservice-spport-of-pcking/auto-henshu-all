# Minecraft Shorts AI Automation System

このシステムは、GitHub Actions (標準Runner) 上で動作し、マインクラフトの操作、録画、編集、BGM生成、そしてYouTube（Shorts）への予約投稿をすべて自動で行うフルオートメーションシステムです。

## システム概要
1.  **企画生成:** ローカルLLM (Llama-3) を使用して、1年分（52週間分）の投稿企画（タイトル、概要、マイクラへの指示）を一括生成します。
    - **初回特別動画:** 企画生成の最初に、必ず「THE IMPOSSIBLE DROP (不可能への挑戦)」という特別動画が生成されるようになっています。この動画は非公開設定でアップロードされます。
2.  **デイリー処理:** 毎日5本ずつ動画を生成・予約投稿します。
    - APIクォータ制限（1日5本程度）を考慮し、11日間かけて1年分の予約を完了させます。
3.  **マイクラ操作:** Forge 1.12.2 と Baritone Mod を使用し、AIがヘッドレス環境でマイクラを操作します。
4.  **動画編集:** 録画データを自動で 9:16 (Shorts) 形式にクロップし、独自生成したBGMと合成します。
5.  **コンプラチェック:** 不適切なワードや行動を自動でフィルタリングします。キーワードベースのチェックに加え、ローカルLLMを用いた高度な内容判定（AIコンプラチェック）を導入しています。

## セットアップ手順

### 1. YouTube API の認証設定 (OAuth2方式)
ブランドアカウントを使用している場合、セキュリティと確実性の観点から **OAuth2（クライアントID、シークレット、リフレッシュトークン）** を使用します。
※注意: アプリパスワードは YouTube API では使用できません。

#### 1-1. Google Cloud Console での作業
1.  [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成し、**YouTube Data API v3** を有効にします。
2.  「OAuth 同意画面」を設定します。
    - User Type: 「外部」を選択。
    - アプリ名、ユーザーサポートメールなどを入力。
    - **重要:** 「テストユーザー」に自分のメールアドレスを追加してください。
3.  「認証情報」>「+ 認証情報を作成」>「OAuth クライアント ID」を選択します。
    - アプリケーションの種類: **「デスクトップ アプリ」**
    - 名前を入力して「作成」をクリック。
4.  表示された **クライアント ID** と **クライアント シークレット** を必ず手元に控えてください。

#### 1-2. リフレッシュトークンの取得
1.  [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) にアクセスします。
2.  右上の設定アイコン（歯車）をクリックし、以下を設定します。
    - **OAuth flow:** `Server-side`
    - **Access type:** `Offline`
    - **Use your own OAuth credentials:** チェックを入れ、上記で控えた **Client ID** と **Client Secret** を入力します。
3.  左側の「Step 1: Select & authorize APIs」の入力欄に `https://www.googleapis.com/auth/youtube.upload` を入力し、**「Authorize APIs」**をクリックします。
4.  Googleアカウントの選択画面が出るので、**動画を投稿したいチャンネル（ブランドアカウント）を選択**して承認します。
5.  「Step 2: Exchange authorization code for tokens」で **「Exchange authorization code for tokens」** をクリックします。
6.  表示された **Refresh Token** を控えます。

### 2. GitHub Secrets の設定
リポジトリの `Settings > Secrets and variables > Actions` に以下を登録します。
- `YOUTUBE_CLIENT_ID`: 取得したクライアントID
- `YOUTUBE_CLIENT_SECRET`: 取得したクライアントシークレット
- `YOUTUBE_REFRESH_TOKEN`: 取得したリフレッシュトークン

### 3. LLMモデルの準備
- LLMモデル（Llama-3-8B GGUF）は、GitHub Actions の実行時に**自動的にダウンロードされる**よう設定されています。手動で配置する必要はありません。

## 使い方

1.  **企画の作成:**
    - GitHub Actions の `Generate 52-Week Plan` ワークフローを手動で実行（workflow_dispatch）します。
2.  **自動運用:**
    - `Daily Video Production` ワークフローが毎日自動的に起動し、5本ずつ投稿予約を行います。

### 動画制作・投稿ワークフローの詳細
毎日実行される `Daily Video Production` アクションは、以下のプロセスを自動で繰り返します。

1.  **環境構築:** Java 8、Xvfb（仮想ディスプレイ）、FFmpeg、および Minecraft Forge 環境をセットアップします。
2.  **AIモデル取得:** 最新の Llama-3-8B GGUF モデルを自動ダウンロードします。
3.  **マイクラ起動:** ヘッドレス環境でマイクラを起動し、ワールドの読み込みが完了するまで待機します。
4.  **AI準備フェーズ:** 企画（`planning.json`）に基づき、AIが撮影前の準備コマンド（ゲームルール設定、時間変更、地形構築など）を自動実行します。
5.  **撮影フェーズ:** AIが Baritone を操作してメインのアクションを実行し、その様子を FFmpeg で録画します。
6.  **動画編集:** 録画した 1280x720 の映像を、背景ぼかし付きの 9:16 (Shorts) 形式に変換し、独自生成したBGMを合成します。
7.  **AIコンプラチェック:** 生成された内容に不適切な表現や行動が含まれていないか、LLMが最終確認を行います。
8.  **自動投稿:** YouTube API (OAuth2) を使用して、指定された日時に公開されるよう「予約投稿」を行います。

## コンプライアンスについて
`scripts/produce_video.py` にてAI（LLM）が動画内容を分析し、不適切な表現や行動（村人の殺害など）が含まれる場合は自動的に制作をスキップします。

## 注意事項
- 標準Runnerの制限時間（6時間）に収まるよう、1日5本に制限しています。
- YouTube APIの制限（クォータ）により、1日に投稿できる本数は制限される場合があります。
