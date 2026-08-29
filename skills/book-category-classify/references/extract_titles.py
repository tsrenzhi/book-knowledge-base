#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从当前磁盘的 分类总览-vN.md 抽取 15 类书名（自然继承用户所有删除），
打印 JSON，供生成 Vn+1 时作为骨架——绝不从记忆/旧数字补书。

用法：
    python3 extract_titles.py <分类总览-vN.md> [输出json路径]

输出：
    { "类名": ["《书名》", ...], ... }
设计铁律（RC306）：标题数字作废；跳号=已删，不补号；只抽当前文件实际《》。
"""
import re
import sys
import json

SEC_RE = re.compile(r'^#{1,4}\s+.*?【(.+?)】')
BOOK_RE = re.compile(r'^\s*\d+\.\s*《(.+?)》')


def extract(path):
    text = open(path, encoding='utf-8').read()
    data = {}
    cur = None
    order = []
    for ln in text.split('\n'):
        hm = SEC_RE.match(ln)
        if hm:
            cur = hm.group(1).strip()
            if cur not in data:
                data[cur] = []
                order.append(cur)
            continue
        bm = BOOK_RE.match(ln)
        if bm and cur:
            data[cur].append(bm.group(1))
    return data, order


def main():
    if len(sys.argv) < 2:
        print('用法: python3 extract_titles.py <分类总览-vN.md> [输出json]')
        sys.exit(1)
    data, order = extract(sys.argv[1])
    out = {k: data[k] for k in order}
    s = json.dumps(out, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        open(sys.argv[2], 'w', encoding='utf-8').write(s)
        print(f'已写 {sys.argv[2]}：{sum(len(v) for v in data.values())} 本 / {len(order)} 类')
    else:
        print(s)


if __name__ == '__main__':
    main()
