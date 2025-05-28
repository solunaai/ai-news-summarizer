#!/usr/bin/env python3
"""
既存記事を未使用状態にリセットするスクリプト（テスト用）
"""

from google.cloud import firestore

def reset_articles_to_unused():
    """全ての記事を未使用状態にリセット"""
    db = firestore.Client()
    
    try:
        # 全ての記事を取得
        docs = db.collection('ai_articles').stream()
        
        count = 0
        for doc in docs:
            # used_in_summaryフィールドを追加/更新
            doc.reference.update({
                'used_in_summary': False,
                'primary_source': None  # 既存記事には1次情報がないため
            })
            count += 1
        
        print(f"✅ {count}件の記事を未使用状態にリセットしました")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    reset_articles_to_unused() 