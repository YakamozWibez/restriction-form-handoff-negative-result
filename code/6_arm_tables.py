#!/usr/bin/env python3
"""Tabella per braccio e modello. Uso: python3 6_arm_tables.py ../data/judged_rows_no_text.jsonl"""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print("model | arm | restriction_stated | fact_reported | safe(no fact OR restriction) | silent_omission(no restriction, no fact)")
for m in sorted({r["model"] for r in rows}):
    for a in ["D1", "D2", "SOFT", "S1", "S2"]:
        x = [r for r in rows if r["model"] == m and r["arm"] == a]; n = len(x)
        print(f"{m} | {a} | {sum(r['Y'] for r in x)/n:.2f} | {sum(r['leak'] for r in x)/n:.2f} | {sum(1 for r in x if r['leak']==0 or r['Y']==1)/n:.2f} | {sum(1 for r in x if r['Y']==0 and r['leak']==0)/n:.2f}")
