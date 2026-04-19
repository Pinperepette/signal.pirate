"""
Estrae i tweet da MongoDB e li salva in data/tweets.json.
Esegui questo script una volta sola prima di tutti gli altri.

Struttura attesa in MongoDB:
  database: SnareData
  collection: twitter
  documento: { data: { data: { legacy: { full_text, lang, created_at }, promoted } } }
"""

import json
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB        = "SnareData"
COL       = "twitter"
OUT       = "data/tweets.json"

client = MongoClient(MONGO_URI)
col    = client[DB][COL]

tweets = []
skipped_promoted = 0
skipped_short    = 0

for doc in col.find({}, {"_id": 0}):
    try:
        inner  = doc.get("data", {}).get("data", {})
        legacy = inner.get("legacy", {})

        if inner.get("promoted"):
            skipped_promoted += 1
            continue

        text    = legacy.get("full_text", "")
        lang    = legacy.get("lang", "und")
        created = legacy.get("created_at", "")

        if len(text) < 15:
            skipped_short += 1
            continue

        tweets.append({"text": text, "lang": lang, "created_at": created})
    except Exception:
        continue

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(tweets, f, ensure_ascii=False, indent=2)

print(f"Estratti  : {len(tweets)} tweet")
print(f"Saltati   : {skipped_promoted} promossi, {skipped_short} troppo corti")
print(f"Output    : {OUT}")
