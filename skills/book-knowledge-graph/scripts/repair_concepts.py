#!/usr/bin/env python3
# sync_graph --repair-concepts：把 72 个 category 不一致的 concept 节点按所属 book 修正
import json, re, argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repair-concepts", action="store_true")
ap.add_argument("--graph", default="/Users/zhenghui/WorkBuddy/books/graph.json")
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

p = Path(args.graph)
g = json.load(open(p, encoding="utf-8"))

book_cat = {b["id"]: b.get("category") for b in g["nodes"] if b.get("type")=="book"}

fixed = 0
for n in g["nodes"]:
    if n.get("type") != "concept": continue
    bid = n.get("book") or (n.get("books") or [None])[0]
    if not bid: continue
    bc = book_cat.get(bid)
    if bc and n.get("category") != bc:
        fixed += 1
        if not args.dry_run:
            n["category"] = bc

print(f"修复 {fixed} 个 concept 节点 category → 继承所属 book")
if not args.dry_run and fixed:
    json.dump(g, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"已写入 {p}")
else:
    print("(dry-run, 未写入)")