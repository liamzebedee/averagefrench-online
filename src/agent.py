#!/usr/bin/env python3
import sqlite3, json, random, pathlib, textwrap, time
from datetime import datetime
from ollama import chat

DB_PATH = "data/tweets.db"
CHARACTER_JSON_PATH = "data/character.json"
MODEL_NAME = "phi4-mini:latest"

PROMPT = """About {{agentName}} (@{{twitterUserName}}):
{{bio}}
{{lore}}

Recent posts:
{{recentPosts}}

# Task
Write exactly ONE tweet in the voice and style of {{agentName}}.
- Max 280 characters.
- One to three short lines only.
- No hashtags unless natural.
- No questions.
- Lowercase english unless a french phrase is natural.
- Brief, concise, and completely in-character.
- Never acknowledge this request.

Topic: {{adjective}} about {{topic}}, without mentioning {{topic}} directly.
The tweet must feel fresh and unlike the recent posts.

Example:
first cigarette of the day  
like a first love  

it kills

Now write the tweet. Output ONLY the tweet text, nothing else."""

def mustache(template: str, data: dict) -> str:
    for k, v in data.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template

def pick(items, k=1):
    items = list(items or [])
    if not items or k <= 0: return []
    k = min(k, len(items))
    return random.sample(items, k)

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        text TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS engagements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        score REAL,
        raw_data TEXT,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )""")
    conn.commit()
    conn.close()

def generate_post(char):
    name = char.get("name") or char.get("id") or "agent"
    handle = char.get("twitter", name)

    bio = " • ".join(pick(char.get("bio"), k=3))
    lore = " • ".join(pick(char.get("lore"), k=3))
    recent_posts = "\n".join(f"- {p}" for p in pick(char.get("postExamples"), k=5))
    adjective = random.choice(char.get("adjectives", ["laconic","direct","teasing"]))
    topic = random.choice(char.get("topics", ["cigarettes","romance","nighttime"]))

    prompt = mustache(PROMPT, {
        "agentName": name,
        "twitterUserName": handle,
        "bio": bio,
        "lore": lore,
        "recentPosts": recent_posts,
        "adjective": adjective,
        "topic": topic
    })

    resp = chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.8, "num_predict": 60}
    )

    return resp.message.content.strip()[:280]

def store_post(text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO posts (timestamp, text) VALUES (?, ?)",
        (datetime.utcnow().isoformat(), text)
    )
    conn.commit()
    conn.close()

def main():
    setup_db()
    char = json.loads(pathlib.Path(CHARACTER_JSON_PATH).read_text(encoding="utf-8"))

    for i in range(1000):
        tweet = generate_post(char)
        # store_post(tweet)
        print(f"[{i+1}/1000] {tweet}")

if __name__ == "__main__":
    main()
