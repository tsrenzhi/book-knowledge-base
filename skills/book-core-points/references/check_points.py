#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-core-points 全量自检器
读 书籍核心要点.json（默认）或 书籍核心要点清单.md（--md），按 SKILL.md 的 11 类错误
（含 RC109 品牌/人名、RC110 书名字面/比喻）+ 判别标准逐条扫描，
输出违反清单（书名 / 违例句 / 命中规则 / 置信度）。

usage: python3 check_points.py [--md] [--fix]
  --md  : 直接扫描 书籍核心要点清单.md（人读层），而非 json 真值
  --fix : 仅删除高置信纯黑名单项（薄词/泛动词/外部标签/万金油/术语装内行/品牌人名/书名比喻），
          具体改写交付人工，避免误伤好样例。（仅 json 模式支持写回）

设计原则：宁可漏报不可误报。金标准书（已梳理知识卡片 13 本 + 用户验收 9 本）
直接跳过，不当作违规。
"""
import json, re, sys

D = 'data/书籍核心要点.json'
OUT = 'data/书籍核心要点.json'

# ---------- 金标准书（13卡片 + 9用户验收），跳过不查 ----------
GOLD = {
    '国富论','纳瓦尔宝典','富爸爸穷爸爸','影响力','人类简史','孙子兵法','这就是人性',
    '小岛经济学','金钱心理学','通往奴役之路','进化心理学','经济学的思维方式','列奥纳多·达·芬奇传',
    '六项精进','创新者的窘境','贫穷的本质','上瘾','黑天鹅','2049','世界观','乌合之众','要钱还是要生活',
    # 书名=核心 coined 概念，合法（不再误报）
    '刻意练习','反脆弱','心流','批判性思维','权衡','洞见','钱商','噪声',
}

# ---------- 高置信黑名单（几乎无争议的必杀）----------
THIN_NOUN = {'自卑感','生活风格','社会兴趣','创造性自我','自我状态','临在','臣服',
             '痛苦之身','观察者','意义疗法','本质','精神','思维','概念','状态'}
LONE_VERB = {'临在','臣服','觉察','接纳','直面','跳出','不认输','不抗拒','活在','觉醒',
             '超越','放下','觉察情绪','跳出思维','不抗拒当下','直面孤独','接纳现实'}
OUTER_LABEL = {'FIRE运动','财务独立','反消费主义','奥地利学派','自由主义','凯恩斯主义',
               '时间比钱贵','去中心化协作',
               '共享高于占有','AI重塑一切','万物皆可追踪','未来30年三大力量','人际伦理','命运认知'}
# 万金油（未来学/通用词，套任一本同主题书都对得上）
VOGUE = {'人机结合时代','不可替代价值','一人公司','时间注意力稀缺'}

# ---------- RC109 品牌/企业/人物名（高置信黑名单，本次翻车核心）----------
# 只列最常见的；人名无穷尽，但以高频 + 本次打回的为准。命中即报，宁可漏不误杀。
BRAND_NAME = {
    '苹果','Apple','PayPal','paypal','麦当劳','英特尔','Intel','乔布斯','巴菲特','芒格',
    '摩根','迪士尼','网飞','奈飞','谷歌','Google','特斯拉','亚马逊','阿里','腾讯','华为',
    '小米','京东','雷·克洛克','克洛克','库克','韦尔奇','郭士纳','马斯克','曾国藩','字节跳动',
    '美团','拼多多','阿里巴巴','脸书','Facebook','微软','IBM','比亚迪','网易',
}
# ---------- RC110 书名字面/比喻/书中意象当唯一概念（本次打回，高置信）----------
BOOK_METAPHOR = {
    '推石上山','蚊子大象隐喻','MEA情绪公式','MEA','销售信','次贷',
}

# ---------- RC306-jargon 专业英文缩写（用户六连击 BATNA 案，2026-08-28 锁定）----------
# 家喻户晓已普及的缩写（GTD/OKR/PK/IQ/EQ）不在此列 → 这些词单独用读者一眼能懂。
# 这里列专业圈/学术界缩写的少数派：大众读者 5 秒内讲不出的 → 必杀，译成中文大白话。
# 注：用户已多次确认 OKR 在《这就是 OKR》《OKR 工作法》等锁区真值中合法单用，
#     不放进黑名单（避免误杀已校对书）。
JARGON = {
    'BATNA','最佳替代方案',     # 谈判圈 Fisher-Ury 派发明缩写（用户原话踩雷）
    'BAN','基准方案',           # BAN（basic acceptable negotiation）
    'ZOPA','可交易空间',        # Zone of Possible Agreement
    'MAUT','多标准权衡',        # Multi-Attribute Utility Theory
    'MECE','互不重叠',          # Mutually Exclusive, Collectively Exhaustive
    'MECE分类','MECE原则',      # MECE 系列说法
    'UPN',                       # Unique Perceived Negotiable
    'LTV','客户终身价值',        # Life-Time Value
    'MVP','最小可行产品',        # Minimum Viable Product
    'NSM','北极星指标',          # North Star Metric
    'KOL','关键意见领袖',
    'UGC','用户生产内容',
    'PGC','专业生产内容',
    'BATNA最佳替代方案',         # 常见组合词
    'GTD',                        # GTD (Get Things Done) 用户2026-08-28原话踩雷「GTD我也看不懂什么意思」 — 但保留作为圈内术语（如 加中文后缀 `GTD工作法` 合法，单用必杀）
    'GTD工作法',                   # 仍加 - 因为首词位置裸用实质还是 GTD
    '5V5',                        # 用户举例踩雷的烂缩写
}

# ---------- RC306-granular 罗列堆砌黑名单（用户六连击 12 种谈判策略案）----------
# 关键词里出现「X种策略/N个法则/五种方法/N个步骤/N个习惯/N个维度/X个要素」类罗列
# = 看完了跟没看一样，必须重组为 2-3 个核心方法名。
# 例外：本身是词典/工具书/合集的书允许列「N 个词条」（如字典的 ~3 万字 = 正常）。
LIST_STUFFING = {
    '12种谈判策略','12种策略','12种方法','12种技巧','12个技巧',
    '5种谈判策略','5种策略','5种倾听技巧','5个步骤','5个法则','5个原则',
    '10种提问框架','10种策略','10个方法','10个原则','10种方法',
    'N种策略','N种方法','N个方法','N个原则','N个法则','N个步骤','N个习惯','N个维度','N个要素',
}

# ---------- 同书近义重复簇（用于 RC103/RC99 内重复）----------
NEAR = [
    ('从众', ['从众','群体无意识','群体平庸','群体盲从','羊群','乌合','随大流']),
    ('复利', ['复利','利滚利','复利的威力','指数增长']),
    ('稀缺', ['稀缺','稀缺心态','稀缺陷阱']),
    ('批判', ['批判性思维','质疑权威','独立思考','认知盲点','学会提问','第一性原理','多元思维']),
    ('社会认同', ['社会认同','社会影响','社会证明']),
    ('锚定', ['锚定','锚定效应']),
    ('损失厌恶', ['损失厌恶','损失规避']),
    ('互惠', ['互惠']),
    ('长期', ['长期主义','长期持有']),
]

# ---------- RC306-fix-ext「读着像没写的纯泛词」（用户二次打回 2026-08-28 修正）----------
# 关键修正：主题大类词（团队管理/认知偏差/习惯养成/领导力/个人成长/心理学/思维认知/
# 经济学…）是【合法第一词】，绝不在黑名单！黑名单只含「过程/动作/结果泛词」——
# 这些词单独作第一词 = "看完了跟没看一样"，永远成不了主题。
# 注意：单字主题缩写（管理/认知/学习/思维/习惯/成长/自律/养成）仍泛，保留在黑名单，
# 逼出双字主题词（团队管理/认知偏差/习惯养成/个人成长）。
# 合法第一词（主题大类，不在黑名单，自检跳过）：团队管理/企业管理/领导力/执行力/
# 沟通力/决策力/认知偏差/习惯养成/个人成长/心理学/思维认知/经济学/经济史/行为经济学/
# 营销学/销售方法/创业/哲学/存在主义/情绪管理/人性/命运/历史/文学/传记…
EMPTY_VAGUE = {
    '能力提升','成功','方法','方法论','成长','改变','突破','提升','打造','构建',
    '升级','进化','创新','创造','塑造','实现','思维','认知','学习','管理',
    '思考','实践','心态','智慧','策略','技巧','工具','原则','心法','习惯','养成',
    '自律','规划','反思','总结','复盘','练习','专注','坚持','积累','机会','优势',
    '资源','效率','效能','杠杆','机遇','法则','定律','要素','步骤','框架','体系',
    '系统','机制','模型','模式','路径','方案','流程','协作','责任','信任','授权','产出',
    '战略',    # 用户2026-08-28原话「什么叫战略呀？是企业战略呀，还是什么战略呀？」 — 必须细分为 竞争战略/营销战略/军事战略/大战略/客户战略 等具体类型才允许用
}


# ---------- 锁定分类（绝对不可改区，用户已手写校验，agent/自检脚本不可动）----------
# RC306-fix-locked：用户亲口「经济与商业 verbatim 保真」（见 RC306/RC306-fix-locked 铁律）。
# 任何自检命中一律降级为「警告」、不进违规报告、不进 --fix 写回，永不动这块。
# 要改这里必须用户显式授权（用户原话「我前面不都有一部分案例都给你写好了吗？还在瞎改什么呀？」）。
LOCKED_CATEGORIES = {'经济与商业'}

def is_locked(v):
    """这本书所属分类是否在锁定区？锁定=绝对不可改。"""
    cat = (v.get('category') or '').strip()
    return cat in LOCKED_CATEGORIES


# 反常识判断关键词（"X是Y" 但 Y 是 骗局/陷阱/谎言/分散/机会 等 → 合法，不误杀）
ANTI_KEY = ('骗局','陷阱','谎言','分散','机会','起点','不是','非','才是','最大','最','真相','本质')  # 末项谨慎

def scan_point(t, p):
    """返回 (命中规则列表, 置信度 high/mid/low)。无命中返回 ([],'')"""
    hits = []
    # R1 描述型 X是Y现象/状态/职业（排除反常识判断）
    if re.search(r'^(.{0,6}是[^不]{0,8}(职业|现象|表现|特征|状态|本质)|.{0,6}是[^不]{2,8})$', p) and len(p) <= 12:
        # 反常识判断豁免
        if not re.search(r'(是(最大|一个)?(骗局|陷阱|谎言)|是分散|是价值交换|就是推销|才是|不是|非)', p):
            hits.append('RC98描述型')
    # R2 抽象类目结尾（排除合法 coined：如"存在先于本质"是萨特概念）
    if re.search(r'(本质|意义|精神|要义|精髓|内涵)$', p) and len(p) <= 8 and p != '存在先于本质':
        hits.append('RC97抽象类目')
    # R3 薄词/泛动词 高置信
    if p in THIN_NOUN or p in LONE_VERB:
        hits.append('RC101/102薄词孤词')
    # R4 外部标签
    if p in OUTER_LABEL:
        hits.append('RC105外部标签')
    # R5 万金油
    if p in VOGUE:
        hits.append('RC106万金油')
    # R6 长描述句（>10字且带叙述虚词，排除反常识判断）
    if len(p) > 10 and re.search(r'[的了被靠在为则需便得与在于]', p):
        if not re.search(r'(是(最大|一个)?(骗局|陷阱|谎言)|才是|不是|非)', p):
            hits.append('RC108长描述句')
    # R7 书名同名堆砌（科学史具体内容，排除合法 coined：可证伪性/相对论怪圈）
    if re.search(r'(亚里士多德逻辑|牛顿|相对论与量子论|科学哲学导论)', p):
        hits.append('RC107书名同名堆砌')
    # R8 章节/书名当概念（point == title，且非金标准 coined 概念）
    if t.strip() == p.strip() and t not in GOLD:
        hits.append('RC100书名当概念')
    # R9 术语装内行
    if p == '黑天鹅' or p == '黑天鹅不可预测':
        hits.append('RC104术语装内行')
    # R10 品牌/企业/人物名（RC109，本次翻车核心）
    if p in BRAND_NAME:
        hits.append('RC109品牌人名')
    # R11 书名字面/比喻当概念（RC110）
    if p in BOOK_METAPHOR:
        hits.append('RC110书名字面比喻')
    # R12 纯泛词主词位（RC306-fix-ext：用户连续打回核心，巨人的工具→习惯养成/名人习惯/刻意练习；
    #   当下的力量→关注当下/精神内耗/活在当下；异类→一万小时定律/机遇优势/文化传承。
    #   "能力提升/成功/方法/成长/管理/认知/学习…"作为主词 = 看完了跟没看一样）
    if p in EMPTY_VAGUE:
        hits.append('RC306-fix纯泛词')
    # R13 专业英文缩写当概念（RC306-jargon：用户六连击 BATNA 案 2026-08-28）
    # 通用规则：[A-Z]{2,6} 全大写字母组、且不在大众词豁免（GTD/OKR/PK/IQ/EQ/SWOT）
    #   → 当点命中即报违规；让点尽量变成大白话。
    if re.fullmatch(r'[A-Z]{2,8}', p or ''):
        # 大众词豁免：GTD 用户2026-08-28原话「GTD我也看不懂」→ 已从豁免名单移除（连同 MECE 也已下沉）— 任何 [A-Z]{2,8} 缩写都触发 R13-jargon；保留极广谱词条做安全垫
        if p not in {'PK','IQ','EQ','SWOT','PEST','Q1','AI','UI','UX','OKR','KPI','SMART','PDCA','MVP','AQI'}:
            hits.append('RC306-jargon英文缩写')
    # R13-ext 缩写复合词：中文字符前/后夹着英文缩写也算（如「MECE分类」「BATNA方案」「LTV价值」）
    if re.search(r'(?<![A-Za-z])([A-Z]{2,8})(?=[一-龥]|[A-Z]?$)', p or ''):
        # 提取缩写群组
        m = re.findall(r'(?<![A-Za-z])([A-Z]{2,8})(?=[一-龥]|[A-Z]?$)', p)
        # 排除合法大众词（GTD 也已移除豁免 → 任何缩写复合词都命中）
        for abbr in m:
            if abbr not in {'PK','IQ','EQ','SWOT','PEST','Q1','AI','UI','UX','OKR','KPI','SMART','PDCA','MVP','AQI'} and abbr not in {'金字塔','法则三'}:
                hits.append('RC306-jargon缩写复合词')
                break
    # R14 罗列堆砌当概念（RC306-granular：用户六连击 12 种谈判策略案 2026-08-28）
    # "X种策略/N个法则/五个方法/N个步骤" 类罗列 + 直接命中 LIST_STUFFING 黑名单 → 必报。
    if p in LIST_STUFFING:
        hits.append('RC306-granular罗列堆砌')
    # R14-ext：广义罗列模式（即使不在黑名单的具体值）—— 检测"N种/N个"结构
    if re.search(r'\d+种|\d+个(法则|方法|技巧|原则|策略|步骤|习惯|维度|要素|框架)|十几种|数十种|N种', p or ''):
        # 例外：本身就是核心方法名（如「5 个步骤」可以接受当作「步骤A/B/C...」，但更推荐拆词）
        # 这里只报"罗列堆砌"型 warning，置信度 mid 让人工判断
        hits.append('RC306-granular罗列堆砌(模式)')
    return hits

# ---------- RC306-flexible v2「核心主题词必须占首词位」检测 ----------
# 用户2026-08-28五连击最终定稿：每本书首词必须是「真正在讲」的核心主题
# （人际沟通书→沟通技巧/人际关系；谈判书→谈判技巧；演讲书→演讲技巧；
# 销售书→销售技巧；写作结构书→结构化表达；影响力书→影响力）。
# 检测：书名里带分类关键词，首词必须落在该分类关键词集合里。
CATEGORY_HEAD = [
    # (书名关键词子串, 合法首词集合)
    # 顺序敏感：写前的组先匹配。让"写作"组在"沟通/对话/谈话"前，
    # 避免写作书副题"人物对话"误命中"沟通"组；让"批判性思维"组在"社交"前。
    (['写作','写作班','写作课','写作力'], {'写作技巧','写作','结构化表达','说服力','批判性思维','叙事学'}),
    (['谈判','谈判力'], {'谈判技巧','谈判','商业谈判','谈判力'}),
    (['演讲','表达','口才','说话','舌战'], {'演讲技巧','演讲','表达技巧','沟通技巧','口才','结构化表达'}),
    (['销售','直销','营销'], {'销售技巧','销售','营销学','营销','市场营销','说服','说服力'}),
    (['演讲的力量','TED'], {'演讲技巧','演讲','沟通技巧'}),
    (['影响力','说服力','说服','行为纵'], {'影响力','说服','说服力','批判性思维','逻辑学'}),
    (['亲密关系','亲密'], {'人际关系','亲密关系'}),
    (['结构化表达','结构化','金字塔原理'], {'结构化表达','逻辑表达','写作技巧'}),
    (['提问','提问力','提问式'], {'提问技巧','提问','沟通技巧','批判性思维'}),
    (['习惯','高效能'], {'习惯养成','习惯','个人成长','个人管理'}),
    (['领导力','领导','管理十诫','赋能','责任病毒','授权','格鲁夫'], {'领导力','团队管理','企业管理','管理','组织管理'}),
    (['社交'], {'沟通技巧','人际关系','社交技巧','沟通','人脉','情商','心理学','心理疗愈'}),
    (['沟通','对话','谈话','沟通力','交流'], {'沟通技巧','沟通','人际沟通','人际关系'}),
    (['冲突'], {'冲突化解','人际关系','沟通技巧','谈判技巧','心理学','国际政治','认知科学','文学'}),
    (['掌控谈话','控制谈话','掌控对话'], {'沟通技巧','谈话技巧','影响力'}),
]

def scan_core_theme_missing(t, pts):
    """返回 [(规则名, p)] 列表。当书名含分类关键词时首词必须落在合法集合里。
    命中策略：CATEGORY_HEAD 按顺序遍历，第一个分组命中即采用——避免一本书同时命中
    "沟通"和"谈判"两组被误判（典型：哈佛谈判思维书名含「谈判」+「沟通困境」）。
    """
    if not pts:
        return []
    head = pts[0].strip()
    for name_keys, legal in CATEGORY_HEAD:
        hit = any(nk in t for nk in name_keys)
        if not hit:
            continue
        # 第一个匹配到的分组生效；head 落在合法集合（含子串匹配 e.g. "人际" 含 "人际沟通") → 通过
        if head in legal or any(h in head for h in [l[:2] for l in legal]):
            return []
        return [('RC306-flexible-v2核心主题词未占首词位', head, legal)]
    return []

def near_dup(pts):
    res = []
    for i, p1 in enumerate(pts):
        for j, p2 in enumerate(pts[i+1:], i+1):
            if p1 == p2:
                res.append((i, j, '完全相同'))
                continue
            for name, words in NEAR:
                if any(w in p1 for w in words) and any(w in p2 for w in words):
                    res.append((i, j, name))
                    break
    return res

# ---------- RC306-fix-misclassified 分类错归检测（用户2026-08-28原话：分类要按主题不能贴shelf）----------
# 关键词-分类映射（一个词命中一个或多个「应入」类目）
CATEGORY_RULES = {
    # 思维认知 = 思考总类（用户铁律：凡“思考/思维/认知/心智/结构化/水平思考/逻辑思考”都归这）
    '思维认知': ['思维','思考','认知','心智','结构化','水平思考','元认知','批判性思维',
              '认知偏差','心智模型','思想实验','隐性逻辑','发散思维','思维工具','重构',
              '逻辑思维','逻辑表达','结构化表达','认知重构'],
    '财富认知': ['理财','财商','金钱观','财务自由','投资','储蓄','消费','现金流','资产',
              '被动收入','复利','退休','预算','通胀','资本','杠杆','财务',
              '税务','纳税','退休金','养老金','金钱','富裕'],
    '哲学思辨': ['哲学','思辨','形而上学','存在主义','心学','伦理学','辩证法','唯心主义',
              '唯物主义','语言哲学','形式逻辑','逻辑哲学','哲学史','社会控制','规训',
              '异化','现象学','理性主义'],
    # 能力提升 = 具体可习得的“能力/技能”（不含“思考”本身；思考归思维认知）
    '能力提升': ['学习效率','刻意练习','一万小时定律','快速学习','记忆','阅读法','写作技巧',
              '写作','演讲','表达','故事','高效','演讲技巧','技能','专长','技艺',
              '创造','创造力','想象力','优势识别','才干发挥','潜能','天赋','自我发现'],
    '人际关系与沟通': ['沟通','谈判','人际','亲密','冲突化解','依恋','边界','性格',
                '外向','内向','心理学性格','社交','同理心','社会性','归属感','连接需求'],
    # 人性洞察 = 欲望/阴暗面/进化本能/底层生物心理（不含“思考类自助书”）
    '人性洞察': ['人性','从众','群体心理','社会心理','社会影响','说服','影响力','纵',
              '行为纵','情绪','情感','抑郁','焦虑','自卑','敏感',
              '道德判断','自私','利他','进化心理学','社会动物','社会认知','人际关系',
              '社交智慧','洞察人性','性格缺陷','人格','心理阴暗面','七宗罪'],
    '习惯养成': ['习惯','日常习惯','拖延','拖延心理','意志力','自律','日常行为','时间管理',
              '精力管理','内驱力','内在动机','自我控制','习惯回路','触发循环',
              '行为改变'],
    # 文学经典 = 故事性统一大类，不细分、不外迁
    '文学经典': ['小说','故事','文学','寓言','戏剧','诗歌','叙事','虚构','名著'],
}

def scan_misclassified(title, points, cur_cat):
    """RC306-fix-misclassified：书的关键词强烈指向另一类目但当前在 cur_cat → 报疑似错归。
    只警告不自动迁移，因为：
    1) 同主题词可能合法存在于多个类目（沟通技巧 既在人际也可能在销售）；
    2) 用户授权后才动清单；
    3) GOLD 豁免（已锁定案例）在更上层处理。

    防再犯规则（RC306-fix-misclassified v2）：
    - 文学经典 是统一大类，绝不报“外迁/细分”（用户铁律：文学不细分）。
    - 思维认知 是“思考总类”，凡关键词含思考类信号就不该被迁走；
      仅当“另一类目命中的关键词数 严格多于 当前类自身命中数”才报，
      避免把思考书误判去 能力提升/哲学思辨/人性洞察（第12/13轮踩过的坑）。
    """
    if not points:
        return []
    if cur_cat == '文学经典':   # 文学统一，不细分、不外迁
        return []
    cur_signal = CATEGORY_RULES.get(cur_cat, [])
    cur_matched = [kw for kw in cur_signal if kw in points]
    hits = []
    for c_target, kws in CATEGORY_RULES.items():
        if c_target == cur_cat:
            continue
        matched = [kw for kw in kws if kw in points]
        # 至少两个关键词命中，且该目标类命中数严格多于当前类（当前类才是更优归属）
        if len(matched) >= 2 and len(matched) > len(cur_matched):
            hits.append((c_target, matched))
    if not hits:
        return []
    # 取命中数最多的类目作为首要疑似去向
    hits.sort(key=lambda h: -len(h[1]))
    best, matched = hits[0]
    return [('RC306-fix-misclassified疑似错归', best, matched, cur_cat)]

def load_md(path):
    """解析 书籍核心要点清单.md 为 {title: {title, category, points}}。"""
    import re as _re
    books = {}
    title = cat = None
    for ln in open(path, encoding='utf-8'):
        if ln.startswith('## '):
            # 去掉【】/（100本）等装饰
            cat = _re.sub(r'[【】（）()\d本]', '', ln[3:]).strip()
            continue
        if ln.startswith('### '):
            title = ln[4:].strip()
            books[title] = {'title': title, 'category': cat, 'points': []}
            continue
        if ln.strip().startswith('- 关键词：') and title:
            words = _re.findall(r'`([^`]+)`', ln)
            books[title]['points'] = words
    return books

def main():
    fix = '--fix' in sys.argv
    use_md = '--md' in sys.argv
    if use_md:
        d = load_md('data/书籍核心要点清单.md')
    else:
        d = json.load(open(D, encoding='utf-8'))
    items = list(d.items())
    report = []
    locked_skip = []    # 锁定区被忽略的违例（仅记录不报）
    locked_kept = 0    # --fix 时锁定区跳过的本数
    auto_fixed = 0
    for k, v in items:
        t = v['title']
        if t in GOLD:
            continue
        # RC306-fix-locked：锁定分类整本跳过——任何违例一律降级为「跳过」
        if is_locked(v):
            locked_kept += 1
            # 仍扫一遍记日志，但不放进 report
            for p in v.get('points', []):
                h = scan_point(t, p)
                if h:
                    locked_skip.append((t, p, h))
            continue
        pts = v.get('points', [])
        for p in pts:
            h = scan_point(t, p)
            if h:
                conf = 'high' if (set(h) & {'RC101/102薄词孤词','RC105外部标签','RC106万金油','RC104术语装内行','RC100书名当概念','RC109品牌人名','RC110书名字面比喻'}) else 'mid'
                report.append((t, p, h, conf))
        nd = near_dup(pts)
        for i, j, name in nd:
            report.append((t, f'{pts[i]} ≈ {pts[j]}', [f'RC103/RC99同义重复({name})'], 'mid'))
        # RC306-flexible v2：核心主题词占首位检测
        ct = scan_core_theme_missing(t, pts)
        for rule, head, legal in ct:
            report.append((t, f'首词=「{head}」(应为 {"/".join(legal)})', [rule], 'mid'))
        mc = scan_misclassified(t, pts, v.get('category', ''))
        for rule, target, matched, cur in mc:
            report.append((t, f'现{cur or "未分"} → 疑为{target}', [rule + '(' + ','.join(matched) + ')'], 'low'))
    print(f'=== 非金标准书扫描，命中 {len(report)} 项 ===')
    print(f'=== 【锁定区】已跳过 {locked_kept} 本（分类 ∈ {LOCKED_CATEGORIES}，RC306-fix-locked 永不报） ===\n')
    if locked_skip:
        print(f'【锁定区扫描明细】（仅日志，不作为违规）—— {len(locked_skip)} 项：')
        for t, p, h in locked_skip[:10]:
            print(f'  [跳过] 《{t}》 | {p} | {",".join(h)}')
        if len(locked_skip) > 10:
            print(f'  ... 还有 {len(locked_skip)-10} 条（锁定区不展示全部）')
        print()
    from collections import Counter
    rc_counter = Counter()
    for t, p, h, conf in report:
        for x in h:
            rc_counter[x] += 1
    print('规则命中分布:')
    for rc, n in rc_counter.most_common():
        print(f'  {rc}: {n}')
    print('\n=== 明细 ===')
    for t, p, h, conf in report:
        print(f'[{conf}] 《{t}》 | {p} | {",".join(h)}')

    if fix:
        if use_md:
            print('\n[跳过] --md 模式不支持 --fix 写回，请用 json 模式或人工改 md。')
            return
        for k, v in list(d.items()):
            t = v['title']
            if t in GOLD:
                continue
            # RC306-fix-locked：锁定分类跳过 --fix，绝不写回
            if is_locked(v):
                continue
            new = [p for p in v.get('points', [])
                   if not (p in THIN_NOUN or p in LONE_VERB or p in OUTER_LABEL or p in VOGUE or p in {'黑天鹅','黑天鹅不可预测'} or p in BRAND_NAME or p in BOOK_METAPHOR or p in EMPTY_VAGUE)]
            if len(new) != len(v.get('points', [])):
                if new:  # 不删到空
                    v['points'] = new
                    v['source'] = v.get('source','') + '+autofix'
                    auto_fixed += 1
        json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'\n自动清理 {auto_fixed} 本（删纯黑名单项），已写回')
        print(f'锁定区跳过 {locked_kept} 本（RC306-fix-locked，绝不写回）')

if __name__ == '__main__':
    main()
