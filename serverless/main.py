import os
import json
import feedparser
import openai
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import functions_framework
from slack_sdk import WebhookClient
import requests
import re

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# RSS フィード一覧（多様な情報源）
RSS_FEEDS = [
    # 日本の主要テックサイト
    {"url": "https://gigazine.net/news/rss_2.0/", "name": "GIGAZINE", "lang": "ja"},
    {"url": "https://www.itmedia.co.jp/rss/2.0/news_ai.xml", "name": "ITmedia AI", "lang": "ja"},
    {"url": "https://www.publickey1.jp/atom.xml", "name": "Publickey", "lang": "ja"},
    {"url": "https://japan.zdnet.com/rss/index.rdf", "name": "ZDNet Japan", "lang": "ja"},
    {"url": "https://ascii.jp/rss.xml", "name": "ASCII.jp", "lang": "ja"},
    {"url": "https://www.watch.impress.co.jp/data/rss/1.0/ipw/feed.rdf", "name": "Impress Watch", "lang": "ja"},
    {"url": "https://tech.nikkeibp.co.jp/rss/index.rdf", "name": "日経xTECH", "lang": "ja"},
    {"url": "https://www.atmarkit.co.jp/rss/rss2dc.xml", "name": "@IT", "lang": "ja"},
    {"url": "https://codezine.jp/rss/new/20/index.xml", "name": "CodeZine", "lang": "ja"},
    {"url": "https://gihyo.jp/feed/rss2", "name": "技術評論社", "lang": "ja"},
    
    # 海外の主要テックサイト
    {"url": "https://feeds.feedburner.com/venturebeat/SZYF", "name": "VentureBeat", "lang": "en"},
    {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "lang": "en"},
    {"url": "https://feeds.feedburner.com/oreilly/radar", "name": "O'Reilly Radar", "lang": "en"},
    {"url": "https://rss.cnn.com/rss/cnn_tech.rss", "name": "CNN Tech", "lang": "en"},
    {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "lang": "en"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "name": "Ars Technica", "lang": "en"},
    {"url": "https://www.wired.com/feed/rss", "name": "WIRED", "lang": "en"},
    {"url": "https://feeds.feedburner.com/Techradar", "name": "TechRadar", "lang": "en"},
    {"url": "https://www.engadget.com/rss.xml", "name": "Engadget", "lang": "en"},
    {"url": "https://feeds.feedburner.com/Mashable", "name": "Mashable", "lang": "en"},
    {"url": "https://www.zdnet.com/news/rss.xml", "name": "ZDNet", "lang": "en"},
    {"url": "https://feeds.feedburner.com/TechCrunchIT", "name": "TechCrunch IT", "lang": "en"},
    
    # AI専門サイト
    {"url": "https://feeds.feedburner.com/aidaily", "name": "AI Daily", "lang": "en"},
    {"url": "https://www.artificialintelligence-news.com/feed/", "name": "AI News", "lang": "en"},
    {"url": "https://venturebeat.com/ai/feed/", "name": "VentureBeat AI", "lang": "en"},
    {"url": "https://www.unite.ai/feed/", "name": "Unite.AI", "lang": "en"},
    {"url": "https://towardsdatascience.com/feed", "name": "Towards Data Science", "lang": "en"},
    {"url": "https://machinelearningmastery.com/feed/", "name": "Machine Learning Mastery", "lang": "en"},
    {"url": "https://www.kdnuggets.com/feed", "name": "KDnuggets", "lang": "en"},
    {"url": "https://analyticsindiamag.com/feed/", "name": "Analytics India Magazine", "lang": "en"},
    {"url": "https://www.marktechpost.com/feed/", "name": "MarkTechPost", "lang": "en"},
    {"url": "https://syncedreview.com/feed/", "name": "Synced", "lang": "en"},
    
    # 学術・研究系
    {"url": "https://arxiv.org/rss/cs.AI", "name": "arXiv AI", "lang": "en"},
    {"url": "https://www.nature.com/subjects/machine-learning.rss", "name": "Nature ML", "lang": "en"},
    {"url": "https://arxiv.org/rss/cs.LG", "name": "arXiv Machine Learning", "lang": "en"},
    {"url": "https://arxiv.org/rss/cs.CL", "name": "arXiv NLP", "lang": "en"},
    {"url": "https://arxiv.org/rss/cs.CV", "name": "arXiv Computer Vision", "lang": "en"},
    {"url": "https://distill.pub/rss.xml", "name": "Distill", "lang": "en"},
    
    # 企業・スタートアップ系
    {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog", "lang": "en"},
    {"url": "https://blog.google/technology/ai/rss/", "name": "Google AI Blog", "lang": "en"},
    {"url": "https://engineering.fb.com/feed/", "name": "Meta Engineering", "lang": "en"},
    {"url": "https://blogs.microsoft.com/ai/feed/", "name": "Microsoft AI Blog", "lang": "en"},
    {"url": "https://aws.amazon.com/blogs/machine-learning/feed/", "name": "AWS ML Blog", "lang": "en"},
    {"url": "https://blog.tensorflow.org/feeds/posts/default", "name": "TensorFlow Blog", "lang": "en"},
    {"url": "https://pytorch.org/blog/feed.xml", "name": "PyTorch Blog", "lang": "en"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "Hugging Face Blog", "lang": "en"},
    {"url": "https://deepmind.com/blog/feed/basic/", "name": "DeepMind Blog", "lang": "en"},
    {"url": "https://blog.anthropic.com/rss.xml", "name": "Anthropic Blog", "lang": "en"},
    
    # 開発者・エンジニア向け
    {"url": "https://github.blog/feed/", "name": "GitHub Blog", "lang": "en"},
    {"url": "https://stackoverflow.blog/feed/", "name": "Stack Overflow Blog", "lang": "en"},
    {"url": "https://dev.to/feed", "name": "DEV Community", "lang": "en"},
    {"url": "https://hackernoon.com/feed", "name": "HackerNoon", "lang": "en"},
    {"url": "https://medium.com/feed/@towardsdatascience", "name": "Medium TDS", "lang": "en"},
    {"url": "https://www.infoq.com/feed/", "name": "InfoQ", "lang": "en"},
    
    # ビジネス・投資系（AI関連）
    {"url": "https://www.cbinsights.com/research/feed/", "name": "CB Insights", "lang": "en"},
    {"url": "https://pitchbook.com/news/feed", "name": "PitchBook", "lang": "en"},
    {"url": "https://www.crunchbase.com/feed", "name": "Crunchbase News", "lang": "en"},
    
    # 日本のAI・スタートアップ系
    {"url": "https://thebridge.jp/feed", "name": "THE BRIDGE", "lang": "ja"},
    {"url": "https://jp.techcrunch.com/feed/", "name": "TechCrunch Japan", "lang": "ja"},
    {"url": "https://www.startupdb.jp/feed", "name": "STARTUP DB", "lang": "ja"},
    {"url": "https://ainow.ai/feed/", "name": "AINOW", "lang": "ja"},
    {"url": "https://ledge.ai/feed/", "name": "Ledge.ai", "lang": "ja"}
]

# クライアント初期化
openai.api_key = OPENAI_API_KEY
db = firestore.Client()

# Slack通知クライアント
slack_client = WebhookClient(url=SLACK_WEBHOOK_URL) if SLACK_WEBHOOK_URL else None

def create_article_hash(url, title):
    """記事の重複チェック用ハッシュを生成"""
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()

def get_processed_articles():
    """Firestoreから処理済み記事のハッシュリストを取得"""
    try:
        docs = db.collection('ai_articles').select(['hash']).stream()
        processed_hashes = set()
        
        for doc in docs:
            data = doc.to_dict()
            if 'hash' in data:
                processed_hashes.add(data['hash'])
        
        return processed_hashes
    except Exception as e:
        logger.error(f"Firestore読み取りエラー: {e}")
        return set()

def is_ai_related_article(title, content):
    """GPTを使ってAI関連の最新ニュースかどうかを判定"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """あなたはAI・機械学習・テクノロジーの最新ニュース分類専門家です。
                    記事がAI、機械学習、人工知能、ChatGPT、Claude、Gemini、深層学習、
                    自然言語処理、コンピュータビジョン、ロボティクス、自動化技術、
                    データサイエンス、MLOps等に関連する「最新ニュース」かどうかを判定してください。
                    
                    【含める】新製品発表、企業発表、技術革新、買収・提携、規制・政策、研究成果
                    【除外する】用語解説、ハウツー記事、チュートリアル、基本概念説明、過去の振り返り
                    
                    判定結果は "YES" または "NO" のみで回答してください。"""
                },
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n内容: {content[:1500]}"
                }
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result == "YES"
    except Exception as e:
        logger.error(f"AI関連判定エラー: {e}")
        return False

def extract_primary_sources(content, title):
    """記事から1次情報のリンクを抽出"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """記事から1次情報のリンクを抽出してください。
                    優先順位：
                    1. 公式発表・プレスリリース
                    2. 企業公式サイト・ブログ
                    3. GitHub・技術文書
                    4. 公式Twitter/X投稿
                    5. 研究論文・学術サイト
                    
                    まとめサイトやニュースサイトのリンクは除外してください。
                    見つからない場合は "なし" と回答してください。"""
                },
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n記事内容: {content[:2000]}"
                }
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        return result if result != "なし" else None
    except Exception as e:
        logger.error(f"1次情報抽出エラー: {e}")
        return None

def summarize_with_openai(title, content, source_lang="en"):
    """OpenAI GPT-4o miniで記事を日本語で要約し、重要度も評価"""
    try:
        lang_instruction = "記事は英語ですが、" if source_lang == "en" else ""
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": f"""あなたはAI・テクノロジー記事の要約・評価スペシャリストです。
                    {lang_instruction}以下の作業を行ってください：
                    
                    1. 記事を日本語で分かりやすく3-5文で要約
                    2. AI初心者・エンジニアにとっての重要度を1-5で評価
                    
                    重要度基準：
                    5: 業界を変える革新的発表、大手企業の重要発表
                    4: 注目すべき新技術、重要な企業動向  
                    3: 興味深い開発、中程度の影響
                    2: 小さな更新、限定的な影響
                    1: 軽微なニュース、参考程度
                    
                    出力形式：
                    要約: [要約文]
                    重要度: [1-5の数値]"""
                },
                {
                    "role": "user",
                    "content": f"記事タイトル: {title}\n\n記事内容: {content[:3000]}"
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        
        # 要約と重要度を分離
        lines = result.split('\n')
        summary = ""
        importance_score = 3  # デフォルト値
        
        for line in lines:
            if line.startswith('要約:'):
                summary = line.replace('要約:', '').strip()
            elif line.startswith('重要度:'):
                try:
                    importance_score = int(line.replace('重要度:', '').strip())
                    importance_score = max(1, min(5, importance_score))  # 1-5の範囲に制限
                except ValueError:
                    importance_score = 3
        
        if not summary:
            summary = result  # フォーマットが異なる場合は全体を要約として使用
        
        return summary, importance_score
        
    except Exception as e:
        logger.error(f"OpenAI要約エラー: {e}")
        return "要約の生成に失敗しました。", 3

def save_to_firestore(title, url, summary, source, article_hash, source_lang, primary_source=None, importance_score=3):
    """要約をFirestoreに保存（拡張データ構造）"""
    try:
        doc_ref = db.collection('ai_articles').document()
        doc_ref.set({
            'title': title,
            'url': url,
            'summary': summary,
            'date': datetime.now(timezone.utc),
            'source': source,
            'source_lang': source_lang,
            'hash': article_hash,
            'primary_source': primary_source,
            'processed': True,
            'used_in_summary': False,  # X投稿まとめで使用済みかフラグ
            'importance_score': importance_score,     # 重要度スコア
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Firestoreに保存完了: {title}")
        return True
    except Exception as e:
        logger.error(f"Firestore保存エラー: {e}")
        return False

def get_recent_unused_articles(hours=24):
    """未使用の最近の記事を重要度順で取得"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # まず未使用の記事を全て取得（created_atフィールドがない場合も考慮）
        docs = db.collection('ai_articles').where(
            filter=firestore.FieldFilter('used_in_summary', '==', False)
        ).stream()
        
        articles = []
        for doc in docs:
            data = doc.to_dict()
            
            # created_atがない場合はdateフィールドを使用
            article_time = data.get('created_at')
            if not article_time:
                article_time = data.get('date')
            
            # 時間フィルタリング（フィールドがない場合は含める）
            if not article_time or article_time >= cutoff_time:
                articles.append({
                    'id': doc.id,
                    'title': data.get('title', ''),
                    'url': data.get('url', ''),
                    'summary': data.get('summary', ''),
                    'source': data.get('source', ''),
                    'primary_source': data.get('primary_source'),
                    'importance_score': data.get('importance_score', 3),
                    'created_at': article_time
                })
        
        # 重要度順でソート（高い順）、同じ重要度なら新しい順
        articles.sort(key=lambda x: (-x.get('importance_score', 3), -(x.get('created_at') or datetime.min).timestamp()))
        
        return articles
    except Exception as e:
        logger.error(f"未使用記事取得エラー: {e}")
        return []

def create_x_thread_summary(articles):
    """記事群からX投稿用のスレッドまとめを生成（★評価・参考リンク付き）"""
    try:
        articles_text = "\n\n".join([
            f"【{article['source']}】{article['title']}\n要約: {article['summary']}\n重要度: {article.get('importance_score', 3)}\n参考URL: {article['url']}\n1次情報: {article.get('primary_source', 'なし')}"
            for article in articles
        ])
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """あなたはAIニュースのキュレーション専門家です。
                    複数のAI関連記事から、X（Twitter）投稿用のスレッドを作成してください。
                    
                    出力形式：
                    【メインポスト】
                    - キャッチーで専門的な導入文（1-2行）
                    - 重要なニュース項目を重要度順（★の多い順）で番号付きリスト（簡潔な見出しのみ）
                    - 最後に「見逃せないニュースを[N]つスレッドにまとめています👇🧵」
                    
                    【詳細スレッド】
                    各項目について：
                    - 番号. 見出し ★★★★☆（重要度を★で表示）
                    - 詳細説明（2-3文、初心者にも分かりやすく）
                    - 参考: [参考URLをそのまま記載]
                    - 1次情報: [1次情報リンクがあれば記載、なければ省略]
                    
                    要件：
                    - 重要度（★の数）順に並べる
                    - 初心者にも分かりやすく
                    - 技術的すぎず、ビジネス的価値も含める
                    - 各詳細ポストは独立して理解できるように
                    - 参考URLは必ず含める"""
                },
                {
                    "role": "user",
                    "content": f"以下のAI関連記事からX投稿用スレッドを作成してください：\n\n{articles_text}"
                }
            ],
            max_tokens=2500,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Xまとめ生成エラー: {e}")
        return None

def mark_articles_as_used(article_ids):
    """記事を使用済みとしてマーク"""
    try:
        for article_id in article_ids:
            doc_ref = db.collection('ai_articles').document(article_id)
            doc_ref.update({'used_in_summary': True})
        logger.info(f"{len(article_ids)}件の記事を使用済みにマーク")
    except Exception as e:
        logger.error(f"使用済みマークエラー: {e}")

def send_slack_notification_summary(x_summary, article_count):
    """X投稿スレッドをSlackに通知"""
    if not slack_client or not x_summary:
        return
    
    try:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🐦 X投稿用AIニューススレッド（{article_count}件から生成）"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{x_summary}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 メインポスト＋詳細スレッドをコピーしてX（Twitter）に投稿できます"
                    }
                ]
            }
        ]
        
        response = slack_client.send(
            blocks=blocks,
            text=f"X投稿用AIニューススレッド（{article_count}件）"
        )
        
        logger.info(f"Slack通知送信完了: X投稿スレッド")
        return True
    except Exception as e:
        logger.error(f"Slack通知エラー: {e}")
        return False

def send_slack_notification(articles):
    """個別記事をSlackに通知（従来機能）"""
    if not slack_client or not articles:
        return
    
    try:
        article_list = []
        for article in articles:
            article_list.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{article['url']}|{article['title']}>*\n📍 {article['source']}\n💡 {article['summary'][:100]}..."
                }
            })
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🤖 AI関連記事 {len(articles)}件を検出"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        blocks.extend(article_list)
        
        response = slack_client.send(
            blocks=blocks,
            text=f"AI関連記事 {len(articles)}件を検出しました"
        )
        
        logger.info(f"Slack通知送信完了: {len(articles)}件")
        return True
    except Exception as e:
        logger.error(f"Slack通知エラー: {e}")
        return False

def get_recent_articles():
    """最近の記事を取得（管理用）"""
    try:
        docs = db.collection('ai_articles').order_by('created_at', direction=firestore.Query.DESCENDING).limit(20).stream()
        articles = []
        
        for doc in docs:
            data = doc.to_dict()
            articles.append({
                'title': data.get('title', ''),
                'url': data.get('url', ''),
                'source': data.get('source', ''),
                'summary': data.get('summary', ''),
                'source_lang': data.get('source_lang', ''),
                'primary_source': data.get('primary_source'),
                'used_in_summary': data.get('used_in_summary', False),
                'date': data.get('date', '').isoformat() if data.get('date') else ''
            })
        
        return articles
    except Exception as e:
        logger.error(f"記事取得エラー: {e}")
        return []

def get_thread_history(days=7):
    """過去のスレッド履歴を取得"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # 使用済み記事を取得（最近のもの）
        docs = db.collection('ai_articles').where(
            filter=firestore.FieldFilter('used_in_summary', '==', True)
        ).where(
            filter=firestore.FieldFilter('created_at', '>=', cutoff_time)
        ).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        threads = {}
        for doc in docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if created_at:
                # 6時間単位でグループ化（スレッド生成間隔に合わせる）
                thread_key = created_at.replace(hour=(created_at.hour // 6) * 6, minute=0, second=0, microsecond=0)
                
                if thread_key not in threads:
                    threads[thread_key] = []
                
                threads[thread_key].append({
                    'id': doc.id,
                    'title': data.get('title', ''),
                    'url': data.get('url', ''),
                    'summary': data.get('summary', ''),
                    'source': data.get('source', ''),
                    'primary_source': data.get('primary_source'),
                    'importance_score': data.get('importance_score', 3),
                    'created_at': created_at
                })
        
        # 各スレッドを重要度順でソート
        for thread_key in threads:
            threads[thread_key].sort(key=lambda x: -x.get('importance_score', 3))
        
        return threads
    except Exception as e:
        logger.error(f"スレッド履歴取得エラー: {e}")
        return {}

def create_custom_thread_from_selection(selected_article_ids):
    """選択された記事IDから新しいスレッドを作成"""
    try:
        # 選択された記事を取得
        selected_articles = []
        for article_id in selected_article_ids:
            doc = db.collection('ai_articles').document(article_id).get()
            if doc.exists:
                data = doc.to_dict()
                selected_articles.append({
                    'id': doc.id,
                    'title': data.get('title', ''),
                    'url': data.get('url', ''),
                    'summary': data.get('summary', ''),
                    'source': data.get('source', ''),
                    'primary_source': data.get('primary_source'),
                    'importance_score': data.get('importance_score', 3),
                    'created_at': data.get('created_at')
                })
        
        if not selected_articles:
            return None
        
        # 重要度順でソート
        selected_articles.sort(key=lambda x: -x.get('importance_score', 3))
        
        # スレッド生成
        thread_summary = create_x_thread_summary(selected_articles)
        
        return {
            'thread_summary': thread_summary,
            'articles_used': len(selected_articles),
            'articles': selected_articles
        }
    except Exception as e:
        logger.error(f"カスタムスレッド作成エラー: {e}")
        return None

@functions_framework.http
def rss_summarizer(request):
    """メインのRSS要約関数"""
    try:
        # GETパラメータで機能を分岐
        action = request.args.get('action', 'collect')
        
        if action == 'list':
            articles = get_recent_articles()
            return json.dumps({
                'status': 'success',
                'articles': articles,
                'count': len(articles)
            }, ensure_ascii=False, indent=2), 200
        
        elif action == 'history':
            # 過去のスレッド履歴を取得
            days = int(request.args.get('days', 7))
            thread_history = get_thread_history(days)
            
            return json.dumps({
                'status': 'success',
                'action': 'history',
                'thread_history': {k.isoformat(): v for k, v in thread_history.items()},
                'thread_count': len(thread_history),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, ensure_ascii=False, indent=2), 200
        
        elif action == 'custom':
            # 選択された記事からカスタムスレッドを作成
            selected_ids = request.args.get('ids', '').split(',')
            selected_ids = [id.strip() for id in selected_ids if id.strip()]
            
            if not selected_ids:
                return json.dumps({
                    'status': 'error',
                    'message': 'idsパラメータが必要です（カンマ区切り）'
                }, ensure_ascii=False), 400
            
            result = create_custom_thread_from_selection(selected_ids)
            if result:
                return json.dumps({
                    'status': 'success',
                    'action': 'custom_thread_created',
                    'articles_used': result['articles_used'],
                    'thread_summary': result['thread_summary'],
                    'articles': result['articles'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, ensure_ascii=False, indent=2), 200
            else:
                return json.dumps({
                    'status': 'error',
                    'message': 'カスタムスレッドの作成に失敗しました'
                }, ensure_ascii=False), 500
        
        elif action == 'summary':
            # X投稿用まとめ生成
            unused_articles = get_recent_unused_articles(24)
            if len(unused_articles) >= 3:  # 最低3件以上で実行
                x_summary = create_x_thread_summary(unused_articles)
                if x_summary:
                    # 使用済みマーク
                    article_ids = [article['id'] for article in unused_articles]
                    mark_articles_as_used(article_ids)
                    
                    # Slack通知
                    send_slack_notification_summary(x_summary, len(unused_articles))
                    
                    return json.dumps({
                        'status': 'success',
                        'action': 'summary_created',
                        'articles_used': len(unused_articles),
                        'x_summary': x_summary,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }, ensure_ascii=False, indent=2), 200
            
            return json.dumps({
                'status': 'success',
                'action': 'summary_skipped',
                'reason': f'記事数不足（{len(unused_articles)}件、最低3件必要）',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, ensure_ascii=False, indent=2), 200
        
        # デフォルト: 記事収集
        logger.info("AI関連RSS要約処理を開始")
        processed_hashes = get_processed_articles()
        new_articles_count = 0
        processed_articles = []
        
        for feed_config in RSS_FEEDS:
            feed_url = feed_config["url"]
            feed_name = feed_config["name"]
            feed_lang = feed_config["lang"]
            
            logger.info(f"RSS取得中: {feed_name} ({feed_url})")
            
            try:
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:
                    logger.warning(f"RSS解析警告: {feed_name}")
                    continue
                
                # 最新3記事を処理
                for entry in feed.entries[:3]:
                    title = entry.title
                    url = entry.link
                    content = entry.get('summary', '') or entry.get('description', '')
                    
                    # 重複チェック
                    article_hash = create_article_hash(url, title)
                    if article_hash in processed_hashes:
                        continue
                    
                    # AI関連記事かどうか判定
                    if not is_ai_related_article(title, content):
                        logger.info(f"AI関連外記事をスキップ: {title}")
                        continue
                    
                    logger.info(f"AI関連記事を処理中: {title}")
                    
                    # 要約生成
                    summary, importance_score = summarize_with_openai(title, content, feed_lang)
                    
                    # 1次情報抽出
                    primary_source = extract_primary_sources(content, title)
                    
                    # Firestoreに保存
                    if save_to_firestore(title, url, summary, feed_name, article_hash, feed_lang, primary_source, importance_score):
                        new_articles_count += 1
                        processed_hashes.add(article_hash)
                        processed_articles.append({
                            'title': title,
                            'url': url,
                            'source': feed_name,
                            'summary': summary,
                            'primary_source': primary_source,
                            'importance_score': importance_score
                        })
                        
            except Exception as e:
                logger.error(f"フィード処理エラー ({feed_name}): {e}")
                continue
        
        # 新しい記事があれば個別通知
        if processed_articles:
            send_slack_notification(processed_articles)
        
        result = {
            'status': 'success',
            'action': 'collect',
            'new_ai_articles': new_articles_count,
            'articles': processed_articles,
            'total_feeds_checked': len(RSS_FEEDS),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"処理完了: {new_articles_count}件のAI関連記事")
        return json.dumps(result, ensure_ascii=False, indent=2), 200
        
    except Exception as e:
        logger.error(f"メイン処理エラー: {e}")
        return json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False), 500 