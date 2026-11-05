#!/usr/bin/env python3
"""Analisi pre-registrata (Fase 2). Delta = media_scenari( Y_direttivo - Y_descrittivo ), D={D1,D2}, S={S1,S2}.
IC 95% = bootstrap per scenario (10000 ripetizioni). Segno per modello riportato a parte.
  python3 4_analyze.py judged_*.jsonl"""
import json, sys, random, collections
random.seed(20261104)
def load(paths):
    return [json.loads(l) for p in paths for l in open(p) if l.strip()]
def deltas(rows, model):
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if r["model"] == model and r["Y"] is not None: by[r["scenario_id"]][r["form"]].append(r["Y"])
    out = {}
    for sc, d in by.items():
        if d.get("directive") and d.get("descriptive"):
            out[sc] = sum(d["directive"]) / len(d["directive"]) - sum(d["descriptive"]) / len(d["descriptive"])
    return out
def boot(v, B=10000):
    v = list(v); n = len(v); m = sorted(sum(random.choice(v) for _ in range(n)) / n for _ in range(B))
    return m[int(.025 * B)], m[int(.975 * B)]
rows = load(sys.argv[1:]); models = sorted({r["model"] for r in rows}); res = {}
print("modello | n scenari | Delta | IC95% | Y_D | Y_S | Y_soft | leak_D | leak_S")
for m in models:
    dl = deltas(rows, m); mean = sum(dl.values()) / len(dl); lo, hi = boot(dl.values()); res[m] = (mean, lo, hi)
    g = lambda f, k: (lambda x: sum(x) / len(x) if x else float("nan"))([r[k] for r in rows if r["model"] == m and r["form"] == f and r[k] is not None])
    print(f"{m} | {len(dl)} | {mean:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {g('directive','Y'):.2f} | {g('descriptive','Y'):.2f} | {g('soft','Y'):.2f} | {g('directive','leak'):.2f} | {g('descriptive','leak'):.2f}")
signs = sum(1 for m in res if res[m][0] > 0); passed = sum(1 for m in res if res[m][0] >= .15 and res[m][1] > 0)
print(f"\nSegno positivo in {signs}/{len(res)} modelli; modelli con Delta>=0.15 e IC>0: {passed}/{len(res)}")
print("PASSA" if passed >= 2 and signs >= 2 else ("FALLISCE (limite sup < 0.10 in tutti)" if all(res[m][2] < .10 for m in res) else "INCONCLUSIVO"))
