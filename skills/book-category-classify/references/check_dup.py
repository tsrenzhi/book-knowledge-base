#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vN-core.json / vN markdown 真重复扫描器 · RC-fix v8 新增

铁律（用户原话："思考，快与慢你怎么能直接截断"）：
- 同 author（去 [美]/[英]/[日] 等前缀后归一比对）
- 两条 title 短者是长者的子串（去《》/空格/全角逗号后）
- abs 长度差 ≤ 5
- 短串长度 ≥ 2
→ 必报「真重复」并提示：保留长名，删除短名

典型场景：
- 《思考，快与慢》（丹尼尔·卡尼曼） vs 《思考》（丹尼尔·卡尼曼） ← v8 真重复，已删
- 《先发影响力》（西奥迪尼） vs 《影响力》（西奥迪尼） ← 系列两本，**非重复**，保留
- 《汉书》（尹小林校注） vs 《后汉书》（尹小林校注） ← 系列两本，**非重复**，保留

用法：
  /Users/zhenghui/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \\
      ~/.workbuddy/skills/book-category-classify/references/check_dup.py \\
      ~/WorkBuddy/books/v8-core.json
"""
import json, re, sys
from collections import defaultdict

def clean_a(s):
    return re.sub(r"^\[[^]]*\]", "", (s or "")).strip()

def norm_title(s):
    s = re.sub(r"[《》\"'`“”‘’]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.replace(",","").replace("，","").replace(" ","").replace("\u3000","").strip()

def scan(path):
    data = json.load(open(path, encoding="utf-8"))
    by_author = defaultdict(list)
    for i, b in enumerate(data):
        a = clean_a(b.get("author",""))
        if a:
            by_author[a].append((i, b.get("title",""), b.get("category",""), norm_title(b.get("title",""))))

    suspects = []
    for a, lst in by_author.items():
        if len(lst) < 2: continue
        seen = set()
        for i in range(len(lst)):
            for j in range(i+1, len(lst)):
                idx1, t1, c1, n1 = lst[i]
                idx2, t2, c2, n2 = lst[j]
                short, long_ = (n1, n2) if len(n1) <= len(n2) else (n2, n1)
                if short and short in long_ and len(short) >= 2 and abs(len(n1)-len(n2)) <= 5:
                    pair = tuple(sorted([idx1, idx2]))
                    if pair not in seen:
                        seen.add(pair)
                        suspects.append((a, idx1, t1, c1, idx2, t2, c2))
    return suspects

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/zhenghui/WorkBuddy/books/v8-core.json"
    sus = scan(path)
    print(f"=== 真重复候选（同 author + title 子串 + 长度差≤5）· {path} ===")
    for s in sus:
        print(f"  作者:{s[0]}")
        print(f"    [{s[1]}] 《{s[2]}》({s[3]})  vs  [{s[4]}] 《{s[5]}》({s[6]})")
    print(f"共 {len(sus)} 对")
    if not sus:
        print("  ✅ 无真重复")
