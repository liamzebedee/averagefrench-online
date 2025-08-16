#!/usr/bin/env python3

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType
import torch
import json
import random
import gc


def mustache(template: str, data: dict) -> str:
    for k, v in data.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template

def pick(items, k=1):
    items = list(items or [])
    if not items or k <= 0: return []
    k = min(k, len(items))
    return random.sample(items, k)

def gen_inference_prompt():
    char_path = Path(__file__).parent.parent.parent / "data" / "character.json"
    char = json.loads(char_path.read_text(encoding="utf-8"))
    name = char.get("name") or char.get("id") or "agent"
    handle = char.get("twitter", name)

    bio = " • ".join(pick(char.get("bio"), k=3))
    lore = " • ".join(pick(char.get("lore"), k=3))
    recent_posts = "\n".join(f"- {p}" for p in pick(char.get("postExamples"), k=5))
    adjective = random.choice(char.get("adjectives", ["laconic","direct","teasing"]))
    topic = random.choice(char.get("topics", ["cigarettes","romance","nighttime"]))

    PROMPT = """You are {{agentName}} (@{{twitterUserName}}).
{{bio}}
{{lore}}

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

Example Output:
"first cigarette of the day  
like a first love  

it kills"

Output:
"""

    prompt = mustache(PROMPT, {
        "agentName": name,
        "twitterUserName": handle,
        "bio": bio,
        "lore": lore,
        "recentPosts": recent_posts,
        "adjective": adjective,
        "topic": topic
    })

    return prompt
gen_inference_prompt()








# Load base Qwen model
print("Loading base Qwen model...")
model_name = "microsoft/Phi-3-mini-4k-instruct"
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(model_name)
# base = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map=None)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16).to(device)
# model = AutoModelForCausalLM.from_config(base.config).to(dtype=torch.float16)
# model.load_state_dict(base.state_dict(), strict=True)
# del base; gc.collect(); torch.cuda.empty_cache()

# model = model.to(device)
model.gradient_checkpointing_enable()
# model.config.use_cache = False
model.train()

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    print(f"Set pad_token to eos_token: {tokenizer.pad_token}")

print("Model loaded successfully!")

# Initialize generation counter
generation = 0

print("Entering training loop...")
print("Press Ctrl+C to stop")

while True:
    print(f"\n{'='*50}")
    print(f"ONLINE TRAIN GENERATION {generation}")
    print(f"{'='*50}")
    
    # Get recent engaging tweets
    print("Fetching recent engaging tweets...")
    
    db_path = Path(__file__).parent.parent.parent / "data" / "tweets.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cutoff_time = int((datetime.now() - timedelta(hours=2)).timestamp())
    
    cursor.execute('''
        SELECT p.id, p.text, p.timestamp,
               COUNT(DISTINCT CASE WHEN e.type = 'like' THEN e.id END) as like_count,
               COUNT(DISTINCT CASE WHEN e.type = 'reply' THEN e.id END) as reply_count,
               COUNT(DISTINCT CASE WHEN e.type = 'clanked' THEN e.id END) as clanked_count
        FROM posts p
        LEFT JOIN new_engagements e ON p.id = e.post_id
        WHERE p.user = 'AverageFrench' 
          AND p.timestamp > ?
        GROUP BY p.id
        HAVING (like_count + reply_count + clanked_count) > 0
        ORDER BY p.timestamp DESC
        LIMIT 15
    ''', (cutoff_time,))
    
    tweets = []
    for row in cursor.fetchall():
        likes = row[3]
        replies = row[4]
        clanks = row[5]
        total_engagements = likes + replies - clanks
        tweets.append({
            'text': row[1],
            'total_engagements': total_engagements
        })
    
    conn.close()
    
    if not tweets:
        print("No engaging tweets found in the past 2 hours")
        print("Waiting 1 minute before next iteration...")
        time.sleep(60)
        generation += 1
        continue
    
    print(f"Found {len(tweets)} engaging tweets")
    
    # Create fine-tuning prompt
    best_tweets = sorted(tweets, key=lambda x: x['total_engagements'], reverse=True)[:5]
    bad_tweets = sorted(tweets, key=lambda x: x['total_engagements'])[:3]
    
    fine_tune_prompt = "You are @averagefrench.\n\n"
    fine_tune_prompt += "Best tweets:\n"
    for tweet in best_tweets:
        fine_tune_prompt += f"- {tweet['text']}\n"
    
    fine_tune_prompt += "Worst tweets:\n"
    for tweet in bad_tweets:
        fine_tune_prompt += f"- {tweet['text']}\n"
    
        
    print("Fine-tuning prompt created")
    
    # Fine-tune model
    print("Starting fine-tuning...")
    
    
    
    # Prepare training data - simple text format, no chat template
    inputs = tokenizer(fine_tune_prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
    
    # Set model to training mode
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    model.train()

    # 8-bit Adam to keep optimizer memory low
    import bitsandbytes as bnb
    opt = bnb.optim.Adam8bit(model.parameters(), lr=1e-5)  # Lower learning rate

    for step in range(10):
        opt.zero_grad(set_to_none=True)
        out = model(inputs.input_ids, labels=inputs.input_ids)  # Use input_ids for both
        loss = out.loss
        
        # Check for NaN loss
        if torch.isnan(loss):
            print(f"NaN loss detected at step {step}, skipping...")
            continue
            
        loss.backward()
        
        # Gradient clipping to prevent explosion
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        opt.step()
        
        print(f"step {step} loss {loss.item():.4f}")

    # ---- save for later inference ----
    model.gradient_checkpointing_disable()
    model.config.use_cache = True
    model.eval()

    
    # Generate completions
    print("Generating completions...")
    
    inference_prompt = gen_inference_prompt()

    completions = []
    
    for i in range(10):
        # Simple text encoding without chat template
        inputs = tokenizer(inference_prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                temperature=0.9,
                do_sample=True,
                num_return_sequences=1,
                max_new_tokens=64,  # Shorter to avoid empty outputs
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,  # Use eos as pad
                eos_token_id=tokenizer.eos_token_id,
                bos_token_id=tokenizer.bos_token_id if tokenizer.bos_token_id else None
            )
        
        # Decode the full output and extract just the new part
        full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove the input prompt to get just the generated part
        if full_output.startswith(inference_prompt):
            generated_text = full_output[len(inference_prompt):].strip()
        else:
            generated_text = full_output.strip()

        print(f"Generated {i+1}: '{generated_text}'")
        
        if generated_text and len(generated_text) <= 280 and len(generated_text) > 5:  # Ensure it's not too short
            completions.append(generated_text)
            
    
    # Insert generated tweets
    if completions:
        print("Inserting generated tweets...")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        for i, text in enumerate(completions):
            cursor.execute('''
                INSERT INTO posts (text, user, timestamp)
                VALUES (?, ?, ?)
            ''', (text, 'AverageFrench', current_time))
        
        conn.commit()
        conn.close()
        
        print(f"Inserted {len(completions)} generated tweets for generation {generation}")
    else:
        print("No valid completions generated")
    
    # Wait 1 minute
    print("Waiting 1 minute before next generation...")
    # time.sleep(60)
    
    generation += 1
