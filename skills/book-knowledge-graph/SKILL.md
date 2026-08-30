---
name: book-knowledge-graph
description: 把书籍知识库（你的书籍库/）的书与核心概念构建成可可视化的「知识星系 / 知识图谱」。核心数据是一个机器可读的全局关系网络 graph.json，星云 Demo 直接消费它。触发词：书籍知识图谱、知识星系、跨书关联、书与书怎么关联、把书做成星云、图谱、graph.json、relation。同时作为 book-knowledge-card 产出后的强制联动环节——每做完一本书的卡片，必须增量更新 graph.json 并刷新 Demo（不要等所有书做完再补）。
---

# 书籍知识图谱（Book Knowledge Graph）

## Overview

把 `你的书籍库/` 里的书及其核心概念，构建成可可视化的「知识星系 / 知识图谱」。核心数据是一个机器可读的全局关系网络 `graph.json`，可视化 Demo（力导向图）直接消费它。

本 skill 是 **`book-knowledge-card` 的强制联动环节**：每做完一本书的卡片，必须回到这里增量更新 `graph.json` 并刷新 Demo。书少时关系不强、不好看，是正常现象——图谱随书增多自然变密，不要等「全做完了」再补（那样等于把存量重做一遍，还容易忘细节）。

## 何时用 / 与卡片 skill 的关系

- 做完一本书的知识卡片 → **必须**调本 skill 增量更新图谱（见增量流程）。
- 用户问「书与书怎么关联 / 做成星云 / 知识图谱 / 跨书关系」→ 直接用本 skill 的 schema 与 Demo。
- 单本书内容拆解（卡片、md）仍归 `book-knowledge-card`；跨书关系层归本 skill。

## 数据架构（真值源）

- `你的书籍库/graph.json` —— 全局关系网络，**机器真值**，可视化直接读它。
- `你的书籍库/GRAPH.md` —— 给人看的图谱规范文档（节点/关系字典 + 增量流程）。
- 每本书 `《书名》.md` 的 frontmatter（`book_id` + `concepts[].id` + 结构化 `related_books`）是 graph.json 的**来源**：写书时按规范写，增量时直接搬进 graph.json。

## 增量流程（每做完一本就做，4 步）

1. **新书 frontmatter 合规**：`book_id`（英文/拼音，避免中文路径）、`category`（大类，15 选 1）、`subcategory`（小类，可选）、`concepts` 每项带 `id`、`related_books` 为结构化对象数组（`book_id / book / relation / concept_link / note`）。schema 见 [references/schema.md](references/schema.md)。
2. **增量 graph.json**：在 `nodes` 加这本书（type=book, status=done, category/subcategory）+ 它的代表概念（type=concept, book=book_id, category=继承）；在 `links` 加书↔书、书↔概念的连线，relation 用统一字典。引用了但还没收录的书，标 `status: "referenced"`（虚线圆），收录后改 `done`。
3. **跑一次 `python3 scripts/gen_spatial.py`**：默认输出 `书籍知识图谱.html`（**v25 起唯一准版本，旧的 `书籍知识图谱-demo.html` 已冻住不再用**）。脚本会自动扫描 books/ 下所有"知识卡片"html 文件构建 CARD_MAP；**默认内嵌完整 graph.json 到 `_EMBEDDED_GRAPH`**（双击 file:// 立即能用，绝不报"必须 server 打开"红色 fail box）+ async fetch('./graph.json') 作为可选升级（HTTP server 打开时拿最新数据替换内嵌）。**判别**：改 HTML 数据流时 grep `_EMBEDDED_GRAPH = {` 锚点；fetch 写进 try/catch + catch 静默回退到内嵌（**绝不在 catch 里 throw / 弹错误框**）。
4. **验证布局**：双击 `书籍知识图谱.html`（file:// 即可，**无需起 server**）→ 应秒开并显示新节点；不显示就重跑第 3 步。同大类自然成团、关系相近的自动聚类、相悖用红线连、待收录书是虚线圆。

> **🔴 RC71 demo.html 数据源铁律（v23 暴怒新立、v24 修正、v25 改主版）**：用户原话"你这个 books 文件夹下已经有这个 HTML 了，你为啥又新建了一个呀？……这个都打不开了"。**所有由本 skill 产出的图谱 HTML** 必须**默认内嵌 graph.json**——用户历来是双击 file:// 打开，绝不能改成 fetch-only 报"必须 server 打开"的红色 fail box。**正确写法**：默认 `const GRAPH = _EMBEDDED_GRAPH;` → try fetch 升级 → catch 静默回退到内嵌（不报错）。改任何图谱 HTML 的数据源前先 grep `_EMBEDDED_GRAPH` 锚点和 `必须 server` fail 字样。

> **🔴 RC72 空间感版唯一主版（v25 立 · v25.3 用户终审定稿）**：`gen_spatial.py` 输出的 `书籍知识图谱.html` 是唯一准版本。**旧的 `书籍知识图谱-demo.html` 已冻住、禁止再手动改动或用作交付**——以后每做完一本书只刷新空间感版。背景铁律（v25.3 用户拍板）：径向渐变 `中心浅 / 四周深`（深色 `#27374F→#1A2238→#0C1120`，浅色 `#FFFCF5→#ECE0C8→#C8B596`）；**绝不加中间黑洞、星云、光晕、四角羽化**；节点实色清亮 + 细白描边 + 柔 drop-shadow，不灰头巴脸不虚边。需要回旧版调试样式才用 `gen_demo.py`，且不得反向污染主版。

## 关系字典（速查）

| relation | 含义 | 颜色 |
|---|---|---|
| 相似 | 说同一件事 / 思路相通 | 雾绿 `#7BC47E` |
| 互补 | 角度不同但拼起来更全 | 雾青 `#5DBDBD` |
| 相悖 | 观点相反 | 暖红 `#E8483E`（虚线） |
| 批判 | A 批判 B 旧框架 | 暖红 `#E8483E`（虚线） |
| 包含 | 书包含某概念 | 牛皮 `#C9B18A` |
| 引用 | A 继承 / 引用 B | 雾紫 `#A88BD8` |
| 应用 | 理论→实践 | 黄油 `#F5C84C` |

完整节点/连线字段 + frontmatter schema 见 [references/schema.md](references/schema.md)。

## 脚本架构（v25.48l 重构 · 脚本=产物唯一真值）

早期版本 `gen_spatial.py` 在脚本里内嵌 530 行 HTML 模板字符串，导致"脚本跟手调产物严重脱节"——脚本里还是 v25.27 的旧参数（`initialT = d3.zoomIdentity.translate(W/2,H/2)` + viewBox 1.2x 偏移 + 关系图例仍渲染等），重跑一次就把"不偏右/不挤一团"等几十轮手调优化全冲掉。

**v25.48l 终态架构**：
- `assets/galaxy-template.html` —— UI 外壳（CSS + `<script type="module">` 含全部 RC 修复 + `/*EMBEDDED_GRAPH_DATA*/` + `/*CARD_MAP*/` 两个占位符），从产物 HTML 抽取生成。
- `scripts/gen_spatial.py` —— 读 graph.json → 标签清洗（剥书名副标题）→ 扫 books/ 找 `*-知识卡片.html` 构 CARD_MAP → 读模板 → 把两个占位符替换成 `json.dumps` → 写产物 HTML。

从此**改任何 UI/交互都改模板 HTML**，再跑脚本同步到产物；改数据改 graph.json，再跑脚本出图。**重跑脚本永远 = 当前产物状态**。

## 🔴 RC 红线速查（v25.48l 终态 · 改模板或脚本前先看）

| 编号 | 红线 | 出处 |
|---|---|---|
| **RC71** | 图谱 HTML 必须默认内嵌 `_EMBEDDED_GRAPH` + fetch 静默升级；禁止 fetch-only 弹红色 fail box | v23 暴怒 |
| **RC72** | `书籍知识图谱.html` 是唯一准版本；旧 `demo.html` 冻住，禁止反向污染主版 | v25 |
| **RC120** | 搜索框只显示书名+作者（`searchItem` 字号 10px），禁止加概念副行 | 用户原话"操你妈干瞎干什么" |
| **RC124** | 右上角关系图例整行 `display:none`（`#relFilters` 隐藏），只留连线 | 用户原话"我不需这些" |
| **RC125** | 只有**双击背景**才 `fitContent`；禁止 `sim.on("end")` / `setTimeout` 自动 fit（"我划过去了又跑到中间去了"） | v25.48g |
| **RC129** | 跨类桥概念=内部标签非视觉特征；靠连线密度自然展现，不单独配色、不进图例 | v25.38 |
| **RC131** | `initialT = d3.zoomIdentity`（**必须不平移**）；`d3.zoomIdentity.translate(W/2,H/2)` 会把整图推到右下角，左半空白 0-960 | v25.48k 根因 |
| **RC133** | 生成"待审补充"清单永远并入主结构同一分类，不要另起独立区块重复列 | v25.48l |
| **密度四件套** | 初始位置 `W*0.42 / H*0.65`；charge `-240`；link 距离 `160/85/55` strength `0.45`；collide `radius(d)+12 / 0.7` | v25.48l |
| **配色** | 15 类沿色相环均布+浅一档：明度≥60%/饱和≤80%；禁灰/褐/米/纯深族 | RC107 |
| **节点描边** | 书 `rgba(255,255,255,0.75) 1.5px` / 概念 `rgba(255,255,255,0.45) 0.8px`；禁黑边/粗描边；文字不加 stroke | 定稿 |
| **背景** | 径向渐变中心浅四周深（深 `#27374F→#1A2238→#0C1120`，浅 `#FFFCF5→#ECE0C8→#C8B596`）；禁黑洞/星云/光晕/四角羽化 | RC71 |
| **数据源脚本坑** | sync 注入时**用 `let GRAPH = _EMBEDDED_GRAPH;` 作下界锚点**，避开 `const _EMBEDDED_GRAPH = {` 双重花括号永不闭合 | RC116 |
| **搜索与图谱隔离** | 清图谱高亮绝不污染搜索输入区（不写 `searchInput.value` 复位） | RC130 |
| **RC300** | 概念节点颜色**必须继承所属书 category**；模板渲染 `fill` 永远先查 `concept.category` 在色板有没有，没有就回退 `nodeById.get(concept.book).category`。重分类只改 book 不改 concept = 视觉颜色错乱（已用 `repair_concepts.py` 修 72 个错位） | v3 重分类漏同步 |
| **RC303** | `fitCategory` **只平移绝不缩小**：`k = Math.max(cur.k, 1.0)`，bbox 只用来算平移中心，scale 绝不用 bbox-fit 公式。组溢出屏幕正常（让用户自己拖），双击背景才 `fitContent` 复位 | 用户反复骂"搞那么小看不清" |
| **RC302** | 每次改 `galaxy-template.html` / `scripts/*` 必须 `cp -R` 同步到开源 repo `book-knowledge-skills/skills/<name>/`，否则开源版漂移缺修复 | 开源前铁律 |

## 资源

- `scripts/gen_spatial.py`（**v25.48l 唯一主用**）：读 `assets/galaxy-template.html` + `graph.json` → 输出 `书籍知识图谱.html`。支持 `gen_spatial.py G.json OUT.html` 指定输入输出（开源 example 用）。每次新增/改任何书都跑一次。
- `assets/galaxy-template.html`：**UI 真值**，含全部 RC 修复。改 UI/交互改这里（再跑脚本同步到产物），不要直接手改产物 HTML。
- `references/schema.md`：graph.json 与 frontmatter 的完整字段规范 + 增量流程细节。

## 🔴 RC304 用户面向文档铁律（2026-08-26 用户原话"你搞那么多又是终端又是代码的东西"）
- **任何面向小白的使用文档（小到 README、大到 USAGE.md）必须以"对 WorkBuddy 说话"的提示词为单位组织内容**。
- **禁止出现**：终端代码块（`export xxx=...`、`cp -R ...`、`python3 ... .py`、`http.server`）、多平台分支（macOS/Linux/Windows 各写一遍）、技术黑话（环境变量/Bearer Token/抓包步骤/绝对路径）。
- **替代写法**：
  - 安装 → "在 WorkBuddy 技能市场搜 `book-knowledge` 装一下" 或 "对 WorkBuddy 说『帮我装 book-knowledge-card 这个 skill』"
  - 拉数据 → "跟 WorkBuddy 说『从我的微信读书拉所有读过的书』，它会让你去 weread.qq.com 复制一段密钥粘贴给它"
  - 改东西 → "对 WorkBuddy 说『把《XXX》删掉』"
  - 找文件 → "问 WorkBuddy『我的书库在哪』"
- **检验**：用户拿到文档后，**能否只在对话里完成所有事、不用碰任何编辑器/终端**。能 = 通过；不能 = 立刻精简。
- **位置**：repo 根 `书籍知识图谱.md` + workflow skill 源同文件。两份必须一致。

## 🔴 RC71·HTML 数据源单一真值铁律（适用于所有图谱 HTML）

所有由本 skill 生成的图谱 HTML（含旧的 demo.html 和新的 空间感.html）**必须**默认走 `const GRAPH = _EMBEDDED_GRAPH;` + async fetch 升级路径。**禁止**只跑 fetch 不内嵌——历史上 v23 把影响力节点写进 graph.json 后 demo.html 仍"看不见"，v24 又改成 fetch-only 弹 fail box，都是这一条没焊死。

- 每次改完 graph.json → 跑 `gen_spatial.py`（默认）重新输出空间感版 HTML，脚本会自动从 books/ 目录扫新书到 CARD_MAP
- 本地预览：直接双击 `书籍知识图谱.html`（file:// 即可，无需 server）；起 server 用 `python3 -m http.server` 在 books/ 目录（如 8096 端口），浏览器开 `http://127.0.0.1:8096/书籍知识图谱.html`
- 自检：刷新后点大星能弹出对应知识卡片 = 链路通；不能 = 检查 books/<书名>/<书名>-知识卡片.html 是否存在且文件名含"知识卡片"

## 设计纪律（不照抄古诗星云）

书籍没有朝代/人名这类硬关系，靠**语义亲疏**聚类：相似→近、互补→中、相悖→远但红线连（对立是刻意设计，不是漏连）。不要照搬「按时间排」的星空逻辑——书的世界是观点世界，不是编年史。

**关系质量红线**：书与书的连线必须基于**核心观点的明确对应**，不能因为 A 书里出现某个词（如"金钱""信任""规则"），就硬拉一条线到同样出现这个词的 B 书。判断标准：两书是否真正在回答同一个问题、拆解同一个底层机制、或指向同一套人性/认知/行为逻辑？如果只是"提过"而非"核心论证"，宁可不连。关系少而实，远好于关系多而牵强。

**配色/分类**：按**大类（category）**分组着色（同大类书同色系，不是每本书随机色）。15 个大类色板参考生活方式品牌包装：暖奶油底 + 低饱和高明度粉黄蓝绿 + 一个高能量暖红锚点（如 Horse Gift 的 `#E8483E`）。具体值见 `graph.json` 的 `meta.category_colors` 与 `meta.color_by_relation`；新增大类先从现有 5 个色系家族里取同色系延伸，保持暖调、低饱和、高明度，禁冷灰、禁纯霓虹。书节点加兼容版柔和投影（`feGaussianBlur+feOffset+feMerge`，避免 `<feDropShadow>` 在某些浏览器不渲染），模拟包装在暖光下的浮起感。

**大类小类**：每本书必填 `category`（15 个大类之一，权威来源 = `wereading-blog/js/books.js` 的 `window.BOOK_LIST`，已与 `graph.json` 的 `meta.categories` 逐本核对一致）。用户暂定**不加小类**，每本书单分类，`subcategory` 暂不填充、不做二级聚类。同大类在力导向图中有弱引力聚类。

**节点描边（已定稿，禁倒退）**：节点圆圈**不得用深色/黑边**（`#6A6058`、`var(--line)`、纸色粗描边等一律禁用——早期版本因此出现过"黑边"被用户否掉）。最终规则：书节点 `rgba(255,255,255,0.75)` 1.5px、概念节点 `rgba(255,255,255,0.45)` 0.8px、待收录虚线圆照旧不描边；节点文字**不加任何 stroke / paint-order**，纯靠背景色保证可读。这版用户已确认满意，以后改 gen_spatial.py 重生成时这条必须保留。
