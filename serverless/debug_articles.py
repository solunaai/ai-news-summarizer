#!/usr/bin/env python3
"""
Firestoreの記事データを確認するデバッグスクリプト
"""

from google.cloud import firestore

def debug_articles():
    """記事データの状態を確認"""
    db = firestore.Client()
    
    try:
        # 全ての記事を取得
        docs = db.collection('ai_articles').stream()
        
        print("=== 全記事の状態確認 ===")
        count = 0
        for doc in docs:
            data = doc.to_dict()
            count += 1
            
            print(f"\n📄 記事 {count}:")
            print(f"  ID: {doc.id}")
            print(f"  タイトル: {data.get('title', 'なし')[:50]}...")
            print(f"  ソース: {data.get('source', 'なし')}")
            print(f"  used_in_summary: {data.get('used_in_summary', 'フィールドなし')}")
            print(f"  created_at: {data.get('created_at', 'なし')}")
            print(f"  date: {data.get('date', 'なし')}")
        
        print(f"\n✅ 合計 {count} 件の記事を確認しました")
        
        # 未使用記事のみ確認
        print("\n=== 未使用記事の確認 ===")
        unused_docs = db.collection('ai_articles').where('used_in_summary', '==', False).stream()
        
        unused_count = 0
        for doc in unused_docs:
            unused_count += 1
            data = doc.to_dict()
            print(f"  未使用記事 {unused_count}: {data.get('title', 'なし')[:30]}...")
        
        print(f"✅ 未使用記事: {unused_count} 件")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    debug_articles() 