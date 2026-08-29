#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 graph.json 生成「书籍知识图谱」自包含 HTML（力导向知识图谱）。

设计原则（v25.48l 终审，所有 RC 修复已固化进 assets/galaxy-template.html）：
  - 背景克制：径向渐变（中心浅、四周深），绝不加中间黑洞/星云/光晕/四角羽化
  - 节点清亮：大类实色填充 + 细白描边 + 柔和 drop-shadow，不灰头巴脸、不虚边
  - 居中三件套（RC131）：viewBox = 0 0 W H（不带偏移）；initialT = d3.zoomIdentity（不平移！
    元素级平移会把整图推到右下角造成左半空白）；forceCenter(W/2,H/2).strength(0.45)
  - 密度四件套（v25.48l）：初始位置 W*0.42 / H*0.65（刷新即散开，不挤一团）；charge -240；
    link 距离 book-book 160 / book-concept 85 / concept-concept 55，strength 0.45；
    collide radius(d)+12 / 0.7
  - 交互红线：搜索只显示书名+作者（RC120）；右上角关系图例整行隐藏只留连线（RC124）；
    只有双击背景才 fitContent（RC125）；点空白只取消高亮不复位镜头（不蹦回）
  - 卡片：book 节点 click 打开对应知识卡片 HTML（由 CARD_MAP 注入）

【关键架构】本脚本不再内嵌 HTML 模板字符串，而是读取 assets/galaxy-template.html（UI 外壳，
含全部 RC 修复），仅把 graph.json 与卡片映射注入占位符。这样「脚本 = 产物」唯一真值，
重跑脚本不会丢失任何手调优化（v25.27 旧版内嵌模板曾因脱节导致偏右/挤一团回退）。

用法：
    python3 scripts/gen_spatial.py                # 默认 ~/WorkBuddy/books/graph.json → 同名 html
    python3 scripts/gen_spatial.py G.json OUT.html  # 指定输入/输出（开源 example 用）
依赖：assets/galaxy-template.html + assets/d3.v7.min.js（与输出 html 同目录的 ./assets/ 下）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
TEMPLATE_PATH = os.path.join(SKILL_DIR, "assets", "galaxy-template.html")

BOOKS_DIR = os.path.expanduser("~/WorkBuddy/books")
GRAPH_PATH = os.path.join(BOOKS_DIR, "graph.json")
OUT_PATH = os.path.join(BOOKS_DIR, "书籍知识图谱.html")


def _strip_title_marks(s):
    # 剥书名号（含中间出现的），不改变其余书名内容
    return s.replace("《", "").replace("》", "")


# 保守清洗：只剥「版本/装帧/丛书」标记，绝不切真实书名（含冒号后的书名部分必须保留）
# 覆盖阿拉伯数字 + 中文数字（第2版 / 第二版 / 第7版 / 原书第3版 等）
_NUM = r"[一二三四五六七八九十百0-9]+"
_VERSION_MARKERS = re.compile(
    # —— 带括号的「第N版 / 第N册 / 第N辑」系列（中文+阿拉伯数字）——
    r"（第?" + _NUM + r"版）|（第?" + _NUM + r"册）|（第?" + _NUM + r"辑）|"
    r"（原书第?" + _NUM + r"版）|（第?" + _NUM + r"版，注疏点评版）|"
    # —— 具体册数/套装/全集 ——
    r"（全" + _NUM + r"册）|（共" + _NUM + r"册）|（套装全两册）|（套装共" + _NUM + r"册）|"
    r"（套装上下册）|（全两册）|（全三册）|（全四册）|（全九册）|（上下册）|（全集）|"
    r"（套装）|（共8册）|"
    # —— 命名版本/装帧/丛书标记 ——
    r"（修订版）|（重印版）|（新版）|（再版）|（全本）|（完整版）|（典藏版）|（珍藏版）|"
    r"（果麦经典）|（2024年版）|（2019年版）|（经典版）|（全新增补版）|（重印）|"
    r"（注疏点评版）|（网格本）|（人文社外国文学名著经典）|（经典重译版）|"
    r"（插图修订版）|（图文精编版）|（人民文学版）|（翻译版）|（终极版）|（精装版）|"
    r"（白金版）|（尊享版）|（珍藏纪念版）|（纪念版）|（普及版）|（权威版）|"
    r"（导读版）|（精华版）|（彩图版）|（插图版）|（插图珍藏版）|（全新版）|"
    r"（原版）|（增订版）|（增补版）|（升级版）|（彩色版）|（平装版）|"
    # —— 无括号写法（防漏网）——
    r"修订版|修订本|重印版|重印本|再版|新版|普及版|珍藏版|典藏版|全本|完整版|"
    r"权威版|导读版|精华版|精装版|平装版|彩色版|彩图版|插图版|插图珍藏版|全新版|"
    r"原版|纪念版|增订版|增补版|升级版|全新增补版|经典版|果麦经典|网格本|注疏点评版"
)


def clean_book_label(s):
    """保守清洗：仅剥版本/装帧/丛书标记，保留完整书名（含冒号后的真实书名）。"""
    if not s:
        return s
    s = s.strip()
    s = _strip_title_marks(s)
    s = _VERSION_MARKERS.sub("", s).strip()
    # 兜底：剥掉版本标记后残留的孤立括号（如「思考，快与慢（第二版」→「思考，快与慢」）
    s = re.sub(r"[（）()]", "", s).strip()
    # 去掉开头多余冒号 / 折叠内部多余空白
    s = re.sub(r"^[:：]\s*", "", s).strip()
    s = re.sub(r"\s+", "", s)
    return s


def build_card_map(graph, books_dir):
    """为每个 book 节点自动找到真实存在的知识卡片 HTML 文件路径（相对 books_dir）。"""
    candidates = []
    for root, _dirs, files in os.walk(books_dir):
        for fname in files:
            if "知识卡片" in fname and fname.endswith(".html"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, books_dir).replace(os.sep, "/")
                dir_name = os.path.basename(root)
                candidates.append((rel, dir_name, fname))

    book_map = {}
    for n in graph.get("nodes", []):
        if n.get("type") != "book" or n.get("status") == "referenced":
            continue
        label = _strip_title_marks(n.get("label", ""))
        if not label:
            continue
        matches = [c for c in candidates if _strip_title_marks(c[1]) == label]
        if not matches:
            continue
        best = None
        perfect = label + "-知识卡片.html"
        for rel, _dir_name, fname in matches:
            if fname == perfect:
                best = rel
                break
            if fname.startswith(label + "-知识卡片"):
                best = rel
        if not best:
            best = matches[0][0]
        book_map[n["id"]] = best
    return book_map


def main():
    graph_path = sys.argv[1] if len(sys.argv) > 1 else GRAPH_PATH
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT_PATH

    if not os.path.exists(TEMPLATE_PATH):
        raise SystemExit(f"找不到 UI 模板 {TEMPLATE_PATH}，请确认 skill 完整（assets/galaxy-template.html）")
    if not os.path.exists(graph_path):
        raise SystemExit(f"找不到 {graph_path}，请先按 book-knowledge-graph 规范生成 graph.json")

    with open(graph_path, encoding="utf-8") as f:
        g = json.load(f)

    # v25.25 标签清洗：book 节点 label 剥副标题；原值备份到 raw_label（写回 disk 同步）
    cleaned = 0
    for n in g.get("nodes", []):
        if n.get("type") != "book":
            continue
        old = n.get("label", "")
        new = clean_book_label(old)
        if new != old:
            n["raw_label"] = old
            n["label"] = new
            cleaned += 1
    if cleaned and graph_path == GRAPH_PATH:
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=1)

    # 卡片映射：用输出 html 所在目录作为 books_dir 根（默认即 ~/WorkBuddy/books）
    books_dir = os.path.dirname(out_path)
    card_map = build_card_map(g, books_dir)

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        tpl = f.read()
    assert "/*EMBEDDED_GRAPH_DATA*/" in tpl, "模板缺少 graph 占位符"
    assert "/*CARD_MAP*/" in tpl, "模板缺少 cardmap 占位符"
    html = tpl.replace("/*EMBEDDED_GRAPH_DATA*/", json.dumps(g, ensure_ascii=False))
    html = html.replace("/*CARD_MAP*/", json.dumps(card_map, ensure_ascii=False))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 自包含：把 d3.v7.min.js 复制到输出 html 同级的 ./assets/ 下（开源场景也能直接双击打开）
    out_assets_dir = os.path.join(os.path.dirname(out_path), "assets")
    src_d3 = os.path.join(SKILL_DIR, "assets", "d3.v7.min.js")
    if os.path.exists(src_d3):
        os.makedirs(out_assets_dir, exist_ok=True)
        dst_d3 = os.path.join(out_assets_dir, "d3.v7.min.js")
        if not os.path.exists(dst_d3) or os.path.getsize(src_d3) != os.path.getsize(dst_d3):
            import shutil
            shutil.copyfile(src_d3, dst_d3)

    n_book = sum(1 for n in g.get("nodes", []) if n.get("type") == "book")
    n_link = len(g.get("links", []))
    print(f"✅ 空间感版已生成：{out_path}")
    print(f"   书节点 {n_book} 个，连线 {n_link} 条")
    print(f"   卡片路径映射 {len(card_map)} 个")
    print(f"   标签清洗 {cleaned} 本书（→raw_label 备份，已持久化）")


if __name__ == "__main__":
    main()
