#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 书单数据源.md 作为唯一真值，干净重建 书籍知识图谱模板.html 的内嵌数据。

核心连线规则（必须配合 ../图谱连线规则说明.md 阅读）：
  1. 只生成两类边：
     - 包含：书 → 概念
     - 相关：同分类且没有共享概念的书 ↔ 书（兜底防孤岛，每本书最多 1 条）
  2. 不生成「相似/强相似」边。共享概念的书只通过 concept 节点间接连接。
  3. 分类、关系类型严禁造词，词表见 ../图谱连线规则说明.md §二、§三。

用法：
  python3 scripts/rebuild_clean.py             # 干跑，打印统计
  python3 scripts/rebuild_clean.py --write     # 写回 HTML
"""
import json
import re
import hashlib
import os
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO_ROOT, "书籍知识图谱模板.html")
CATALOG = os.path.join(REPO_ROOT, "书单数据源.md")

CAT_PAT = re.compile(r'^###\s+\d+\.\s*【(.+?)】')
BOOK_PAT = re.compile(
    r'^(\d+)\.\s*《(.+?)》\s*作者[:：](.*?)\s*关键词[:：](.*?)\s*豆瓣评分[:：](\S+)'
    r'(?:\s*一句话介绍[:：].*)?\s*$'
)


def hid(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]


def importance(use_count: int) -> int:
    return 2 if use_count <= 1 else 3 if use_count <= 2 else 4 if use_count == 3 else 5


def parse_catalog(path: str):
    """返回 [(title, author, category, keywords, rating)]"""
    catalog = []
    cur_cat = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            m = CAT_PAT.match(s)
            if m:
                cur_cat = m.group(1).strip()
                continue
            bm = BOOK_PAT.match(s)
            if bm:
                title = bm.group(2).strip()
                author = bm.group(3).strip()
                keywords = [c.strip() for c in bm.group(4).split("、") if c.strip()]
                rating = bm.group(5).strip()
                catalog.append((title, author, cur_cat, keywords, rating))
    return catalog


def load_embedded_graph(html_path: str) -> dict:
    html = open(html_path, encoding="utf-8").read()
    key = "const _EMBEDDED_GRAPH = "
    i = html.find(key)
    if i == -1:
        raise ValueError("HTML 中找不到 _EMBEDDED_GRAPH")
    j = html.index("{", i)
    depth = 0
    k = j
    while k < len(html):
        c = html[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                je = k + 1
                break
        k += 1
    else:
        raise ValueError("HTML 中 _EMBEDDED_GRAPH JSON 未闭合")
    return json.loads(html[j:je])


def discover_cards() -> dict:
    """扫描 cards/ 下真实存在的 *-知识卡片.html，返回 {书名: 相对路径}。"""
    cards_dir = os.path.join(REPO_ROOT, "cards")
    mapping = {}
    if not os.path.isdir(cards_dir):
        return mapping
    for root, _, files in os.walk(cards_dir):
        for fn in files:
            if fn.endswith("-知识卡片.html"):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, REPO_ROOT).replace("\\", "/")
                stem = fn.replace("-知识卡片.html", "")
                mapping[stem] = rel
    return mapping


def build_graph(catalog: list, existing: dict = None):
    """仅用书单数据构建干净图谱。existing 仅用于复用书节点坐标（如果可用）。"""
    card_map = discover_cards()

    # ---- book nodes ----
    book_nodes = []
    bid_map = {}
    old_pos = {}
    if existing:
        for n in existing.get("nodes", []):
            if n.get("type") == "book":
                old_pos[n.get("label")] = (n.get("x"), n.get("y"))

    for title, author, cat, _, rating_raw in catalog:
        bid = "b_" + hid(title)
        bid_map[title] = bid
        rating = None
        try:
            rating = float(rating_raw)
        except ValueError:
            pass
        x, y = old_pos.get(title, (None, None))
        node = {
            "id": bid,
            "type": "book",
            "label": title,
            "title_full": title,
            "author": author,
            "category": cat,
            "group": cat,
            "status": "done",
            "rating": rating,
            "has_card": False,
            "card_path": None,
        }
        if title in card_map:
            node["has_card"] = True
            node["card_path"] = card_map[title]
        if x is not None and y is not None:
            node["x"] = x
            node["y"] = y
        book_nodes.append(node)

    # ---- concept nodes：严格来自书单 keywords，按 (label, category) 合并 ----
    concept_bids = defaultdict(set)
    for title, _, cat, keywords, _ in catalog:
        bid = bid_map[title]
        for kw in keywords:
            concept_bids[(kw, cat)].add(bid)

    concept_nodes = []
    cid_map = {}
    for (label, cat), bids in sorted(concept_bids.items()):
        cid = "c_" + hid(label + cat)
        cid_map[(label, cat)] = cid
        bids_list = sorted(list(bids))
        concept_nodes.append({
            "id": cid,
            "type": "concept",
            "label": label,
            "books": bids_list,
            "use_count": len(bids_list),
            "category": cat,
            "group": cat,
            "importance": importance(len(bids_list)),
        })

    # ---- 包含 links ----
    contains_links = []
    for title, _, cat, keywords, _ in catalog:
        bid = bid_map[title]
        for kw in keywords:
            cid = cid_map[(kw, cat)]
            contains_links.append({
                "source": bid,
                "target": cid,
                "relation": "包含",
                "concept": kw,
            })

    # ---- book↔book 边：共享概念的书已通过 concept 节点间接连接，
    # 不再重复画书与书直连。仅在「同分类且没有共享概念」的书之间
    # 保留一条轻量「相关」边，避免孤岛（与原版图谱视觉一致）。
    b2b_links = []
    existing_pairs = set()

    # 预计算：哪些书对已经通过共享 concept 节点间接连接
    already_connected = set()
    for n in concept_nodes:
        bids = sorted(n["books"])
        for i in range(len(bids)):
            for j in range(i + 1, len(bids)):
                already_connected.add(frozenset((bids[i], bids[j])))

    deg = defaultdict(int)
    book_cat = {n["id"]: n["category"] for n in book_nodes}
    cat_books = defaultdict(list)
    for n in book_nodes:
        cat_books[n["category"]].append(n["id"])

    for bid in list(bid_map.values()):
        if deg[bid] > 0:
            continue
        same = [b for b in cat_books.get(book_cat.get(bid), []) if b != bid]
        if not same:
            continue
        # 只兜底「还没通过共享概念连接」的书
        candidates = [b for b in same if frozenset((bid, b)) not in already_connected]
        if not candidates:
            continue
        tgt = next((b for b in candidates if deg[b] > 0), candidates[0])
        pair = frozenset((bid, tgt))
        if pair in existing_pairs:
            continue
        b2b_links.append({
            "source": bid,
            "target": tgt,
            "relation": "相关",
            "shared": [],
            "n": 0,
            "family": None,
            "reason": "同分类兜底(避免孤岛)",
        })
        existing_pairs.add(pair)
        deg[bid] += 1
        deg[tgt] += 1

    links = contains_links + b2b_links
    nodes = book_nodes + concept_nodes

    # ---- meta：对齐模板 JS 对 GRAPH.meta 的读取 ----
    # 取书单实际出现的分类，保持色板一致
    cats_in_use = sorted(set(n["category"] for n in nodes if n.get("category")))
    base_category_colors = {
        "经济与商业": "#FF6B6B",
        "财富认知": "#FFD166",
        "成事方法": "#FF9F45",
        "底层规律": "#4ECDC4",
        "人性洞察": "#EC5D7A",
        "人际关系与沟通": "#FF8FAB",
        "心理成长": "#E879B9",
        "思维认知": "#4D96FF",
        "决策避坑": "#6BCB77",
        "能力提升": "#10A19D",
        "习惯养成": "#C5E063",
        "文学经典": "#F5C28B",
        "哲学思辨": "#6F86D6",
        "名人传记": "#B8A6E8",
        "历史": "#C68B59",
    }
    category_colors = {c: base_category_colors.get(c, "#999999") for c in cats_in_use}
    meta = {
        "version": "1.0-lite",
        "description": "开源版 22 本书籍知识图谱",
        "node_types": ["book", "concept", "domain", "author", "category"],
        "relation_types": ["相似", "相悖", "互补", "应用", "引用", "批判", "包含"],
        "color_by_relation": {
            "相似": "#7BC47E",
            "互补": "#5DBDBD",
            "相悖": "#E8483E",
            "包含": "#C9B18A",
            "引用": "#A88BD8",
            "应用": "#F5C84C",
            "批判": "#E8483E",
        },
        "group_colors": category_colors,
        "category_colors": category_colors,
        "categories": cats_in_use,
        "gen_time": f"基于 书单数据源.md ({len(book_nodes)} 本)",
        "node_count": len(nodes),
        "link_count": len(links),
        "book_count": len(book_nodes),
        "concept_count": len(concept_nodes),
    }
    return {"nodes": nodes, "links": links, "meta": meta}


def write_graph(html_path: str, graph: dict):
    html = open(html_path, encoding="utf-8").read()

    # 0) 先算好 CARD_MAP 并注入 graph，再一次性 dumps，避免坐标错位
    card_map = {
        n["id"]: n["card_path"]
        for n in graph.get("nodes", [])
        if n.get("type") == "book" and n.get("has_card") and n.get("card_path")
    }
    graph["CARD_MAP"] = card_map

    # 1) 替换 _EMBEDDED_GRAPH
    key = "const _EMBEDDED_GRAPH = "
    i = html.find(key)
    if i == -1:
        raise ValueError("HTML 中找不到 _EMBEDDED_GRAPH")
    j = html.index("{", i)
    depth = 0
    k = j
    je = None
    while k < len(html):
        c = html[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                je = k + 1
                break
        k += 1
    if je is None:
        raise ValueError("HTML 中 _EMBEDDED_GRAPH JSON 未闭合")
    new_json = json.dumps(graph, ensure_ascii=False, separators=(',', ':'))
    html = html[:j] + new_json + html[je:]

    # 2) 同步 JS 顶层 CARD_MAP 变量
    card_map_js = "const CARD_MAP = {\n" + "\n".join(
        f'"{bid}": "{path}",' for bid, path in sorted(card_map.items())
    ) + "\n};"
    card_map_pat = re.compile(r'const CARD_MAP = \{[^}]*\};', re.S)
    if card_map_pat.search(html):
        html = card_map_pat.sub(card_map_js, html)
    else:
        print("[WARN] HTML 中找不到 CARD_MAP 块，跳过更新")

    open(html_path, "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    catalog = parse_catalog(CATALOG)
    print(f"[书单数据源] {len(catalog)} 本书")

    existing = load_embedded_graph(HTML)
    print(f"[baseline] 原 nodes={len(existing['nodes'])} links={len(existing['links'])}")

    G = build_graph(catalog, existing)
    books = [n for n in G["nodes"] if n["type"] == "book"]
    concepts = [n for n in G["nodes"] if n["type"] == "concept"]
    print(f"[新图谱] books={len(books)} concepts={len(concepts)} links={len(G['links'])}")

    # 自检：不应存在书单里没有的概念
    catalog_concepts = set()
    for _, _, cat, keywords, _ in catalog:
        for kw in keywords:
            catalog_concepts.add((kw, cat))
    bad_concepts = [n for n in concepts if (n["label"], n["category"]) not in catalog_concepts]
    if bad_concepts:
        print(f"[ERROR] 发现 {len(bad_concepts)} 个非书单概念：")
        for n in bad_concepts:
            print(f"  - {n['label']} ({n['category']})")
        sys.exit(1)

    # 自检：分类必须都来自书单
    catalog_cats = set(cat for _, _, cat, _, _ in catalog)
    bad_cats = set(n["category"] for n in concepts) - catalog_cats
    if bad_cats:
        print(f"[ERROR] 发现书单外的分类：{bad_cats}")
        sys.exit(1)

    # 自检：没有真正的孤岛（书↔书直连 或 通过共享 concept 节点连接 都算连接）
    connected_books = set()
    for l in G["links"]:
        if l.get("relation") != "包含":
            connected_books.add(l["source"])
            connected_books.add(l["target"])
    # 通过共享 concept 节点连接的书对
    for n in concepts:
        if len(n.get("books", [])) >= 2:
            connected_books.update(n["books"])
    isolated = [n["label"] for n in books if n["id"] not in connected_books]
    if isolated:
        print(f"[WARN] 以下书籍没有任何关联（无直连、无共享概念）：{isolated}")

    if "--write" in sys.argv:
        write_graph(HTML, G)
        print(f"[已写回] {HTML}")
    else:
        print("[干跑] 加 --write 才落盘")
