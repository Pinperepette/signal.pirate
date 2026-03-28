#!/usr/bin/env python3
"""
00_extract.py — Estrai dati da MongoDB (SnareData) in CSV replicabili.

Legge le collection twitter_per-te e twitter_seguiti,
normalizza i campi utili e salva due CSV identici come schema.

Uso:
    python 00_extract.py

Output:
    data/per_te.csv
    data/seguiti.csv

Schema CSV:
    feed, tweet_id, created_at, screen_name, name, followers_count,
    is_blue_verified, following, full_text, lang,
    favorite_count, retweet_count, reply_count, bookmark_count, quote_count,
    hashtags, urls_count, mentions_count, has_media,
    sentiment, emotions, intensity
"""

import csv
import os
from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017'
DB_NAME = 'SnareData'
COLLECTIONS = {
    'per_te': 'twitter_per-te',
    'seguiti': 'twitter_seguiti',
}
OUTPUT_DIR = 'data'
LIMIT = 800

FIELDS = [
    'feed', 'tweet_id', 'created_at', 'screen_name', 'name',
    'user_id', 'followers_count', 'is_blue_verified', 'following',
    'full_text', 'lang',
    'favorite_count', 'retweet_count', 'reply_count',
    'bookmark_count', 'quote_count',
    'hashtags', 'urls_count', 'mentions_count', 'has_media',
    'sentiment', 'emotions', 'intensity',
]


def safe_get(d, *keys, default=None):
    """Naviga un dict annidato senza errori."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
    return d if d is not None else default


def extract_tweet(doc, feed_label):
    """Estrai campi flat da un documento MongoDB."""
    data = safe_get(doc, 'data', 'data', default={})
    legacy = safe_get(data, 'legacy', default={})
    user = safe_get(data, 'core', 'user_results', 'result', default={})
    user_core = safe_get(user, 'core', default={})
    user_legacy = safe_get(user, 'legacy', default={})
    rel = safe_get(user, 'relationship_perspectives', default={})
    entities = safe_get(legacy, 'entities', default={})

    hashtags_list = [h.get('text', '') for h in entities.get('hashtags', [])]
    has_media = bool(
        safe_get(data, 'mediaDetails')
        or safe_get(legacy, 'extended_entities', 'media')
        or entities.get('media')
    )

    return {
        'feed': feed_label,
        'tweet_id': legacy.get('id_str', safe_get(doc, 'data', 'item_id', default='')),
        'created_at': legacy.get('created_at', ''),
        'screen_name': user_core.get('screen_name', ''),
        'name': user_core.get('name', ''),
        'user_id': user.get('rest_id', ''),
        'followers_count': user_legacy.get('followers_count', 0),
        'is_blue_verified': user.get('is_blue_verified', False),
        'following': rel.get('following', False),
        'full_text': legacy.get('full_text', ''),
        'lang': legacy.get('lang', ''),
        'favorite_count': legacy.get('favorite_count', 0),
        'retweet_count': legacy.get('retweet_count', 0),
        'reply_count': legacy.get('reply_count', 0),
        'bookmark_count': legacy.get('bookmark_count', 0),
        'quote_count': legacy.get('quote_count', 0),
        'hashtags': '|'.join(hashtags_list),
        'urls_count': len(entities.get('urls', [])),
        'mentions_count': len(entities.get('user_mentions', [])),
        'has_media': has_media,
        'sentiment': doc.get('sentiment', ''),
        'emotions': '|'.join(doc.get('emotions', [])),
        'intensity': doc.get('intensity', ''),
    }


def export_collection(db, collection_name, feed_label, output_path):
    """Esporta una collection in CSV."""
    coll = db[collection_name]
    cursor = coll.find().limit(LIMIT)

    rows = []
    for doc in cursor:
        row = extract_tweet(doc, feed_label)
        if row['full_text']:  # skip vuoti
            rows.append(row)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    for label, coll_name in COLLECTIONS.items():
        path = os.path.join(OUTPUT_DIR, f'{label}.csv')
        n = export_collection(db, coll_name, label, path)
        print(f'[+] {label}: {n} tweet -> {path}')

    client.close()
    print('[✓] Estrazione completata.')


if __name__ == '__main__':
    main()
