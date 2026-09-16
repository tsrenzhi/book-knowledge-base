# 图谱数据规范（schema）

> 本文件是 `book-knowledge-graph` 的字段级真值规范。`graph.json` 由 `scripts/rebuild_clean.py` 从 `书单数据源.md`（每本的分类 + 关键词）构建——**改书单就重建，不手改 graph.json**。

## 一、graph.json 顶层结构

```json
{
 "meta": {
 "version": "1.0",
 "description": "书籍知识库全局关系网络……",
 "node_types": ["book", "concept"],
 "relation_types": ["相似", "相悖", "互补", "应用", "引用", "批判", "包含"],
 "categories": ["经济与商业", "思维认知", "底层规律", "人性洞察", "文学经典", "能力提升", "习惯养成", "人际关系与沟通", "财富认知", "名人传记", "哲学思辨", "成事方法", "决策避坑", "心理成长", "历史"],
 "color_by_relation": { "相似": "#7BC47E", "互补": "#5DBDBD", "相悖": "#E8483E", "包含": "#C9B18A", "引用": "#A88BD8", "应用": "#F5C84C", "批判": "#E8483E" },
 "category_colors": { "经济与商业": "#F5C84C", "思维认知": "#5DBDBD", "底层规律": "#4A9AA8", "人性洞察": "#E85A5A", "文学经典": "#C9B18A", "能力提升": "#8FCB8F", "习惯养成": "#B8E0B8", "人际关系与沟通": "#F4A6B8", "财富认知": "#F9E07A", "名人传记": "#B89ECB", "哲学思辨": "#A89880", "成事方法": "#E87A8A", "决策避坑": "#7ACFE0", "心理成长": "#F2C6C6", "历史": "#D4B896" },
 "group_colors": { /* category_colors 的别名，兼容旧逻辑 */ }
 },
 "nodes": [ /* 见下 */ ],
 "links": [ /* 见下 */ ]
}
```

### node 字段

| 字段 | 必填 | 适用 | 说明 |
|---|---|---|---|
| id | 是 | 全部 | 全局唯一，英文/拼音（如 `wealth-of-nations`），避免中文路径/引用乱码 |
| type | 是 | 全部 | `book` / `concept` / `category` / `author` |
| label | 是 | 全部 | 显示名（中文） |
| author | 否 | book | 作者 |
| year | 否 | book | 出版年，公元前用负数 |
| category | 是 | book/concept | 大类（如「经济与商业」「人性洞察」），决定节点颜色 |
| subcategory | 否 | book | 大类下的小类（如「经济学原理」「战略决策」），tooltip/二级筛选用 |
| group | 是 | book/concept | `category` 的别名，兼容旧可视化逻辑 |
| book | 否 | concept | 所属书 id，用于归类与跳转 |
| status | 否 | book | `done`（已收录）/ `referenced`（引用待收录，渲染为虚线圆） |
| importance | 否 | concept | 1–5，决定概念节点大小 |

### link 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| source | 是 | 源节点 id |
| target | 是 | 目标节点 id |
| relation | 是 | 见关系字典 |
| concept | 否 | 关联的概念名（tooltip 用） |
| note | 否 | 一句关系说明（双击/tooltip 展示） |

## 二、关系字典

| relation | 含义 | 连线颜色 | 线型 |
|---|---|---|---|
| 相似 | 说同一件事 / 思路相通 | 雾绿 `#7BC47E` | 实线 |
| 互补 | 角度不同但拼起来更全 | 雾青 `#5DBDBD` | 实线 |
| 相悖 | 观点相反 | 暖红 `#E8483E` | 虚线 |
| 批判 | A 批判 B 的旧框架 | 暖红 `#E8483E` | 虚线 |
| 包含 | 书包含某概念 | 牛皮 `#C9B18A` | 实线 |
| 引用 | A 继承 / 引用 B | 雾紫 `#A88BD8` | 实线 |
| 应用 | 理论 → 实践 | 黄油 `#F5C84C` | 实线 |

空间语义：相似度越高越近；相悖强制分到两侧但用红线连着（表示「这对立是刻意设计」）；同大类有弱引力聚类；待收录书（referenced）渲染为虚线圆、不强制入簇。

## 三、增量流程（每做完一本就做）

1. 新书写进 `书单数据源.md`：`数字. 《书名》｜作者：X｜关键词：a、b、c｜豆瓣评分：X`，归到 15 类里对应那一类。
2. 在 `graph.json` 的 `nodes` 加这本书（status=done）+ 它的代表概念（type=concept, book=book_id, category=继承）；在 `links` 加书↔书、书↔概念的连线。
3. **跑一次 `python3 scripts/gen_spatial.py`**（默认输出 `书籍知识图谱.html`，**唯一准版本**，旧的 demo 版已冻住）。脚本会从 `assets/galaxy-template.html`（UI 外壳，含全部 RC 修复）读取模板，注入 `graph.json` 与自动扫到的 `CARD_MAP`，写回产物 HTML。**默认内嵌完整 graph.json 到 `_EMBEDDED_GRAPH`**（双击 file:// 立即能用，绝不报"必须 server 打开"红色 fail box）+ async fetch('./graph.json') 作为可选升级（HTTP server 打开时拿最新数据替换内嵌）。**判别**：改 HTML 数据流时 grep `_EMBEDDED_GRAPH = {` 锚点；fetch 写进 try/catch + catch 静默回退到内嵌（**绝不在 catch 里 throw / 弹错误框**）。
4. 验证：同大类自然成团、关系近的自动聚类、相悖用红线连、待收录书是虚线圆。标错就改 graph.json 重跑。

## 四、与古诗图谱的关键区别（设计纪律）

古诗靠**朝代 + 亲密度**聚类（白居易↔元稹近、王维→李白远）；书籍没有这种硬关系，但有更强的**语义关系**。所以图谱不按时间排，而按**观点亲疏**排——这是书籍图谱的本质，不照抄图谱逻辑。
