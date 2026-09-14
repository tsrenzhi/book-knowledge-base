# -*- coding: utf-8 -*-
# ⚠️ 废弃警告：本脚本已废弃，请勿使用。
# 它会继承旧 baseline 的 concepts / 书↔书边，导致旧 142 本概念污染新图谱（2026-09-13 已踩坑）。
# 重生成图谱一律改用 scripts/rebuild_clean.py（从书单数据源干净重建，不继承任何旧概念）。
"""重生成书籍知识图谱 书籍知识图谱模板.html

工作流：
  1. 读 书单数据源.md 作为唯一数据真值
  2. 以当前 书籍知识图谱模板.html 为 baseline，提取内嵌的 _EMBEDDED_GRAPH
  3. 按 书单数据源 过滤 / 增删 / 改书名；补回丢失的书↔书连线
  4. 写回 书籍知识图谱模板.html

用法：
  python3 scripts/rebuild_final.py             # 干跑：只打印统计
  python3 scripts/rebuild_final.py --write     # 落盘：写回 书籍知识图谱模板.html

路径默认相对仓库根目录（脚本在 scripts/ 下），clone 到任何位置都能跑。
"""
import json, re, sys, hashlib
import os
from collections import defaultdict

# ---- 路径：相对仓库根 ----
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO_ROOT, "书籍知识图谱模板.html")
CATALOG = os.path.join(REPO_ROOT, "书单数据源.md")
OUT = HTML  # 写回当前 书籍知识图谱模板.html

def imp(uc):
    return 2 if uc <= 1 else 3 if uc <= 2 else 4 if uc == 3 else 5

# ---- parse 书单数据源 ----
cat_pat = re.compile(r'^###\s+\d+\.\s*【(.+?)】')
# 兼容"一句话介绍"字段（v1.1.0 数据源新增）；旧数据源没有该字段时也照常匹配
book_pat = re.compile(r'^(\d+)\.\s*《(.+?)》\s*作者[:：](.*?)\s*关键词[:：](.*?)\s*豆瓣评分[:：](\S+)(?:\s*一句话介绍[:：].*)?\s*$')
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
print(f"[书单数据源] {len(CATALOG_TITLES)} 本书待对齐")

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
print(f"[对齐] 命中 {len(kept_book_ids)} 本；书单数据源 缺失于图：{missing}")

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

# ---- add missing 书单数据源 books (merge concepts) ----
def hid(s): return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]
def short_name(t):
    """去副标取短名，用于「同名不同版」识别。"""
    for sep in ['：', '——', '——', '—']:
        if sep in t: return t.split(sep)[0].strip()
    return t.strip()

# 先扫一遍被丢弃的书（label 不在 CATALOG_TITLES），后续给 missing book 继承书↔书连线
dropped_books = [n for n in nodes if n.get("type")=="book" and n.get("label") not in CATALOG_TITLES]
print(f"[丢弃] {len(dropped_books)} 本（label 与 书单数据源 不一致或被删除的书）")

new_nodes = []
new_links = []
new_bid_map = {}   # 书单数据源 title -> 新 bid
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

# ---- (v1.4.0) 书单关键词回填 concept：让「改书单关键词」真能触发书↔书建边 ----
# 旧逻辑只继承 baseline 的 concept.books，书单关键词改动不生效（孤立书永远孤立）。
# 这里用书单 catalog 的 keywords，把每本「图里已有的书」加进对应 concept 的 books
# （同 label 合并；缺失则新建 concept），使「改书单关键词 = 自然建立共词关联」成立。
_concept_by_label = {}
for n in filtered_nodes:
    if n.get("type") == "concept":
        _concept_by_label.setdefault(n["label"], n)
for title in catalog:
    if title not in kept_labels:
        continue  # missing 书已在前面建过 concept
    bid = next((n["id"] for n in filtered_nodes
                if n.get("type") == "book" and n.get("label") == title), None)
    if not bid:
        continue
    _, cat, cons = catalog[title]
    for c in cons:
        if c in _concept_by_label:
            cn = _concept_by_label[c]
            if bid not in cn.get("books", []):
                cn.setdefault("books", []).append(bid)
                cn["use_count"] = len(cn["books"])
                cn["importance"] = imp(cn["use_count"])
        else:
            cid = "c_" + hid(title + c)
            cn = {"id": cid, "type": "concept", "label": c,
                  "books": [bid], "use_count": 1, "category": cat,
                  "group": cat, "importance": 2}
            filtered_nodes.append(cn)
            _concept_by_label[c] = cn
            kept_concept_ids.add(cid)

# ---- 主动建立书↔书关联（v1.2.0 新增）----
# 旧逻辑只继承 baseline 的书↔书边：删书后大量书变成孤岛。
# 这里按「共有关键词」重建 相似/强相似 边，再用「同分类」兜底，
# 保证 142 本里的每一本书至少有一条连线（用户硬要求）。
_book_concepts = {}   # bid -> set(concept labels)
_concept_books = {}   # concept label -> [bid]（仅保留书单内的书）
for n in filtered_nodes:
    if n.get("type") == "concept":
        _concept_books[n["label"]] = [b for b in n.get("books", []) if b in kept_book_ids]
for n in filtered_nodes:
    if n.get("type") == "book":
        _book_concepts[n["id"]] = set()
for n in filtered_nodes:
    if n.get("type") == "concept":
        for b in _concept_books.get(n["label"], []):
            _book_concepts[b].add(n["label"])

# 已存在的书↔书对（仅 new_links 生成的，用于去重）。
# 注意（v1.4.0）：baseline 的「书↔书」边视为过期（旧逻辑可能含 hub 爆边 / 孤岛旧连线），
# 一律不再继承，避免旧边被「削了就变孤岛」的保护锁死、hub 削不下来。
_existing_pairs = set()
for l in new_links:
    if l.get("relation") != "包含" and l.get("source") in kept_book_ids and l.get("target") in kept_book_ids:
        _existing_pairs.add(frozenset((l["source"], l["target"])))

_gen_b2b = 0
for clabel, bids in _concept_books.items():
    if len(bids) < 2:
        continue
    for a in range(len(bids)):
        for b in range(a + 1, len(bids)):
            ba, bb = bids[a], bids[b]
            pair = frozenset((ba, bb))
            if pair in _existing_pairs:
                continue
            shared = sorted(_book_concepts[ba] & _book_concepts[bb])
            n_shared = len(shared)
            rel = "强相似" if n_shared >= 2 else "相似"
            new_links.append({"source": ba, "target": bb, "relation": rel,
                              "shared": shared, "n": n_shared,
                              "family": None, "reason": f"共享概念词={n_shared}"})
            _existing_pairs.add(pair)
            _gen_b2b += 1

# 当前度数（仅统计 new_links 生成的边；baseline 书↔书旧边视为过期，不计入度数）
_deg = {bid: 0 for bid in kept_book_ids}
for l in new_links:
    if l.get("relation") != "包含" and l.get("source") in kept_book_ids and l.get("target") in kept_book_ids:
        _deg[l["source"]] += 1; _deg[l["target"]] += 1

_cat_books = {}
for n in filtered_nodes:
    if n.get("type") == "book":
        _cat_books.setdefault(n.get("category"), []).append(n["id"])

# 同分类串链兜底：同类别书按在图里的顺序排成链，相邻两本建「相关」边。
# 只对「当前为 0 度」的书触发，使其连到相邻书（有度或同为 0 度均可），
# 从而把同分类书串起来、消除孤岛，且不会把多本孤岛全连到同一个 hub 造成爆度。
_cat_order = defaultdict(list)
for n in filtered_nodes:
    if n.get("type") == "book":
        _cat_order[n.get("category")].append(n["id"])

_iso_fixed = 0
for _cat, _chain in _cat_order.items():
    for _a, _b in zip(_chain, _chain[1:]):
        _pair = frozenset((_a, _b))
        if _pair in _existing_pairs:
            # 该对已有共有关键词边：若两端都不为 0 度（边存活）→ 无需串链；
            # 若有一端 0 度 → 说明那条共词边被降度丢弃了，必须补回一条锁定的串链兜底边，避免孤岛
            if _deg[_a] > 0 and _deg[_b] > 0:
                continue
        else:
            # 完全无共词边时，只在有一端为 0 度才串（不强行给已连通的书加冗余边）
            if not (_deg[_a] == 0 or _deg[_b] == 0):
                continue
        _shared = sorted(_book_concepts[_a] & _book_concepts[_b])
        new_links.append({"source": _a, "target": _b, "relation": "相关",
                          "shared": _shared, "n": len(_shared),
                          "family": None, "reason": "同分类串链(避免孤岛)"})
        _existing_pairs.add(_pair)
        _deg[_a] += 1; _deg[_b] += 1
        _iso_fixed += 1

# 全局兜底：仅对同类别都没有、全库彻底孤立的书，连到度数最高的书
_hub = max(kept_book_ids, key=lambda x: _deg[x]) if kept_book_ids else None
for bid in [b for b in kept_book_ids if _deg[b] == 0]:
    if _hub and _hub != bid:
        pair = frozenset((bid, _hub))
        if pair not in _existing_pairs:
            new_links.append({"source": bid, "target": _hub, "relation": "相关",
                              "shared": [], "n": 0,
                              "family": None, "reason": "全局兜底(避免孤岛)"})
            _existing_pairs.add(pair)
            _deg[bid] += 1
            _iso_fixed += 1

_iso_left = sum(1 for b in kept_book_ids if _deg[b] == 0)
print(f"[主动建关联] 共有关键词边={_gen_b2b} 条；同分类/全局兜底={_iso_fixed} 条；孤岛剩余={_iso_left}")

# ---- filter links ----
# v1.4.0：baseline 的「书↔书」边视为过期（可能含旧逻辑生成的 hub 爆边），不再继承；
# 仅保留 baseline 的「包含」边（概念→书的从属关系，仍是真值），
# 所有书↔书边统一由 new_links（共有关键词 + 同分类串链 + 改名继承 + 兜底）重新生成。
filtered_links = []
for l in links:
    s, t = l.get("source"), l.get("target")
    if l.get("relation") == "包含":
        if s in kept_book_ids and t in kept_concept_ids:
            filtered_links.append(l)
    # else: baseline 书↔书旧边不继承，交给 new_links 重新生成（避免旧 hub 爆边残留）
filtered_links.extend(new_links)

# ---- 书↔书边降度：每本书 ≥1 且绝大多数 ≤3（hub 偶尔 ≤4）----
_b2b_all = [l for l in filtered_links if l.get("relation") != "包含"]
_other_links = [l for l in filtered_links if l.get("relation") == "包含"]
_REL_WEIGHT = {"强相似": 3, "相似": 2, "相关": 1}
_CAP = 3
_CAP_TOLERANCE = 3  # 硬 cap：每本严格 ≤3，孤岛可接受
def _score(l):
    return (_REL_WEIGHT.get(l.get("relation", ""), 0),
            l.get("n", 0),
            len(l.get("shared", [])))

_all_book_ids = set(kept_book_ids)
_b2b_all.sort(key=_score, reverse=True)

# Phase 0：先锁定「兜底边（避免孤岛）」，保证每本至少 1 度——孤岛不可接受
_kept_b2b = []
_deg = defaultdict(int)
_locked = [l for l in _b2b_all
           if '避免孤岛' in (l.get('reason') or '') or '兜底' in (l.get('reason') or '')]
for l in _locked:
    _kept_b2b.append(l)
    _deg[l["source"]] += 1; _deg[l["target"]] += 1
# Phase 1：贪心 cap=_CAP_TOLERANCE 在剩余边里尽量连（已锁定的书占用 1 度）
_rest = [l for l in _b2b_all if l not in _kept_b2b]
for l in _rest:
    s, t = l["source"], l["target"]
    if _deg[s] < _CAP_TOLERANCE and _deg[t] < _CAP_TOLERANCE:
        _kept_b2b.append(l)
        _deg[s] += 1; _deg[t] += 1
_dropped = [l for l in _b2b_all if l not in _kept_b2b]

# Phase 2：补 0 度书（只在对方 < _CAP_TOLERANCE 时补，否则接受孤岛）
for _round in range(8):
    _isos = [bid for bid in _all_book_ids if _deg[bid] == 0]
    if not _isos:
        break
    _fixed = 0
    for bid in _isos:
        _cands = [l for l in _dropped
                  if bid in (l["source"], l["target"])
                  and _deg[l["target"] if l["source"] == bid else l["source"]] < _CAP_TOLERANCE]
        if not _cands:
            continue
        _cands.sort(key=_score, reverse=True)
        l = _cands[0]
        s, t = l["source"], l["target"]
        other = s if t == bid else t
        _kept_b2b.append(l)
        _dropped.remove(l)
        _deg[bid] += 1; _deg[other] += 1
        _fixed += 1
    if _fixed == 0:
        break

# Phase 3：cap 到 _CAP + 迭代修复（削后产生新孤岛就补回来）
while True:
    _over = [bid for bid, d in _deg.items() if d > _CAP]
    if not _over:
        break
    _over_set = set(_over)
    # 候选 = 涉及超度数书的所有保留边，按强度升序（先削最弱）
    _cand = [l for l in _kept_b2b if l["source"] in _over_set or l["target"] in _over_set]
    if not _cand:
        break
    _cand.sort(key=_score)
    _removed = False
    for w in _cand:
        s, t = w["source"], w["target"]
        # 削后 s 或 t 是否会变 0 度？会就跳到下一条候选
        if _deg[s] - 1 == 0 or _deg[t] - 1 == 0:
            continue
        _kept_b2b.remove(w)
        _dropped.append(w)
        _deg[s] -= 1; _deg[t] -= 1
        _removed = True
        # 削后立刻补可能产生的新孤岛
        for orphan in (s, t):
            if _deg[orphan] == 0:
                _cands2 = [l for l in _dropped if orphan in (l["source"], l["target"])]
                if _cands2:
                    _cands2.sort(key=_score, reverse=True)
                    l2 = _cands2[0]
                    ss, tt = l2["source"], l2["target"]
                    oo = ss if tt == orphan else tt
                    if _deg[oo] < _CAP_TOLERANCE:  # 允许暂时超 cap
                        _kept_b2b.append(l2)
                        _dropped.remove(l2)
                        _deg[orphan] += 1; _deg[oo] += 1
        break
    if not _removed:
        break  # 所有候选都会造成新孤岛，跳出

_before = len(_b2b_all)
_after = len(_kept_b2b)
_iso_left = sum(1 for b in _all_book_ids if _deg[b] == 0)
_over = sum(1 for d in _deg.values() if d > 3)
_max_d = max(_deg.values()) if _deg else 0
print(f"[降度 cap=3 (hub≤4)] 排序前 {_before} → 保留 {_after}；剩余0度书={_iso_left}；超3度书={_over}；最大度数={_max_d}")

# ---- 最终兜底：消除降度后可能残留的 0 度书 ----
# 成因：某书仅有的共词边，其邻居在降度时优先保了其他更高分边而触顶 cap，
# 导致该书所有边被挤出 → 变孤岛。这里强行把它连到同概念/同分类里度数最低的邻居
# （若该邻居已达 3，则允许临时到 4——只为救孤岛，绝不制造 5+ 的 hub）。
_deg3 = {bid: 0 for bid in _all_book_ids}
for l in _kept_b2b:
    _deg3[l["source"]] += 1; _deg3[l["target"]] += 1
_bid_cat = {n["id"]: n.get("category") for n in filtered_nodes if n.get("type") == "book"}
_final_fixed = 0
for bid in [b for b in _all_book_ids if _deg3[b] == 0]:
    cand = None
    # 1) 同概念邻居中度数最低的（优先 < 3，避免额外制造 hub）
    for c in _book_concepts.get(bid, set()):
        for other in _concept_books.get(c, []):
            if other != bid and _deg3[other] < 3:
                if cand is None or _deg3[other] < _deg3[cand[0]]:
                    cand = (other, c)
    # 2) 同分类链邻居中度数最低的（哪怕到 4，只为救孤岛）
    if cand is None:
        for other in _cat_order.get(_bid_cat.get(bid), []):
            if other != bid and _deg3[other] < 4:
                if cand is None or _deg3[other] < _deg3[cand[0]]:
                    cand = (other, None)
    if cand:
        other = cand[0]
        shared = sorted(_book_concepts.get(bid, set()) & _book_concepts.get(other, set()))
        _kept_b2b.append({"source": bid, "target": other, "relation": "相关",
                          "shared": shared, "n": len(shared), "family": None,
                          "reason": "最终兜底(避免孤岛)"})
        _deg3[bid] += 1; _deg3[other] += 1
        _final_fixed += 1
if _final_fixed:
    print(f"[最终兜底] 救回 {_final_fixed} 本残留孤岛")

filtered_links = _other_links + _kept_b2b

# ---- reassemble ----
G2 = dict(G)
G2["nodes"] = filtered_nodes
G2["links"] = filtered_links
G2["meta"] = dict(G["meta"])
G2["meta"]["node_count"] = len(filtered_nodes)
G2["meta"]["link_count"] = len(filtered_links)
G2["meta"]["book_count"] = len([n for n in filtered_nodes if n["type"] == "book"])
G2["meta"]["concept_count"] = len([n for n in filtered_nodes if n["type"] == "concept"])
G2["meta"]["gen_time"] = f"基于 书单数据源.md ({len(CATALOG_TITLES)} 本)"

# ---- validate ----
nids = {n["id"] for n in filtered_nodes}
bad = [l for l in filtered_links if l["source"] not in nids or l["target"] not in nids]
nb = G2["meta"]["book_count"]
print(f"[产出] nodes={len(filtered_nodes)} books={nb} concepts={G2['meta']['concept_count']} links={len(filtered_links)}")
print(f"[校验] 悬空连线={len(bad)} ；书数应=书单数据源({len(CATALOG_TITLES)}) -> {'OK' if nb==len(CATALOG_TITLES) else 'MISMATCH'}")
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
