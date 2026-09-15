#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从用户改完的「书籍核心要点清单.md」回灌到 graph.json。

读取 md 解析出每个书的：
  - title（书名）
  - author
  - category
  - 是否带关键词（带 = 已收核心；标书架补充且无关键词 = 忽略/标 referenced）

作 graph.json：
  - 已存在的 book 节点：category 改了 → 更新；raw_label 保留原值
  - md 里有但 graph.json 没有的「带关键词」book：新建为 done（需要 user 提供基础字段）
  - md 里标「书架补充」且无关键词的：跳过（不污染 graph.json，只在 md 里待筛）

⚠️ 「带关键词的补充书」新建节点需要 fields（id/type/label/author/year/category/concepts[]）。
   本脚本只在用户改完 md、给图谱补新书时跑；新建节点逻辑由调用方补全或人工介入。
   本脚本的主战场是「已有书 category 修正」+「交叉验证」。

用法：
    python3 scripts/sync_graph.py [--dry-run] [MD] [graph.json]
    默认 books/书籍核心要点清单.md → books/graph.json
"""
import json
import os
import re
import sys

CATS_15 = [
    "经济与商业", "人性洞察", "思维认知", "哲学思辨", "财富认知", "底层规律", "能力提升",
    "人际关系与沟通", "文学经典", "习惯养成", "名人传记", "成事方法", "历史", "决策避坑", "心理成长",
]

# 解析 md 行
HEADING_RE = re.compile(r"^## 【(.+?)】")           # 分类标题
BOOK_RE = re.compile(r"^### (.+?)$")                 # 书名小标题
CONCEPT_LINE_RE = re.compile(r"^- 关键词：(.+)$")     # 关键词行（带 backtick 词）
AUTHOR_LINE_RE = re.compile(r"^- 作者：(.+?)（书架补充")  # 书架补充行

CONCEPT_TOKEN_RE = re.compile(r"`([^`]+)`")


def parse_md(path):
    """返回 (by_title: dict{title→{category, has_concepts, author, is_supplement}})"""
    by_title = {}
    cur_cat = None
    cur_title = None
    with open(path, encoding="utf-8") as f:
        for raw in f.read().splitlines():
            line = raw.rstrip()
            m = HEADING_RE.match(line)
            if m:
                cur_cat = m.group(1).strip()
                cur_title = None
                continue
            m = BOOK_RE.match(line)
            if m:
                cur_title = m.group(1).strip()
                if cur_cat:
                    by_title[cur_title] = {
                        "category": cur_cat,
                        "has_concepts": False,
                        "author": "",
                        "is_supplement": False,
                    }
                continue
            if cur_title is None:
                continue
            info = by_title[cur_title]
            m = CONCEPT_LINE_RE.match(line)
            if m:
                tokens = CONCEPT_TOKEN_RE.findall(m.group(1))
                # 过滤掉 ⚠️ 占位
                tokens = [t for t in tokens if "⚠" not in t and "未匹配" not in t]
                if tokens:
                    info["has_concepts"] = True
                    info["concepts"] = tokens
                continue
            m = AUTHOR_LINE_RE.match(line)
            if m:
                info["author"] = m.group(1).strip()
                info["is_supplement"] = True
                continue
    return by_title


def main():
    dry_run = "--dry-run" in sys.argv
    from_graph = "--from-graph" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    books_dir = os.environ.get("BOOKS_DIR", os.path.join(os.getcwd(), "books"))
    md_path = args[0] if len(args) > 0 else os.path.join(books_dir, "书籍核心要点清单.md")
    g_path = args[1] if len(args) > 1 else os.path.join(books_dir, "graph.json")
    core_path = os.path.join(books_dir, "书籍核心要点.json")

    if not os.path.exists(md_path):
        raise SystemExit(f"找不到 {md_path}")
    if not os.path.exists(g_path):
        raise SystemExit(f"找不到 {g_path}")

    md = parse_md(md_path)
    with open(g_path, encoding="utf-8") as f:
        g = json.load(f)

    # 标题 → 节点映射（label 可能有《》符号，先剥）
    def norm(s):
        return s.lstrip("《").rstrip("》").strip()

    node_by_title = {}
    for n in g.get("nodes", []):
        if n.get("type") == "book":
            node_by_title[norm(n.get("label", ""))] = n

    changes = 0
    meta_cats = set(g.get("meta", {}).get("categories", []))
    new_cats = 0

    if from_graph:
        # === 反向同步：graph.json → core.json（修复历史遗留的 stale category）===
        print("↔️  --from-graph：从 graph.json 反向同步到 core.json")
        if not os.path.exists(core_path):
            raise SystemExit(f"找不到 {core_path}")
        with open(core_path, encoding="utf-8") as f:
            core = json.load(f)
        core_changes = 0
        for bid, info in core.items():
            t = info.get("title", "").strip()
            nt = norm(t)
            if nt in node_by_title:
                gc = node_by_title[nt].get("category")
                cc = info.get("category")
                if gc and gc != cc:
                    if not dry_run:
                        info["category"] = gc
                    core_changes += 1
        if not dry_run:
            with open(core_path, "w", encoding="utf-8") as f:
                json.dump(core, f, ensure_ascii=False, indent=1)
        print(f"{'🔍 [dry-run] ' if dry_run else '✅'} 反向同步完成：core.json 修正 {core_changes} 本书的 category")
        # 同时把 md 里的对应分类章节标记为变更，让用户后续重生成（避免误改）
        return

    for title, info in md.items():
        nt = norm(title)
        if nt in node_by_title:
            n = node_by_title[nt]
            old_cat = n.get("category")
            new_cat = info["category"]
            if old_cat != new_cat:
                if not dry_run:
                    n["category"] = new_cat
                    if "group" in n:
                        n["group"] = new_cat
                changes += 1
                if new_cat not in meta_cats:
                    meta_cats.add(new_cat)
                    new_cats += 1
        else:
            # md 里有但 graph.json 没有的（仅做报告，不自动新建节点）
            print(f"   [新书] {title} → {info['category']}（md 有但 graph.json 无，需手动加节点）")

    if not dry_run:
        g["meta"]["categories"] = list(meta_cats)
        with open(g_path, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=1)

    print(f"{'🔍 [dry-run] ' if dry_run else '✅'} 同步完成")
    print(f"   解析 md：{len(md)} 本书")
    print(f"   graph.json 命中：{sum(1 for nt in [norm(t) for t in md] if nt in node_by_title)} 本")
    print(f"   category 变更：{changes} 本")
    print(f"   meta.categories 新增：{new_cats} 类")
    print(f"\n💡 反向同步（graph.json → core.json）：python3 scripts/sync_graph.py --from-graph")


if __name__ == "__main__":
    main()