#!/usr/bin/env python3
import os, time, json, atexit, shutil, tempfile, subprocess, itertools, threading, queue, requests
from concurrent.futures import ThreadPoolExecutor

class OllamaReplica:
    def __init__(self, model, port, models_dir=None):
        self.model = model
        self.port = int(port)
        self.models_dir = models_dir or tempfile.mkdtemp(prefix=f"ollama_models_{self.port}_")
        self.proc = None
        self.base = f"http://127.0.0.1:{self.port}"
        self._start()

    def _start(self):
        env = os.environ.copy()
        env["OLLAMA_PORT"] = str(self.port)
        env["OLLAMA_MODELS"] = self.models_dir
        # Launch daemon
        self.proc = subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait for server
        for _ in range(100):
            try:
                requests.get(self.base, timeout=0.25)
                break
            except Exception:
                time.sleep(0.05)
        # Pull + warm (keeps model resident)
        requests.post(f"{self.base}/api/pull", json={"name": self.model}, timeout=120)
        requests.post(f"{self.base}/api/generate",
                      json={"model": self.model, "prompt": "warmup", "keep_alive": "24h"},
                      timeout=120)

    def chat(self, messages, **kwargs):
        payload = {"model": self.model, "messages": messages, "stream": False, "keep_alive": "24h"}
        payload.update(kwargs)
        r = requests.post(f"{self.base}/api/chat", json=payload, timeout=600)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def stop(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        finally:
            shutil.rmtree(self.models_dir, ignore_errors=True)


class OllamaPool:
    def __init__(self, model: str, replicas: int = 4, base_port: int = 11500):
        self.replicas = [OllamaReplica(model, base_port + i) for i in range(replicas)]
        self._rr = itertools.cycle(self.replicas)
        self._lock = threading.Lock()
        atexit.register(self.close)

    def submit(self, messages, **kwargs):
        # Round-robin selection
        with self._lock:
            r = next(self._rr)
        try:
            return r.chat(messages, **kwargs)
        except Exception:
            # simple failover: try the next replica once
            with self._lock:
                r2 = next(self._rr)
            return r2.chat(messages, **kwargs)

    def map(self, list_of_messages, max_workers=None, **kwargs):
        results = [None] * len(list_of_messages)
        def work(ix_msgs):
            i, msgs = ix_msgs
            results[i] = self.submit(msgs, **kwargs)
        with ThreadPoolExecutor(max_workers=max_workers or len(self.replicas)) as ex:
            ex.map(work, enumerate(list_of_messages))
        return results

    def close(self):
        for r in self.replicas:
            r.stop()


MODEL_NAME = "phi4-mini:latest"
if __name__ == "__main__":
    # Example: 4 persistent Qwen workers
    pool = OllamaPool(model=MODEL_NAME, replicas=4, base_port=11500)

    # Single request
    out = pool.submit([{"role": "user", "content": "Say hi from your port."}])
    print(out)

    # Batch
    prompts = [[{"role": "user", "content": f"Worker test {i}"}] for i in range(8)]
    for resp in pool.map(prompts):
        print(resp)

    pool.close()
