#!/usr/bin/env bash
# 一键初始化：把本仓库的 skills/ 装到 ~/.workbuddy/skills/
# 同时校验关键依赖、给第一次跑的用户一个干净起点
#
# 用法：bash init.sh
# 卸载：bash init.sh --uninstall

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
SKILLS_DST="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"

echo "📦 仓库根目录: $REPO_ROOT"
echo "📍 目标 skills 目录: $SKILLS_DST"
echo

# ---- uninstall ----
if [ "$1" = "--uninstall" ]; then
  echo "🗑  卸载模式：移除本仓库的所有 skill"
  for d in "$SKILLS_SRC"/*/; do
    name=$(basename "$d")
    target="$SKILLS_DST/$name"
    if [ -d "$target" ]; then
      rm -rf "$target"
      echo "  - 已移除 $target"
    fi
  done
  echo "✅ 卸载完成"
  exit 0
fi

# ---- install ----
mkdir -p "$SKILLS_DST"

copied=0
skipped=0
for d in "$SKILLS_SRC"/*/; do
  name=$(basename "$d")
  target="$SKILLS_DST/$name"

  if [ -d "$target" ]; then
    echo "  ⚠️  $name 已存在，跳过（删掉再跑会覆盖）"
    skipped=$((skipped+1))
    continue
  fi

  cp -R "$d" "$target"
  echo "  ✅ 已安装 $name"
  copied=$((copied+1))
done

echo
echo "📊 统计：$copied 个新装，$skipped 个跳过"
echo

# ---- 关键文件校验 ----
echo "🔍 校验关键文件..."
problems=0

for f in README.md LICENSE 更新记录.md 书单数据源.md 书籍知识图谱模板.html scripts/rebuild_clean.py; do
  if [ ! -f "$REPO_ROOT/$f" ]; then
    echo "  ❌ 缺：$f"
    problems=$((problems+1))
  fi
done

# 公开示例卡片必须都在（当前开源版含 2 套：纳瓦尔宝典 + 国富论）
for book in guo-fu-lun na-wa-er-bao-dian; do
  if [ ! -d "$REPO_ROOT/cards/$book" ]; then
    echo "  ❌ 缺示例书：cards/$book"
    problems=$((problems+1))
  fi
done

if [ "$problems" -eq 0 ]; then
  echo "  ✅ 关键文件齐全"
else
  echo "  ⚠️  有 $problems 个缺失，请检查仓库完整性"
fi

echo
echo "🎉 初始化完成。下一步："
echo "  1. 打开 README.md 看「场景对话示例」段，把里面引号内容复制发给你的 AI 助手"
echo "  2. 打开 书单数据源.md 末尾看怎么改你的书单"
echo "  3. 双击 书籍知识图谱模板.html 预览演示图谱"
echo
echo "🗑  卸载：bash init.sh --uninstall"
