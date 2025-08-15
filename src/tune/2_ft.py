import os, gc, random, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
torch.backends.cuda.matmul.allow_tf32 = True

device = "cuda"
MODEL = "microsoft/Phi-3-mini-4k-instruct"
SAVE_DIR = "./phi3_full_ft_fp16"

tok = AutoTokenizer.from_pretrained(MODEL)

# Load once on CPU, clone fresh fp16 model, then move to GPU (avoid two GPU copies)
base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map=None)
model = AutoModelForCausalLM.from_config(base.config).to(dtype=torch.float16)
model.load_state_dict(base.state_dict(), strict=True)
del base; gc.collect(); torch.cuda.empty_cache()

model = model.to(device)
model.gradient_checkpointing_enable()
model.config.use_cache = False
model.train()

# 8-bit Adam to keep optimizer memory low
import bitsandbytes as bnb
opt = bnb.optim.Adam8bit(model.parameters(), lr=5e-5)

vocab = ["banana", "dragonfruit", "apple", "kiwi"]
max_len = 64

for step in range(70):
    text = " ".join(random.choices(vocab, k=32))
    batch = tok([text], return_tensors="pt", truncation=True, max_length=max_len)
    batch = {k: v.to(device, non_blocking=True) for k, v in batch.items()}

    opt.zero_grad(set_to_none=True)
    out = model(**batch, labels=batch["input_ids"])
    loss = out.loss
    loss.backward()
    opt.step()
    
    print(f"step {step} loss {loss.item():.4f}")

# ---- save for later inference ----
model.gradient_checkpointing_disable()
model.config.use_cache = True
model.eval()
os.makedirs(SAVE_DIR, exist_ok=True)
model.save_pretrained(SAVE_DIR, safe_serialization=True)
tok.save_pretrained(SAVE_DIR)
print(f"Saved to {SAVE_DIR}")

# ---- test: 10 generations using the saved model ----
del model; gc.collect(); torch.cuda.empty_cache()
model = AutoModelForCausalLM.from_pretrained(SAVE_DIR, torch_dtype=torch.float16).to(device)
tok = AutoTokenizer.from_pretrained(SAVE_DIR)
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

with torch.no_grad():
    for i, p in enumerate(prompts, 1):
        # Phi-3 expects chat template; wrap as a single-user message
        msgs = [{"role": "user", "content": p}]
        inputs = tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt"
        ).to(device)

        gen = model.generate(
            inputs,
            max_new_tokens=96,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
            repetition_penalty=1.1,
            pad_token_id=tok.eos_token_id
        )
        text = tok.batch_decode(gen, skip_special_tokens=True)[0]
        print(f"\n=== Sample {i} ===\n{text}\n")

print("Done.")
