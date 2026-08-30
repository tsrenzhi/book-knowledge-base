# 书籍知识库（book-knowledge-base）

把读过的书沉淀成可检索、可视化、可连接的知识网络——一张知识卡片对应一本书，一张图谱把所有的书连成网。

## 它解决什么

- **读完就忘**：卡片把每本书的重点留下来，随时能回看，不用重新翻完整本书。
- **忘了自己之前的想法**：你当时记下的灵感、批注都留在卡片里，重读时能看见。
- **书与书是散的**：关系网让你看出哪本书在补充哪本、哪本在讲相近的话题，顺着关联接着读，知识连成体系。

## 这是什么 / 不是什么

- **它是「方法」**——5 个 skill 教你/AI 怎么把一本书做成卡片、怎么抽核心要点、怎么分类、怎么画关系网。
- **它不是「数据」**——`data/books-catalog.md` 在你本地起手时是空的，由你自己加书。
- **它附带了「示例」**——`cards/` 下 6 本书的完整卡片 md + html，作为「如何做」的范例。
- **它附带了「演示图谱」**——`index.html` 含完整 426 本书的关系网，**这是作者的私人阅读清单**，作为结构参考可，但请从自己的书单起步。

## 仓库里有什么

```
book-knowledge-base/
├── README.md              # 你正在看
├── LICENSE                # MIT 协议
├── CHANGELOG.md           # 变更记录（如何回滚 / 迁移到新版）
├── init.sh                # 一键装配：把 skills/ 拷到 ~/.workbuddy/skills/
│
├── index.html             # ⓘ 演示图谱：完整 426 本书关系网（作者私人数据）
├── 操作手册.md            # 新手向：场景化使用示例
├── 如何维护书单.md        # 改书单：只改 books-catalog.md，其他自动衍生
│
├── assets/                # 图谱依赖：d3 库
│
├── cards/                 # 6 本示例书（每本只含 md + html，不含 png）
│   ├── guo-fu-lun/                国富论
│   ├── na-wa-er-bao-dian/         纳瓦尔宝典
│   ├── lie-na-duo-da-fen-qi-zhuan/ 列奥纳多·达·芬奇传
│   ├── ren-lei-jian-shi/          人类简史
│   ├── fu-ba-ba-qiong-ba-ba/      富爸爸穷爸爸
│   └── sun-zi-bing-fa/            孙子兵法
│
├── data/
│   └── books-catalog.md   # ⓘ 书目真值（你改这一份，其他自动衍生）
│
├── scripts/
│   └── rebuild_final.py   # 基于 books-catalog.md 重生成 index.html
│
└── skills/                # 5 个 WorkBuddy 技能
    ├── book-knowledge-card/        # 知识卡片生成
    ├── book-core-points/           # 提核心要点
    ├── book-category-classify/     # 15 大类分类
    ├── book-knowledge-graph/       # 关系网生成
    └── book-knowledge-workflow/    # 端到端总控
```

## 怎么用

### 第一次使用
```bash
# 1. clone 仓库
git clone <repo-url>
cd book-knowledge-base

# 2. 一键装配 skill
bash init.sh

# 3. 打开操作手册看场景化示例
open 操作手册.md

# 4. 预览演示图谱（仅参考用，从自己的书单起步）
open index.html
```

### 加你的第一本书
1. 在 `data/books-catalog.md` 末尾加一行：
   ```
   N. 《你的书名》 作者 概念词1、概念词2 豆瓣评分
   ```
2. 跟 WorkBuddy 说：**「用 book-knowledge-card 给《你的书名》做一张知识卡片」**
3. 重生成图谱：`python3 scripts/rebuild_final.py`

详见 `如何维护书单.md`。

### 6 本示例书怎么用

`cards/` 下 6 本书是**模板**，不是「你必须读完的清单」。它们存在的意义是：
- 让你看「一张完整的知识卡片长什么样」
- 让 skill 学到「好卡片的标准」是什么
- 让你按它的 md 文件结构，照着给新书写

**图片资源（png 预览图、达芬奇传插图）刻意没放进仓库**——你可以跑 skill 自己生成，也可以用浏览器直接打开 html 看矢量版。

## 关键原则

- **数据真值只在一处**：`data/books-catalog.md` 是你唯一改的地方。其他文件都从它衍生。
- **分类有边界铁律**：15 大类不要乱加。详见 `操作手册.md`。
- **脚本要去绝对路径**：`scripts/rebuild_final.py` 用相对仓库根目录的路径，clone 到任何位置都能跑。

## 开源说明

- 协议：MIT（见 LICENSE）
- 演示图谱 `index.html` 含作者私人阅读清单——clone 后**请用你自己的数据覆盖**，或删掉它重生成。
- 6 本示例书的 md 内容（国富论.md 等）也来自作者个人笔记，可以参考但请替换为你的版本。

## 贡献

提 Issue 报 bug 或想要的功能；提 PR 改 skill 文档、补示例书、调脚本都可以。

## 更新记录

见 [CHANGELOG.md](./CHANGELOG.md)。
