# -*- coding: utf-8 -*-
"""重生成书籍知识图谱 书籍知识图谱模板.html

工作流：
  1. 读 data/分类总览.md 作为唯一数据真值
  2. 以当前 书籍知识图谱模板.html 为 baseline，提取内嵌的 _EMBEDDED_GRAPH
  3. 按 分类总览 过滤 / 增删 / 改书名；补回丢失的书↔书连线
  4. 写回 书籍知识图谱模板.html

用法：
  python3 scripts/rebuild_final.py             # 干跑：只打印统计
  python3 scripts/rebuild_final.py --write     # 落盘：写回 书籍知识图谱模板.html

路径默认相对仓库根目录（脚本在 scripts/ 下），clone 到任何位置都能跑。
"""
import json, re, sys, hashlib
import os

# ---- 路径：相对仓库根 ----
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO_ROOT, "书籍知识图谱模板.html")
CATALOG = os.path.join(REPO_ROOT, "data", "分类总览.md")
OUT = HTML  # 写回当前 书籍知识图谱模板.html

def imp(uc):
    return 2 if uc <= 1 else 3 if uc <= 2 else 4 if uc == 3 else 5

# ---- parse 分类总览 ----
cat_pat = re.compile(r'^###\s+\d+\.\s*【(.+?)】')
book_pat = re.compile(r'^(\d+)\.\s*《(.+?)》\s*作者[:：](.*?)\s*关键词[:：](.*?)\s*豆瓣评分[:：](\S+)\s*$')
catalog = {}   # title -> (author, category, [concepts])
cur = None
with open(CATALOG, encoding="utf-8") as f:
    for line in f:
        s = line.rstrip("\n")
        m = cat_pat.match(s)
        if m: cur = m.group(1); continue
        bm = book_pat.match(s)
        if bm:
            t = bm.group(2).strip()
            cons = [c.strip() for c in bm.group(4).split("、") if c.strip()]
            catalog[t] = (bm.group(3).strip(), cur, cons)
CATALOG_TITLES = set(catalog.keys())
print(f"[分类总览] {len(CATALOG_TITLES)} 本书待对齐")

# ---- extract embedded ----
html = open(HTML, encoding="utf-8").read()
key = "const _EMBEDDED_GRAPH = "
i = html.find(key); assert i != -1
j = html.index("{", i)
depth = 0; k = j
while k < len(html):
    c = html[k]
    if c == '{': depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            je = k + 1
            break
    k += 1
else:
    raise ValueError("no close brace")
emb = html[j:je]
G = json.loads(emb)
print(f"[embedded] 原 nodes={len(G['nodes'])} links={len(G['links'])}")

nodes = G["nodes"]; links = G["links"]
book_nodes = [n for n in nodes if n.get("type") == "book"]
kept_book_ids = {n["id"] for n in book_nodes if n.get("label") in CATALOG_TITLES}
kept_labels = {n.get("label") for n in book_nodes if n["id"] in kept_book_ids}
missing = [t for t in CATALOG_TITLES if t not in kept_labels]
print(f"[对齐] 命中 {len(kept_book_ids)} 本；分类总览 缺失于图：{missing}")

# ---- filter concept nodes + book nodes ----
kept_concept_ids = set()
filtered_nodes = []
for n in nodes:
    if n.get("type") == "book":
        if n["id"] in kept_book_ids:
            filtered_nodes.append(n)
    elif n.get("type") == "concept":
        bs = [b for b in n.get("books", []) if b in kept_book_ids]
        if bs:
            n2 = dict(n); n2["books"] = bs; n2["use_count"] = len(bs)
            n2["importance"] = imp(n2["use_count"])
            filtered_nodes.append(n2); kept_concept_ids.add(n["id"])
    else:
        filtered_nodes.append(n)

# ---- add missing 分类总览 books (merge concepts) ----
def hid(s): return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]
def short_name(t):
    """去副标取短名，用于「同名不同版」识别。"""
    for sep in ['：', '——', '——', '—']:
        if sep in t: return t.split(sep)[0].strip()
    return t.strip()

# 先扫一遍被丢弃的书（label 不在 CATALOG_TITLES），后续给 missing book 继承书↔书连线
dropped_books = [n for n in nodes if n.get("type")=="book" and n.get("label") not in CATALOG_TITLES]
print(f"[丢弃] {len(dropped_books)} 本（label 与 分类总览 不一致或被删除的书）")

new_nodes = []
new_links = []
new_bid_map = {}   # 分类总览 title -> 新 bid
for title in missing:
    author, cat, cons = catalog[title]
    bid = "b_" + hid(title)
    new_bid_map[title] = bid
    filtered_nodes.append({"id": bid, "type": "book", "label": title,
                           "title_full": title, "author": author,
                           "category": cat, "group": cat, "status": "done"})
    kept_book_ids.add(bid)
    for c in cons:
        # try merge into existing same-label+cat concept
        merged = None
        matched_n = None
        for n in nodes:
            if n.get("type") == "concept" and n.get("label") == c and n.get("category") == cat:
                if bid not in n.get("books", []):
                    n.setdefault("books", []).append(bid)
                merged = n["id"]
                matched_n = n
                break
        if merged:
            cid = merged
            if cid not in kept_concept_ids:   # 该概念原被丢弃(其他书都删了)，合并后必须补回节点
                n2 = dict(matched_n); n2["books"] = [b for b in matched_n.get("books", []) if b in kept_book_ids]
                n2["use_count"] = len(n2["books"]); n2["importance"] = imp(n2["use_count"])
                filtered_nodes.append(n2); kept_concept_ids.add(cid)
        else:
            cid = "c_" + hid(title + c)
            new_nodes.append({"id": cid, "type": "concept", "label": c,
                              "books": [bid], "use_count": 1, "category": cat,
                              "group": cat, "importance": 2})
            kept_concept_ids.add(cid)
        new_links.append({"source": bid, "target": cid, "relation": "包含", "concept": c})

# ---- 改名继承：missing book（如「第19版」）继承被丢弃的老书（如「第18版」）的书↔书连线 ----
# 这是开源用户改副标/版本号不丢脸的核心兜底
inherited_count = 0
inherited_pairs = set()
for t in missing:
    t_short = short_name(t)
    candidate = None
    for db in dropped_books:
        if short_name(db.get("label","")) == t_short and (db.get("category") or "").strip() == (catalog[t][1] or "").strip():
            candidate = db; break
    if not candidate: continue
    old_bid = candidate["id"]; new_bid = new_bid_map[t]
    for l in links:
        if l.get("relation") == "包含": continue
        s, tgt = l.get("source"), l.get("target")
        if s == old_bid and tgt in kept_book_ids and tgt != new_bid:
            l2 = dict(l); l2["source"] = new_bid
            key = (l2["source"], l2["target"], l2.get("relation"))
            if key not in inherited_pairs:
                new_links.append(l2); inherited_pairs.add(key); inherited_count += 1
        elif tgt == old_bid and s in kept_book_ids and s != new_bid:
            l2 = dict(l); l2["target"] = new_bid
            key = (l2["source"], l2["target"], l2.get("relation"))
            if key not in inherited_pairs:
                new_links.append(l2); inherited_pairs.add(key); inherited_count += 1
if inherited_count:
    print(f"[继承] missing books 从同名老书继承 {inherited_count} 条书↔书连线（改名副标不丢脸兜底）")

filtered_nodes.extend(new_nodes)

# ---- filter links ----
filtered_links = []
for l in links:
    s, t = l.get("source"), l.get("target")
    if l.get("relation") == "包含":
        if s in kept_book_ids and t in kept_concept_ids:
            filtered_links.append(l)
    else:
        if s in kept_book_ids and t in kept_book_ids:
            filtered_links.append(l)
filtered_links.extend(new_links)

# ---- reassemble ----
G2 = dict(G)
G2["nodes"] = filtered_nodes
G2["links"] = filtered_links
G2["meta"] = dict(G["meta"])
G2["meta"]["node_count"] = len(filtered_nodes)
G2["meta"]["link_count"] = len(filtered_links)
G2["meta"]["book_count"] = len([n for n in filtered_nodes if n["type"] == "book"])
G2["meta"]["concept_count"] = len([n for n in filtered_nodes if n["type"] == "concept"])
G2["meta"]["gen_time"] = f"基于 分类总览.md ({len(CATALOG_TITLES)} 本)"

# ---- validate ----
nids = {n["id"] for n in filtered_nodes}
bad = [l for l in filtered_links if l["source"] not in nids or l["target"] not in nids]
nb = G2["meta"]["book_count"]
print(f"[产出] nodes={len(filtered_nodes)} books={nb} concepts={G2['meta']['concept_count']} links={len(filtered_links)}")
print(f"[校验] 悬空连线={len(bad)} ；书数应=分类总览({len(CATALOG_TITLES)}) -> {'OK' if nb==len(CATALOG_TITLES) else 'MISMATCH'}")
empty_con = [n['id'] for n in filtered_nodes if n.get('type')=='concept' and not n.get('books')]
print(f"[校验] 空概念节点={len(empty_con)}")

if "--write" in sys.argv:
    new_json = json.dumps(G2, ensure_ascii=False, separators=(",", ":"))
    html2 = html[:j] + new_json + html[je:]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html2)
    print(f"\n[写出] {OUT}  ({len(html2)} bytes)")
else:
    print("\n(干跑模式，未落盘；加 --write 落盘)")
