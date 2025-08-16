#!/usr/bin/env python3
import torch, gc
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "./phi3_full_ft_fp16"
device = "cuda" if torch.cuda.is_available() else "cpu"

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
if tok.pad_token_id is None:
    tok.pad_token_id = tok.eos_token_id

model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32
).to(device)
model.eval()

prompts = [
    "Write a two-sentence idea for a sci-fi short.",
    "Give a quirky startup concept involving fruit.",
    "Explain a simple morning routine for focus.",
    "Describe a cyberpunk city in 3 lines.",
    "Pitch a mobile app for healthy snacking.",
    "Write a haiku about the ocean.",
    "Suggest a fun weekend experiment.",
    "Give a one-paragraph product teaser.",
    "Explain recursion to a 10-year-old.",
    "Tell a one-paragraph folk tale."
]

@torch.inference_mode()
def generate(prompt):
    msgs = [{"role": "user", "content": prompt}]
    inputs = tok.apply_chat_template(
        msgs, add_generation_prompt=True, return_tensors="pt"
    ).to(device)

    out = model.generate(
        inputs,
        max_new_tokens=96,
        do_sample=True,
        temperature=0.8,
        top_p=0.95,
        repetition_penalty=1.1,
        pad_token_id=tok.pad_token_id,
        eos_token_id=tok.eos_token_id
    )
    return tok.batch_decode(out, skip_special_tokens=True)[0]

for i, p in enumerate(prompts, 1):
    print(f"\n=== Sample {i} ===\n{generate(p)}\n")
