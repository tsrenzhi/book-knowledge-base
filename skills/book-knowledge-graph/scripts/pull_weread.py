#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从微信读书书架拉全量书籍，剔除纯职业/应试书，按 15 大类映射，
合并进现有的「书籍核心要点清单.md」（ 单一结构，不另起独立区块）。

⚠️ 隐私：本脚本需要 `WEREAD_KEY`（微信读书开放 API 的 Bearer Token）。
   严禁把 Key 写进仓库/提交 git；只通过环境变量传入。

用法：
    export WEREAD_KEY=xxx
    python3 scripts/pull_weread.py              # 默认 books/ 路径
    python3 scripts/pull_weread.py OUT.md       # 指定输出 md
"""
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

def _norm(t):
    """统一书名（去《》/空格/标点），用于跨数据源对齐"""
    return re.sub(r'[《》\s·…\.\-_:：()（）·!/／]', '', t or "")

# ============ 可配置：硬剔除职业书分类（按微信读书原生 category） ============
HARD_DROP_SHELF = {
    "漫画-经典改编", "漫画-科普漫画", "漫画-治愈漫画",
    "计算机-编程设计", "计算机-数据库", "计算机-软件学习",
    "计算机-图像视频", "计算机-理论知识",
    "教育学习-考试", "教育学习-外语", "教育学习-教材",
    "生活百科-游戏", "生活百科-美食", "生活百科-体育", "生活百科-情感",
    "艺术-设计", "艺术-绘画",
}

# v25.51 黑名单：只删「具体平台/职业作手册」，不删「营销/商业底层」
# 依据 干啥都需要），营销管理/跨越鸿沟/疯传/上瘾
# 这类讲原理的底层书必须保留；但「抖音/小红书/跨境电商/电商数据」的具体方法=废书，删。
# 删除范畴：
# ① 具体平台运营（抖音/快手/小红书/视频号/公众号的运营/涨粉/爆款/带货/实）
# ② 电商与具体平台作（淘宝/天猫/京东/拼多多/Shopee/跨境电商/亚马逊 + 电商产品/运营/后台）
# ③ 互联网职业务实（产品经理/增长黑客/用户增长/数据分析/数据中台/UI设计/交互设计/SEO/SEM…）
# ④ 技术栈/应试/工具（微服务/DevOps/考研/四六级/Excel/PPT/简历面试…）
# ⑤ 具体公司管理法（腾讯方法/重新定义公司/重新定义团队/赋能敏捷团队）
HARD_DROP_KEYWORDS = re.compile(
    r"^半小时漫画"
    r"|^(语文|数学|英语|物理|化学|生物|历史|地理|政治)\s*[下初高中].*教材"
    r"|^(高考|中考|考研|公务员|教师资格证|托福|雅思|GRE|四级|六级).*"
    # ① 具体平台运营
    r"|抖音.*?(运营|涨粉|爆款|吸金|带货|实|玩法)"
    r"|快手.*?(运营|涨粉|爆款|玩法)"
    r"|小红书.*?(运营|涨粉|爆款|玩法)"
    r"|视频号.*?(运营|涨粉|爆款|玩法)"
    r"|公众号.*?(运营|涨粉|涨粉)"
    r"|128招玩转抖音|玩转抖音|抖音.*?实战"
    r"|人设.*?流量与成交|私域流量池|私域流量.*?密码"
    # ② 电商与具体平台作
    r"|淘宝|天猫|京东|拼多多|Shopee|跨境电商|亚马逊运营|亚马逊.*?爆款"
    r"|电商产品经理|电商后台|电商运营设计|谁说菜鸟不会电商"
    r"|营在设计：电商.*?手册"
    # ③ 互联网职业务实
    r"|产品经理|增长黑客|用户增长方法论"
    r"|数据分析思维|数据中台|数据化.*?运营|数据化最佳实践"
    r"|产品设计|交互设计|UI\s*设计|UX设计"
    r"|SEO|SEM|信息流|广告投放"
    r"|敏捷开发|Scrum|PMP"
    r"|微服务|高并发|架构设计|DevOps|精通\s*\w{0,8}(React|Vue|Angular|Java|Python|算法|SQL|MySQL|架构|Docker|Kubernetes|Git)"
    r"|深入\s*\w{0,8}(分布式|JVM|React|算法|架构|设计模式)"
    r"|匹配度.*?(产品|用户需求)"
    # ④ 应试/工具
    r"|Excel\s*|PPT\s*|PowerPoint|Keynote|Office\s*三?合一"
    r"|简历|面试技巧|跳槽|加薪|晋升"
    # ⑤ 具体公司管理法
    r"|腾讯方法|重新定义公司|赋能.*?敏捷团队"
    r"|华与华|超级符号"
)


CATS_15 = [
    "经济与商业", "人性洞察", "思维认知", "哲学思辨", "财富认知", "底层规律", "能力提升",
    "人际关系与沟通", "文学经典", "习惯养成", "名人传记", "成事方法", "历史", "决策避坑", "心理成长",
]

# ============ 关键词召回规则（v3 实战沉淀） ============
KEY_REMAP = {
    "人性洞察": ["影响力", "乌合之众", "狂热分子", "怪诞行为学", "冲动", "说服", "纵", "人心", "从众", "人性的弱点"],
    "决策避坑": ["黑天鹅", "反脆弱", "灰犀牛", "塔勒布", "稀缺", "助推", "噪声", "快思慢想", "卡尼曼", "损失厌恶",
                  "幸存者", "避坑", "陷阱", "风险与", "失控", "盲点", "沉没成本", "心智陷阱", "认知偏误"],
    "能力提升": ["会读", "高效读", "谈判", "口才", "演讲", "辩论", "说服力", "写作", "刻意练习", "记忆术",
                  "自学", "番茄工作法", "GTD", "搞定", "时间管理", "做事的", "清单", "任务管理", "效率", "专注力",
                  "执行力", "深度工作", "即兴", "复盘", "如何学习"],
    "习惯养成": ["原子习惯", "掌控习惯", "习惯的力量", "福格", "微习惯", "坚持", "睡眠", "自律", "日更", "早起"],
    "财富认知": ["富爸爸", "穷爸爸", "纳瓦尔", "穷查理", "巴菲特", "芒格", "投资", "财务自由", "理财",
                  "指数基金", "价值投资", "买房", "房产", "股票", "基金", "比特币", "区块链", "经济学", "货币", "金融"],
    "成事方法": ["OKR", "项目管理", "管理", "领导力", "高效能", "工作", "职场", "执行", "经理", "领导",
                  "团队", "组织行为", "绩效", "授权", "精要主义", "要事第一", "关键对话"],
    "人际关系与沟通": ["人际", "情商", "非暴力沟通", "公开讲话", "即兴演讲"],
}


def shelf_map(sc, title):
    """微信读书原生 category → 15 大类"""
    if sc == "个人成长-认知思维": return "思维认知"
    if sc == "个人成长-人生哲学": return "思维认知"
    if sc == "个人成长-沟通表达": return "人际关系与沟通"
    if sc == "个人成长-人在职场": return "成事方法"
    if sc == "个人成长-励志成长": return "习惯养成"
    if sc == "个人成长-女性成长": return "思维认知"
    if sc == "个人成长-情绪心灵": return "心理成长"
    if sc.startswith("心理-"): return "心理成长"
    if sc.startswith("哲学宗教-"):
        if "思维" in sc or "逻辑" in sc: return "思维认知"
        return "哲学思辨"
    if sc.startswith("经济理财-财经"): return "经济与商业"
    if sc.startswith("经济理财-商业"): return "经济与商业"
    if sc.startswith("经济理财-管理"): return "成事方法"
    if sc.startswith("经济理财-理财"): return "财富认知"
    if sc.startswith("文学"): return "文学经典"
    if sc.startswith("精品小说"): return "文学经典"
    if sc.startswith("人物传记"): return "名人传记"
    if sc.startswith("历史"): return "历史"
    if sc.startswith("政治军事"): return "底层规律"
    if sc.startswith("社会文化-"): return "底层规律"
    if sc.startswith("科学技术-"):
        if any(k in title for k in ["思维", "心智", "认知", "复杂", "系统", "模型"]): return "思维认知"
        return "底层规律"
    if sc.startswith("医学健康-"): return "心理成长"
    if sc.startswith("教育学习-"):
        if "育儿" in sc: return None
        return "思维认知"
    if sc.startswith("艺术-"):
        if "理论" in sc: return "文学经典"
        return None
    if sc.startswith("计算机-人工智能"): return "思维认知"
    if sc == "":
        if any(k in title for k in ["乔布斯", "马斯克", "贝佐斯", "任正非", "稻盛", "曾国藩", "查理"]):
            return "名人传记"
        return "思维认知"
    return None


def upgrade(title, cur):
    """关键词召回：把易错分的 6 类从泛类里拽出来"""
    for cat, keys in KEY_REMAP.items():
        for k in keys:
            if k in title:
                return cat
    return cur


def fetch_shelf(key):
    req = urllib.request.Request(
        "https://i.weread.qq.com/api/agent/gateway",
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        data=json.dumps({"api_name": "/shelf/sync", "skill_version": "1.0.4"}).encode(),
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    key = os.environ.get("WEREAD_KEY")
    if not key:
        raise SystemExit("❌ 未设置环境变量 WEREAD_KEY。微信读书开放 API 的 Bearer Token，请勿入库。")

    books_dir = os.environ.get("BOOKS_DIR", os.path.join(os.getcwd(), "books"))
    core_json = os.path.join(books_dir, "书籍核心要点.json")
    md_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(books_dir, "书籍核心要点清单.md")

    print("→ 拉取微信读书书架...")
    shelf = fetch_shelf(key)
    books = shelf.get("books", [])
    print(f"   拉取到 {len(books)} 本")

    # 已有书（核心要点 json 已经收录 + 已经建过卡的目录，两者都不是"补充本"该列的）
    existing = set()
    if os.path.exists(core_json):
        with open(core_json, encoding="utf-8") as f:
            core = json.load(f)
            existing = set(core.keys())
            existing_norm = {_norm(k) for k in existing}
    else:
        existing_norm = set()

    # 已建卡（= cards/ 下已有 <书名>-知识卡片.html）
    archived_norm = set()
    bd = Path(books_dir)
    if bd.is_dir():
        for d in bd.iterdir():
            if not d.is_dir() or d.name in ("assets",): continue
            if d.name.startswith(".") or re.match(r'^\d{4}-\d{2}', d.name): continue
            if any(d.glob("*.md")):
                archived_norm.add(_norm(d.name))
                for md in d.glob("*.md"):
                    archived_norm.add(_norm(md.stem))
    print(f"   核心要点已收录 {len(existing)} 本；已建卡 {len(archived_norm)} 个书名")

    # 分类 + 剔除
    missing = []
    dropped = []
    seen = set()
    for b in books:
        t = b.get("title", "").strip()
        if not t or t in existing or t in seen:
            continue
        seen.add(t)
        sc = b.get("category", "")
        a = b.get("author", "").strip()
        fin = b.get("finishReading", 0) == 1
        item = {
            "title": t, "author": a, "shelfCat": sc, "finished": fin,
            "bookId": b.get("bookId", ""),
        }
        nt = _norm(t)
        if nt in existing_norm or nt in archived_norm:
            dropped.append({**item, "reason": "已在核心/建过卡"})
            continue
        if sc in HARD_DROP_SHELF:
            dropped.append({**item, "reason": f"shelfCat={sc}"})
            continue
        if HARD_DROP_KEYWORDS.search(t):
            dropped.append({**item, "reason": f"keyword match"})
            continue
        c = shelf_map(sc, t)
        if c is None:
            dropped.append({**item, "reason": "shelf map=None"})
            continue
        c = upgrade(t, c)
        missing.append({**item, "category": c})

    # 按类分组
    by_cat = defaultdict(list)
    for it in missing:
        by_cat[it["category"]].append(it)

    # 合并进现有 md（ 单一结构：找到每个 `## 【分类】（N本）` 章节，append 补充本）
    if not os.path.exists(md_path):
        print(f"⚠️ 找不到 {md_path}，先用 build_md.py 生成基底")
        sys.exit(1)

    with open(md_path, encoding="utf-8") as f:
        text = f.read()

    # 在每个分类章节尾部追加 书架补充 本（无关键词、仅标补充标记）
    insert_count_by_cat = {}
    for cat in CATS_15:
        items = sorted(by_cat.get(cat, []), key=lambda x: (not x["finished"], x["title"]))
        if not items:
            continue
        marker = f"## 【{cat}】"
        # 找下一个 ## 【...】（下一个分类）或文件尾
        idx = text.find(marker)
        if idx < 0:
            continue
        nxt = text.find("\n## 【", idx + 1)
        if nxt < 0:
            nxt = len(text)
        # 在 nxt 前插入
        block = ""
        for it in items:
            fin_mark = "已读" if it["finished"] else "未读"
            a = it["author"] or "—"
            shelf = it["shelfCat"] or "—"
            block += f"### {it['title']}\n- 作者：{a}（书架补充·{fin_mark}·shelf={shelf}）\n\n"
        text = text[:nxt] + block + text[nxt:]
        insert_count_by_cat[cat] = len(items)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ 微信读书补充已合并进 {md_path}")
    print(f"   本次新增 {len(missing)} 本（剔除 {len(dropped)} 本纯职业书）")
    for c in CATS_15:
        n = insert_count_by_cat.get(c, 0)
        if n:
            print(f"   · {c}：+{n}")


if __name__ == "__main__":
    main()