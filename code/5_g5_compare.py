#!/usr/bin/env python3
"""G5: confronto tra giudice (gpt-5) e due valutatori LLM su 60 righe cieche.
Uso: python3 5_g5_compare.py ../g5/g5_sample_key.json ../g5/labels_grok.txt ../g5/labels_chatgpt.csv"""
import re, json, sys, collections
key = json.load(open(sys.argv[1]))
load = lambda p: {int(a): (int(b), int(c)) for a, b, c in re.findall(r"(\d+),([01]),([01])", open(p).read())}
G, C = load(sys.argv[2]), load(sys.argv[3])
J = {i: (key[str(i)]["Y"], key[str(i)]["leak"]) for i in range(1, 61)}
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n; pa = sum(a) / n; pb = sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))
forms = {"all": lambda a: True, "directive(D1,D2)": lambda a: a in ("D1", "D2"), "descriptive(S1,S2)": lambda a: a in ("S1", "S2"), "soft": lambda a: a == "SOFT"}
for ix, lab in ((0, "RESTRICTION"), (1, "FACT REPORTED")):
    print("==", lab, "(agreement, kappa)")
    for pn, A, B in (("ChatGPT-judge", C, J), ("Grok-judge", G, J), ("ChatGPT-Grok", C, G)):
        s = f"{pn:15}"
        for fn, sel in forms.items():
            ids = [i for i in range(1, 61) if sel(key[str(i)]["arm"])]
            po, k = kappa([A[i][ix] for i in ids], [B[i][ix] for i in ids]); s += f" | {fn} n={len(ids)}: {po:.2f} (k={k:.2f})"
        print(s)
print("== mean by form: restriction | fact")
for fn, sel in forms.items():
    ids = [i for i in range(1, 61) if sel(key[str(i)]["arm"])]
    m = lambda D, ix: sum(D[i][ix] for i in ids) / len(ids)
    print(f"{fn:20} Y judge={m(J,0):.2f} grok={m(G,0):.2f} chatgpt={m(C,0):.2f} | fact judge={m(J,1):.2f} grok={m(G,1):.2f} chatgpt={m(C,1):.2f}")
