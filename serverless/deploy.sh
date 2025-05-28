#!/bin/bash

# 環境変数をロード
source ../config/.env

echo "🚀 RSS要約システム (サーバレス版) をデプロイ中..."

# Cloud Functions APIを有効化
gcloud services enable cloudfunctions.googleapis.com --project=$PROJECT_ID

# Cloud Functionsをデプロイ
gcloud functions deploy rss-summarizer \
    --gen2 \
    --runtime=python311 \
    --region=asia-northeast1 \
    --source=. \
    --entry-point=rss_summarizer \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=540 \
    --memory=256MB \
    --set-env-vars="OPENAI_API_KEY=$OPENAI_API_KEY,NOTION_API_KEY=$NOTION_API_KEY,NOTION_DATABASE_ID=$NOTION_DATABASE_ID,RSS_FEEDS=https://www.lifehacker.jp/rss.xml,https://gigazine.net/news/rss_2.0/" \
    --project=$PROJECT_ID

echo "✅ デプロイ完了！"

# 関数のURLを取得
FUNCTION_URL=$(gcloud functions describe rss-summarizer --region=asia-northeast1 --project=$PROJECT_ID --format="value(serviceConfig.uri)")
echo "📋 Function URL: $FUNCTION_URL"

echo "🕒 Cloud Schedulerを設定中..."

# Cloud Scheduler APIを有効化
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Cloud Schedulerジョブを作成（15分間隔）
gcloud scheduler jobs create http rss-summarizer-job \
    --schedule="*/15 * * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=GET \
    --location=asia-northeast1 \
    --project=$PROJECT_ID \
    --description="RSS記事を15分ごとに要約してNotionに保存"

echo "✅ Cloud Scheduler設定完了！"
echo "💰 推定月額コスト: $2-4 (実行時のみ課金)" 