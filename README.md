# AI情報取得・要約システム MVP

## 概要
RSS/NewsとYouTube動画の自動要約システム。n8n + Cloud Runアーキテクチャで構築。

## MVPの範囲
- RSS/Newsフィードの15分毎ポーリング
- GPT-4o miniによる要約生成
- Notionデータベースへの保存
- Slackへの通知

## アーキテクチャ
```
Cloud Scheduler → n8n (Cloud Run) → OpenAI API → Notion
                                  → Slack通知
```

## 構成
- `docker/`: n8n Dockerセットアップ
- `workflows/`: n8nワークフロー定義
- `scripts/`: デプロイ・管理スクリプト
- `docs/`: 設定手順・API仕様

## 推定コスト（月額）
- Cloud Run: 無料枠内
- Cloud Scheduler: ~$0.07
- OpenAI API: ~$3.6
- 合計: ~$4/月

## セットアップ手順
1. GCPプロジェクト作成・設定
2. n8n Docker環境構築
3. Cloud Runデプロイ
4. ワークフロー設定
5. Cloud Scheduler設定 
