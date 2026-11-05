#!/usr/bin/env python3
"""Compressione (e giudizio) via API compatibili OpenAI. Stdlib soltanto.
Chiavi da variabili d'ambiente: OPENAI_API_KEY, TOGETHER_API_KEY. Mai scriverle nei file.
  python3 2_run.py compress --provider openai   --model gpt-5-mini --prompts prompts.jsonl --out out_gpt5mini.jsonl --limit 3
  python3 2_run.py compress --provider together --model <nome esatto dal catalogo> ...
  python3 2_run.py --list-together-models
  --mock : nessuna chiamata, output finti (collaudo della pipeline)"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error
ENDPOINTS = {"openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
             "together": ("https://api.together.xyz/v1/chat/completions", "TOGETHER_API_KEY")}
STREAM = False
def call(provider, model, prompt, max_tokens, retries=3, system=None):
    url, env = ENDPOINTS[provider]; key = os.environ.get(env)
    if not key: sys.exit(f"{env} non impostata")
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs}
    if provider == "openai":
        body["max_completion_tokens"] = max_tokens
        if model.startswith("gpt-5"): body["reasoning_effort"] = "minimal"
        else: body["temperature"] = 0.1
    else:
        body["max_tokens"] = max_tokens; body["temperature"] = 0.1
        if STREAM: body["stream"] = True
    last = None
    for a in range(retries + 1):
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "research-script/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                if body.get("stream"):
                    parts, usage = [], {}
                    for raw in r:
                        line = raw.decode("utf-8", "replace").strip()
                        if not line.startswith("data:") or line.endswith("[DONE]"): continue
                        try: ch = json.loads(line[5:].strip())
                        except Exception: continue
                        if ch.get("usage"): usage = ch["usage"]
                        for c in ch.get("choices") or []:
                            d = c.get("delta") or {}
                            if d.get("content"): parts.append(d["content"])
                    return {"choices": [{"message": {"content": "".join(parts)}}], "usage": usage}
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code not in (429, 500, 502, 503, 504): break
        except Exception as e: last = repr(e)
        time.sleep(2 ** a)
    raise RuntimeError(last)
def text_of(resp):
    t = resp["choices"][0]["message"].get("content") or ""
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()
def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", nargs="?", choices=["compress", "judge"])
    p.add_argument("--provider", choices=list(ENDPOINTS)); p.add_argument("--model")
    p.add_argument("--prompts"); p.add_argument("--out"); p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=3000)
    p.add_argument("--mock", action="store_true"); p.add_argument("--list-together-models", action="store_true")
    p.add_argument("--workers", type=int, default=1, help="chiamate in parallelo (es. 8)")
    p.add_argument("--stream", action="store_true", help="necessario per i modelli Together che lo richiedono")
    a = p.parse_args()
    global STREAM; STREAM = a.stream
    if a.list_together_models:
        req = urllib.request.Request("https://api.together.xyz/v1/models", headers={"Authorization": "Bearer " + os.environ["TOGETHER_API_KEY"], "User-Agent": "research-script/1.0"})
        for m in json.loads(urllib.request.urlopen(req).read()):
            if any(k in m["id"].lower() for k in ("qwen3", "deepseek")): print(m["id"])
        return
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(l)["prompt_id"] for l in open(a.out) if l.strip()}
    rows = [json.loads(l) for l in open(a.prompts) if l.strip()]
    rows = [r for r in rows if r["prompt_id"] not in done][: a.limit]
    print(f"{len(rows)} chiamate con {a.model}")
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock(); counter = [0]
    def work(r):
        if a.mock:
            out = "Mock handoff: " + r["sensitive_fact"]; usage = {}
        else:
            try:
                resp = call(a.provider, a.model, r["prompt"], a.max_tokens); out = text_of(resp); usage = resp.get("usage", {})
            except Exception as e:
                print(f"ERRORE {r['prompt_id']}: {str(e)[:200]}", flush=True); return
        with lock:
            f.write(json.dumps({**{k: r[k] for k in ("prompt_id", "scenario_id", "arm", "form", "sensitive_fact")},
                                "model": a.model, "output": out, "usage": usage, "t": int(time.time())}) + "\n"); f.flush()
            counter[0] += 1
            print(f"[{counter[0]}/{len(rows)}] {r['prompt_id']} tok={usage.get('total_tokens','?')}", flush=True)
    with open(a.out, "a") as f:
        with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex: list(ex.map(work, rows))
    print("Finito. Se compaiono righe ERRORE sopra, rilancia lo stesso comando: riprende solo quelle mancanti.")
if __name__ == "__main__": main()
