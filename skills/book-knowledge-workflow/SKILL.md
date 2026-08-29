---
name: book-knowledge-workflow
description: 书籍知识库端到端总控 SOP —— 编排「输入 → 建卡(book-knowledge-card) → 提要点+分类(book-core-points + book-category-classify) → 建图谱(book-knowledge-graph)」全流程。触发词：书籍知识库流程、端到端建书库、拉书建卡建图谱、整库流程、批量梳理书、新增一本书全流程、书库怎么搭、图谱加卡片怎么组织、怎么开源部署书籍图谱。本 skill 不重复各子 skill 的写法纪律，只负责"按顺序把子 skill 串起来 + 对齐真实产物命名/铁律"，具体写法看被编排的子 skill。详细面向人的操作见仓库根 `书籍知识图谱-操作手册.md`（与本文档同源）。
---

# 书籍知识库 · 端到端总控工作流（Book Knowledge Workflow）

## Overview

把「一本书 / 一段笔记 / 一个书名 → 一张可视化卡片 + 一份结构化 md + 2-4 个可迁移概念词 + 知识星系里的一个节点」这条链路**标准化成可复用的 SOP**。

本 skill 是**总控 / 编排层**，自己不写卡片、不提炼词、不画图谱，而是按顺序调用子 skill + 内部 build 脚本。具体写法纪律在各自子 skill 里。

> **链路铁律**：① 卡片/笔记永远是 ②③ 的**唯一真值源**。卡片先落，概念词与图谱节点跟着它走；绝不让图谱凭空编节点，绝不让概念词脱离卡片内容。②③ 是①的**强制下游**——做完一本必须顺手更新，不要等全部做完再补（存量重做最易漏细节）。

## 技能地图（5 个核心，本仓库搭库专用）

| 角色 | skill | 职责 | 产物 |
|---|---|---|---|
| ① 建卡 | `book-knowledge-card`（888 行，最全） | 可视化卡片 + 双格式 md | `《书名》/《书名》-知识卡片.html` + `.md` |
| ② 分类 | `book-category-classify`（113 行） | 归 15 大类（边界真值） | 分类判定 |
| ② 提词 | `book-core-points`（334 行） | 抽 2-4 可迁移概念词 | `书籍核心要点清单.md` / `v8-core.json` |
| ③ 建图 | `book-knowledge-graph`（118 行） | 增量节点 + 出图 | `书籍知识图谱-真实版.html` 等 |
| 总控 | `book-knowledge-workflow`（本文） | 只编排不写内容 | — |

> 注：`book-reading-framework`（长文阅读框架）和 `book-theory-support`（写稿时找书撑观点）是另外两个独立 skill，**跟搭库本身没关系**，是创作用途，所以没列进本表。

## 数据真值源与目录（现实命名 · 2026-08-29 对齐）

```
~/WorkBuddy/books/
├── 书籍知识图谱-真实版.html        ← 图谱主力（fix7d，md5 3e6f8a83，内嵌数据 0 fetch，双击即开）【日常迭代在这】
├── ✅当前基线-fix7d-3e6f8a83.html  ← 🏆 黄金副本（禁止覆盖，一键回滚）
├── 书籍知识图谱.html              ← 锁死的 v25.46 原始参考样板（md5 e0e419cb，只看不改）
├── 书籍知识图谱-核心要点.html      ← 核心要点新图（书→概念词组织）
├── graph.json                      ← 旧版全量关系网（机器真值，已锁死不再增量）
├── graph.points.json               ← 核心要点新图数据（由 _build_points_graph.py 出）
├── v8-core.json                    ← 【用户最终清单真值】含 author/concepts，build 脚本读它
├── 书籍核心要点清单.md             ← 人读要点清单
├── 分类总览-v8.md                  ← 【分类唯一真值·显示用】build 从这里解析书名/作者/概念
├── BOOK-CATALOG.md                 ← 15 大类权威来源
├── 《书名》/
│   ├── 《书名》.md                  ← 双格式之一：结构化文本（带 frontmatter）
│   └── 《书名》-知识卡片.html        ← 双格式之二：可视化卡片（最高优先真值）
├── _build_v8_truth.py              ← 内部脚本：读 v8-core.json → 出 书籍知识图谱-真实版.html
└── _build_points_graph.py          ← 内部脚本：读 书籍核心要点清单.md → 出 graph.points.json + 核心要点新图
```

**三处真值链（改一处必同步另外两处）**：
- 卡片笔记 frontmatter 的 `category` ← 来自 `分类总览-v8.md` / `BOOK-CATALOG.md`（15 大类）
- `书籍核心要点清单.md` / `v8-core.json` 的分类 ← 同上
- 图谱节点的 `category` ← 同上

## 端到端 SOP（5 阶段 · 对齐现实）

### Phase 0 · 输入获取
- **A. 用户给素材**（笔记/划线/口述/成稿）→ 直接进 `book-knowledge-card` 的「输入即素材」通道。
- **B. 只给书名（没读过）→ 速读模式**：`book-knowledge-card` 调微信读书接口取真实重点（章号/热门划线必须来自真实返回，**严禁编造**）。
- **C. 微信读书书架批量**：`book-knowledge-card` 的 `pull_weread` 通道拉书架 → 标 15 类 → 批量建卡。

> **分类纪律（贯穿全程）**：动笔/归类前先查 `分类总览-v8.md` + `book-category-classify` 这本归哪类；`category` 在卡片/清单/图谱三处必须一致。

### Phase 1 · 建卡（book-knowledge-card）
1. 写前强制预读标杆（国富论 / 纳瓦尔宝典 / sample-国富论.html）+ 跑写前输入闸门。
2. 产 `<书名>.md`（frontmatter 带 `category` + `concepts` + `related_books`）+ `<书名>-知识卡片.html`（六段骨架/四块必含/语言铁律/视觉规范全过）。
3. **先 HTML 后 PNG**：HTML 改完、用户说"可以出图"才生 PNG。
4. 双格式落盘到 `~/WorkBuddy/books/《书名》/`，**绝不覆盖标杆母版**。

### Phase 2 · 提要点 + 分类（book-core-points + book-category-classify）
1. **分类归属先走 `book-category-classify`**（15 类唯一真值：边界/用户三铁律/迭代版本纪律）。
2. 从 Phase 1 的 md 抽可学内容 → 给 2-4 个**可迁移短概念词**（≤8 字）。
3. 过 `book-core-points` 的「9 类必杀」自检 + `references/check_points.py` 自检（0 违规才收）。
4. 追加进 `书籍核心要点清单.md` / `v8-core.json`，归到对应 15 类。
5. **迭代时永远先 Read 当前磁盘 `分类总览-v8.md`**，绝不凭记忆补回用户删的书。

### Phase 3 · 增量建图谱（book-knowledge-graph）
1. **当前主力产物是 `书籍知识图谱-真实版.html`（手改内嵌 HTML + `_EMBEDDED_GRAPH`，0 fetch）**，不是模板注入架构。新增/改书后：
   - 改数据真值 `v8-core.json` / `书籍核心要点清单.md` → 跑 `_build_v8_truth.py` 重建 `书籍知识图谱-真实版.html`；
   - 或直接在真实版 HTML 上做力导向/交互微调（这是日常迭代方式）。
2. **核心要点新图**：跑 `_build_points_graph.py` 从 `书籍核心要点清单.md` 出 `graph.points.json` + `书籍知识图谱-核心要点.html`。
3. **CARD_MAP 跳转**：构建时扫描 `~/WorkBuddy/books/` 下所有 `《书名》/*知识卡片*.html`，建立节点 click → 卡片跳转。没有卡片的书节点 click 静默不响应。
4. 双击 HTML（file:// 即可）验证新节点出现、同大类成团、相悖红线连。

> **现实与旧文档的差异（务必知道）**：早期 `book-knowledge-graph` 描述的 `gen_spatial.py` 模板注入 `galaxy-template.html` 架构，在当前主力产物上**未采用**——真实版是手改内嵌 HTML。开源时若要长期可维护，建议回到"模板 + 脚本注入"架构（改 UI 改模板、改数据改 json、跑脚本出图），避免手改 600KB HTML 难维护。**但无论哪种，交付前必过三关（见下）。**

### Phase 4 · 回灌与校验（选跑）
- **三向一致性**：`书籍核心要点清单.md` / `v8-core.json` / 图谱节点 的 `category` 必须一致。
- **用户审阅门**：清单分类/剔除等"动用户书库"的动作，死守不擅自动——先呈现给用户，用户改完再回灌。
- **黄金版机制**：`✅当前基线-fix7d-3e6f8a83.html` 是「目前最好版本」，md5 锁死禁止覆盖；出问题 `cp` 它救回。

## 交付前三关验证（2026-08-29 铁律 · 少一道都可能把图改崩）

1. **关卡 1 · 语法**：抽取 HTML 内 `<script type="module">` 跑 `node --check`，抓 SyntaxError（孤立 `*/`、漏闭合 `}`、TDZ 引用未声明变量等浏览器只"全图空白"不报错的致命错）。
2. **关卡 2 · 内嵌**：确认 HTML 100% 内嵌数据（`_EMBEDDED_GRAPH`），`fetch('./graph.json')` 计数 = 0。file:// 下 fetch 会被 CORS 拦截且部分 Chrome 会 pending 卡死后续代码。
3. **关卡 3 · 真渲染**：headless chrome 跑一次 `--dump-dom`，grep `<circle` 数量 = 预期节点数（当前 1597），确认不空白。

> **已知 TDZ 坑**：d3-force v3 的 `forceX(fn).initialize` 会**同步**调 `fn(node)` 预计算，被引用的 `let` 变量必须在 force config **之前**声明，否则 `ReferenceError: Cannot access 'x' before initialization` 全图空。

## 红线速查（编排层最易翻车）

- **原始样板锁死**：`书籍知识图谱.html`（md5 e0e419cb）只看不改；新迭代全在 `书籍知识图谱-真实版.html`。
- **graph.json 锁死**：旧版全量关系网不再增量；新图只产 `graph.points.json` + `书籍知识图谱-核心要点.html`。
- **黄金副本禁止覆盖**：`✅当前基线-fix7d-3e6f8a83.html`。
- **RC110（用户审阅门）**：改用户书库分类/删书/重分类必须等用户确认。
- **RC304（小白文档）**：面向人的操作文档以"对 WorkBuddy 说话"为单位，禁终端代码块/多平台分支/技术黑话；见 `书籍知识图谱-操作手册.md`。
- **三关验证**：交付前必过（语法/内嵌/真渲染）。

## 开源部署到 GitHub（给维护者）

**面向人的使用文档是 `书籍知识图谱-操作手册.md`**（纯小白向，全是「对 WorkBuddy 发一句话」的对话示例，普通使用者看那份就够了）。本节的命令细节只给需要自己维护代码仓库的人看。

要点：

1. **只挑要分享的文件入库**：图谱网页（真实版 / 核心要点 / 原始样板）+ 数据（graph.json / graph.points.json / v8-core.json / 清单 md）+ 文档（操作手册 / GRAPH.md / 图谱规范样式.md）+ 已有卡片目录 + 5 个 book-* 技能源 + 内部 build 脚本。
2. **开发过程中的副本不要开源**：所有 `⏸️回滚备份-*`、`✅当前基线-*`、`baseline-*`、`.bak`、`.pre-*`、`__pycache__`、`.DS_Store` 用 `.gitignore` 挡掉（见仓库根 `.gitignore`）。
3. **GitHub Pages 直接托管**：因 HTML 100% 内嵌（0 fetch），push 后 Settings→Pages→main/(root) 即可访问，无需后端。
4. **回滚机制随仓库走**：黄金副本 `✅当前基线-fix7d-3e6f8a83.html` 一并入库，出问题 `cp` 救回。

## 子 skill 索引（写法纪律看各自）

- `book-knowledge-card` —— 建卡 + 双格式 md（视觉/语言/结构/红线最全）。
- `book-core-points` —— 提炼 2-4 个可迁移概念词（9 类必杀 + check_points.py）。
- `book-category-classify` —— 归 15 大类（边界/迭代版本纪律）。
- `book-knowledge-graph` —— 增量节点 + 出图（RC 红线速查 + 脚本架构）。
- 三者构成「真值源 → 概念词 → 跨书节点」的闭环；本 skill 是它们的编排入口。
