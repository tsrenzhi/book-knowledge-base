#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 书籍核心要点.json 渲染成 15 类清单 md，供人工审核/编辑。

设计目标：单一结构（）——「带关键词 = 已收核心」「标书架补充且无关键词 = 待筛补充」，
所有书在同一份 md 里按 15 类分区排列，便于上下通览、不用翻对比。

输入：{book_id: {title, category, points: [...]}} 的 json dict
输出：<out>.md（默认 `书籍核心要点清单.md`），含可填补充本区块

用法：
    python3 scripts/build_md.py                        # 默认 books/ 路径
    python3 scripts/build_md.py books.json out.md       # 指定输入/输出
"""
import json
import os
import sys
from collections import defaultdict, OrderedDict

CATS_15 = [
    "经济与商业", "人性洞察", "思维认知", "哲学思辨", "财富认知", "底层规律", "能力提升",
    "人际关系与沟通", "文学经典", "习惯养成", "名人传记", "成事方法", "历史", "决策避坑", "心理成长",
]


def main():
    args_clean = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    books_dir = os.environ.get("BOOKS_DIR", os.path.join(os.getcwd(), "books"))
    in_path = args_clean[0] if len(args_clean) >= 1 else os.path.join(books_dir, "书籍核心要点.json")
    out_path = args_clean[1] if len(args_clean) >= 2 else os.path.join(books_dir, "书籍核心要点清单.md")

    # 保护已有 md：只在用户显式 --force 时覆盖；默认报错退出，避免误删书架补充本
    if os.path.exists(out_path) and not force:
        raise SystemExit(f"❌ {out_path} 已存在（通常含书架补充本）。覆盖会丢失补充内容。\n"
                          "   强制重建：python3 scripts/build_md.py --force")

    if not os.path.exists(in_path):
        raise SystemExit(f"找不到 {in_path}")

    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    # 分类
    by_cat = defaultdict(list)
    for bid, info in data.items():
        cat = info.get("category", "未分类")
        by_cat[cat].append((bid, info))

    # 未匹配要点
    missing_pts = [info for _, info in by_cat.get("未分类", [])] if "未分类" in by_cat else []

    # 写入
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 书籍核心要点清单\n\n")
        f.write("> 共 15 个一级分类，按分类→书名→要点词（≤8字）逐条列出。\n")
        f.write("> ⚠️ **发现问题直接编辑本文件**，改完用 `python3 scripts/sync_graph.py` 回灌到 graph.json + 重跑 `gen_spatial.py` 出图。\n\n")
        f.write("---\n\n")
        for cat in CATS_15:
            items = sorted(by_cat.get(cat, []), key=lambda x: x[1].get("title", ""))
            f.write(f"## 【{cat}】（{len(items)} 本）\n")
            for bid, info in items:
                f.write(f"### {info.get('title', bid)}\n")
                pts = info.get("points") or []
                if pts:
                    quoted = "、".join(f"`{p}`" for p in pts)
                    f.write(f"- 关键词：{quoted}\n")
                else:
                    f.write(f"- 关键词：`⚠️ **未匹配要点**（请补）`\n")
                    f.write(f"  - ⚠️ graph label: `{info.get('title', bid)}` / id: `{bid}`\n")
                f.write("\n")
            f.write("\n")
        # 未分类的兜底
        if missing_pts:
            f.write(f"\n## 【未分类】（{len(missing_pts)} 本 · 需手动归类）\n")
            for info in missing_pts:
                f.write(f"### {info.get('title', '?')}\n")
                f.write(f"- 关键词：`⚠️ **未分类**（请指定 category）`\n\n")

    n_book = sum(len(v) for v in by_cat.values())
    print(f"✅ 清单已生成：{out_path}")
    print(f"   共 {n_book} 本 · {len(by_cat)} 个分类")
    print(f"   缺关键词：{sum(1 for items in by_cat.values() for _, i in items if not i.get('points'))}")


if __name__ == "__main__":
    main()