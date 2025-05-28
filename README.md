# AI情報取得・要約システム セットアップ手順書

## 📋 システム概要

このシステムは、ニュースのRSSフィードを自動的に監視し、OpenAI GPT-4o miniで要約してFirestoreに保存、Slackに通知するサーバレスシステムです。

### 主な機能
- 70以上のRSSフィード（日本語・英語）の15分間隔での自動監視
- AI関連記事の自動判定・フィルタリング
- GPT-4o miniによる日本語要約生成
- 重要度スコア付与
- Firestore（NoSQLデータベース）への保存
- Slack通知機能
- Webダッシュボードでの記事閲覧


### 前提
- 技術的に不明な箇所等あればAI（ChatGPT）等を活用しながら疑問点を解決していただけますと幸いです。

### アーキテクチャ
```
Cloud Scheduler → Cloud Functions → OpenAI API → Firestore
                                 → Slack通知
```

### 推定月額コスト
- Cloud Functions: 無料枠内（月100万リクエストまで無料）
- Cloud Scheduler: 約$0.07
- OpenAI API: 約$3-6（使用量による）
- Firestore: 無料枠内（月50,000読み取り、20,000書き込みまで無料）
- **合計: 約$4-7/月**

---

## 🛠️ 事前準備

### 1. 必要なアカウント・サービス

#### 1.1 Googleアカウント
- Gmailアカウントが必要
- Google Cloud Platform（GCP）の利用に使用

#### 1.2 OpenAIアカウント
- ChatGPTのAPIを利用するため
- クレジットカード登録が必要（従量課金）

#### 1.3 Slackワークスペース（オプション）
- 通知を受け取りたい場合

### 2. 開発環境の準備

#### 2.1 Gitのインストール

**Windows:**
1. https://git-scm.com/download/win からダウンロード
2. インストーラーを実行し、デフォルト設定でインストール
3. コマンドプロンプトまたはPowerShellで `git --version` を実行して確認

**Mac:**
1. ターミナルを開く
2. `git --version` を実行
3. インストールされていない場合、Xcodeコマンドラインツールのインストールが促される
4. または Homebrew を使用: `brew install git`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install git
```

#### 2.2 Google Cloud CLIのインストール

**Windows:**
1. https://cloud.google.com/sdk/docs/install からインストーラーをダウンロード
2. インストーラーを実行
3. インストール後、新しいコマンドプロンプトを開く

**Mac:**
```bash
# Homebrewを使用
brew install --cask google-cloud-sdk

# または公式インストーラー
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Linux:**
```bash
# Debian/Ubuntu
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-cli
```

#### 2.3 Pythonのインストール（ローカル開発用）

**Windows:**
1. https://www.python.org/downloads/ からPython 3.11をダウンロード
2. インストール時に「Add Python to PATH」をチェック

**Mac:**
```bash
# Homebrewを使用
brew install python@3.11
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip
```

---

## 🔧 Google Cloud Platform セットアップ

### 1. GCPプロジェクトの作成

1. **Google Cloud Console にアクセス**
   - https://console.cloud.google.com/ にアクセス
   - Googleアカウントでログイン

2. **新しいプロジェクトを作成**
   - 画面上部の「プロジェクトを選択」をクリック
   - 「新しいプロジェクト」をクリック
   - プロジェクト名を入力（例: `ai-news-summarizer`）
   - 「作成」をクリック

3. **請求先アカウントの設定**
   - 左側メニューから「お支払い」を選択
   - 請求先アカウントを作成（クレジットカード情報が必要）
   - 新規ユーザーは$300の無料クレジットが付与されます

### 2. 必要なAPIの有効化

Google Cloud Consoleで以下のAPIを有効化します：

1. **Cloud Functions API**
   - 左側メニュー → 「APIとサービス」 → 「ライブラリ」
   - 「Cloud Functions API」を検索
   - 「有効にする」をクリック±

2. **Cloud Scheduler API**
   - 同様に「Cloud Scheduler API」を検索して有効化

3. **Firestore API**
   - 「Cloud Firestore API」を検索して有効化

4. **Cloud Build API**
   - 「Cloud Build API」を検索して有効化

### 3. Firestoreデータベースの作成

1. **Firestoreの設定**
   - 左側メニュー → 「Firestore」
   - 「データベースを作成」をクリック
   - 「ネイティブモード」を選択
   - ロケーション: `asia-northeast1` (東京) を選択
   - 「作成」をクリック

2. **セキュリティルールの設定**
   - 「ルール」タブをクリック
   - 以下のルールを設定:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if true;
       }
     }
   }
   ```
   - 「公開」をクリック

### 4. Google Cloud CLIの認証

ターミナル（コマンドプロンプト）で以下を実行：

```bash
# Google Cloud CLIにログイン
gcloud auth login

# プロジェクトを設定（YOUR_PROJECT_IDは作成したプロジェクトIDに置き換え）
gcloud config set project YOUR_PROJECT_ID

# アプリケーションデフォルト認証を設定
gcloud auth application-default login
```

---

## 🔑 APIキーの取得

### 1. OpenAI APIキーの取得

1. **OpenAIアカウントの作成**
   - https://platform.openai.com/ にアクセス
   - 「Sign up」でアカウント作成
   - 電話番号認証が必要

2. **APIキーの生成**
   - ログイン後、右上のアカウントメニューから「API keys」を選択
   - 「Create new secret key」をクリック
   - 名前を入力（例: `ai-news-summarizer`）
   - 生成されたキーをコピーして安全に保存
   - **⚠️ このキーは二度と表示されないので必ず保存してください**

3. **使用量制限の設定**
   - 左側メニューから「Usage limits」を選択
   - 月額上限を設定（例: $10）して予期しない課金を防ぐ

### 2. Slack Webhook URL の取得（オプション）

通知機能を使用する場合：

1. **Slackアプリの作成**
   - https://api.slack.com/apps にアクセス
   - 「Create New App」をクリック
   - 「From scratch」を選択
   - アプリ名とワークスペースを選択

2. **Incoming Webhookの有効化**
   - 左側メニューから「Incoming Webhooks」を選択
   - 「Activate Incoming Webhooks」をオンにする
   - 「Add New Webhook to Workspace」をクリック
   - 通知を送信するチャンネルを選択
   - Webhook URLをコピーして保存

---

## 📥 プロジェクトのダウンロード

### 1. リポジトリのクローン

ターミナルで以下を実行：

```bash
# 作業ディレクトリに移動（例: デスクトップ）
cd ~/Desktop

# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/ai-news-summarizer.git

# プロジェクトディレクトリに移動
cd ai-news-summarizer
```

### 2. 環境変数ファイルの作成

1. **configディレクトリの作成**
```bash
mkdir config
```

2. **環境変数ファイルの作成**
`config/.env` ファイルを作成し、以下の内容を記述：

```bash
# Google Cloud Project ID
PROJECT_ID=your-project-id

# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key

# Slack Webhook URL (オプション)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Notion設定（使用しない場合は空でOK）
NOTION_API_KEY=
NOTION_DATABASE_ID=
```

**⚠️ 重要な注意事項:**
- `your-project-id` は実際のGCPプロジェクトIDに置き換え
- `sk-your-openai-api-key` は取得したOpenAI APIキーに置き換え
- Slack通知が不要な場合は `SLACK_WEBHOOK_URL` の行を削除またはコメントアウト

---

## 🚀 デプロイ手順

### 1. デプロイスクリプトの実行

```bash
# serverlessディレクトリに移動
cd serverless

# デプロイスクリプトに実行権限を付与
chmod +x deploy.sh

# デプロイを実行
./deploy.sh
```

### 2. デプロイの確認

デプロイが成功すると以下のような出力が表示されます：

```
🚀 RSS要約システム (サーバレス版) をデプロイ中...
✅ デプロイ完了！
📋 Function URL: https://asia-northeast1-your-project.cloudfunctions.net/rss-summarizer
🕒 Cloud Schedulerを設定中...
✅ Cloud Scheduler設定完了！
💰 推定月額コスト: $2-4 (実行時のみ課金)
```

### 3. 動作確認

1. **手動実行テスト**
```bash
# 表示されたFunction URLにアクセス
curl "https://asia-northeast1-your-project.cloudfunctions.net/rss-summarizer"
```

2. **Google Cloud Consoleでの確認**
   - Cloud Functions → `rss-summarizer` → 「ログ」タブで実行ログを確認
   - Firestore → `ai_articles` コレクションに記事が保存されているか確認

---

## 📊 Webダッシュボードの設定

### 1. ダッシュボードのデプロイ

```bash
# プロジェクトルートに戻る
cd ..

# App Engineアプリケーションを作成
gcloud app create --region=asia-northeast1

# ダッシュボードをデプロイ
cd serverless
gcloud app deploy --quiet
```

### 2. ダッシュボードへのアクセス

デプロイ完了後、以下のURLでダッシュボードにアクセスできます：
```
https://your-project-id.appspot.com
```

---

## ⚙️ システム設定のカスタマイズ

### 1. RSS フィードの追加・削除

`serverless/main.py` の `RSS_FEEDS` リストを編集：

```python
RSS_FEEDS = [
    {"url": "https://example.com/rss.xml", "name": "Example Site", "lang": "ja"},
    # 新しいフィードを追加
]
```

### 2. 実行間隔の変更

`serverless/deploy.sh` の cron 設定を変更：

```bash
# 現在: 15分間隔
--schedule="*/15 * * * *"

# 例: 30分間隔に変更
--schedule="*/30 * * * *"

# 例: 1時間間隔に変更
--schedule="0 * * * *"
```

### 3. 要約の品質調整

`serverless/main.py` の `summarize_with_openai` 関数内のプロンプトを調整可能

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. デプロイエラー: "API not enabled"
```bash
# 必要なAPIを手動で有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### 2. 認証エラー
```bash
# 認証を再実行
gcloud auth login
gcloud auth application-default login
```

#### 3. OpenAI APIエラー
- APIキーが正しく設定されているか確認
- OpenAIアカウントに十分なクレジットがあるか確認
- 使用量制限に達していないか確認

#### 4. Firestore書き込みエラー
- Firestoreのセキュリティルールが正しく設定されているか確認
- プロジェクトでFirestore APIが有効になっているか確認

#### 5. Cloud Scheduler が動作しない
```bash
# Cloud Schedulerの状態確認
gcloud scheduler jobs list --location=asia-northeast1

# ジョブの手動実行
gcloud scheduler jobs run rss-summarizer-job --location=asia-northeast1
```

### ログの確認方法

1. **Cloud Functions のログ**
```bash
gcloud functions logs read rss-summarizer --region=asia-northeast1
```

2. **Google Cloud Console でのログ確認**
   - Cloud Functions → `rss-summarizer` → 「ログ」タブ

---

## 📈 運用・メンテナンス

### 1. コスト監視

1. **請求アラートの設定**
   - Google Cloud Console → 「お支払い」 → 「予算とアラート」
   - 月額$10などの上限を設定

2. **使用量の確認**
   - OpenAI Usage dashboard で API使用量を定期確認
   - Google Cloud Console で各サービスの使用量を確認

### 2. データベースのメンテナンス

古い記事データの削除（オプション）：

```bash
# 30日以上古い記事を削除するスクリプトの実行
cd serverless
python reset_articles.py
```

### 3. システムの停止

一時的にシステムを停止する場合：

```bash
# Cloud Scheduler ジョブを無効化
gcloud scheduler jobs pause rss-summarizer-job --location=asia-northeast1

# 再開する場合
gcloud scheduler jobs resume rss-summarizer-job --location=asia-northeast1
```

完全に削除する場合：

```bash
# Cloud Functions を削除
gcloud functions delete rss-summarizer --region=asia-northeast1

# Cloud Scheduler ジョブを削除
gcloud scheduler jobs delete rss-summarizer-job --location=asia-northeast1
```

---

## 🔒 セキュリティ考慮事項

### 1. APIキーの管理
- `.env` ファイルは絶対にGitにコミットしない
- APIキーは定期的にローテーション
- 不要になったキーは即座に削除

### 2. アクセス制御
- Firestoreのセキュリティルールを本番環境では厳格に設定
- Cloud Functions の認証設定を必要に応じて変更

### 3. 監視
- 異常なAPI使用量がないか定期的に確認
- 不正アクセスの兆候がないかログを監視

---

## 📞 サポート・問い合わせ

### 技術的な問題
1. まずはこの手順書のトラブルシューティングセクションを確認
2. Google Cloud の公式ドキュメントを参照
3. OpenAI の公式ドキュメントを参照

### 緊急時の対応
システムに問題が発生した場合：
1. Cloud Scheduler を一時停止
2. ログを確認して原因を特定
3. 必要に応じてCloud Functions を再デプロイ

---

## 📚 参考資料

- [Google Cloud Functions ドキュメント](https://cloud.google.com/functions/docs)
- [OpenAI API ドキュメント](https://platform.openai.com/docs)
- [Firestore ドキュメント](https://cloud.google.com/firestore/docs)
- [Cloud Scheduler ドキュメント](https://cloud.google.com/scheduler/docs)

---

**🎉 セットアップ完了！**

これで AI情報取得・要約システムが稼働開始します。15分間隔でAI関連の最新ニュースが自動的に収集・要約され、Firestoreに保存されます。Webダッシュボードで記事を確認し、Slackで通知を受け取ることができます。

何か問題が発生した場合は、このドキュメントのトラブルシューティングセクションを参照してください。 