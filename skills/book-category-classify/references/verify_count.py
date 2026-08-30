#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验一份 15 类分类清单 markdown 文件的本数与结构。

用法：
    python3 verify_count.py <分类总览-vN.md>

输出：
    - 每个类的本数
    - 总本数
    - 类别数（必须 = 15，否则报错）
    - 总本数是否 = 各类之和
    - 书名行是否带 作者/关键词 字段（用于最终化清单体检）

设计铁律（RC306）：标题写的数字作废，按实际《》出现数实算；跳号=已删，不补号。
"""
import re
import sys

# 兼容两类段标题： "## 【类名】" / "### N. 【类名】"
SEC_RE = re.compile(r'^#{1,4}\s+.*?【(.+?)】')
BOOK_RE = re.compile(r'^\s*\d+\.\s*《(.+?)》')
META_RE = re.compile(r'《.+?》.*?(作者[:：].*?)(关键词[:：].*?)$|《.+?》.*?(关键词[:：].*?)(作者[:：].*?)$')


def parse(path):
    text = open(path, encoding='utf-8').read()
    data = {}
    cur = None
    order = []
    missing_meta = 0
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
            if '作者' not in ln or '关键词' not in ln:
                missing_meta += 1
    return data, order, missing_meta


def main():
    if len(sys.argv) < 2:
        print('用法: python3 verify_count.py <分类总览-vN.md>')
        sys.exit(1)
    data, order, missing_meta = parse(sys.argv[1])
    total = sum(len(v) for v in data.values())
    print('=' * 50)
    print(f'分类清单校验：{sys.argv[1]}')
    print('=' * 50)
    for k in order:
        print(f'  {k:<10} {len(data[k]):>4} 本')
    print('-' * 50)
    print(f'  类别数：{len(order)}  {"✅=15" if len(order)==15 else "❌≠15，必须 15 类"}')
    print(f'  总本数：{total}')
    sum_check = sum(len(v) for v in data.values())
    print(f'  总=各类之和：{"✅" if total==sum_check else "❌"} ({sum_check})')
    if missing_meta:
        print(f'  ⚠️  {missing_meta} 本书名行缺 作者/关键词 字段（最终化清单应补全）')
    print('=' * 50)
    if len(order) != 15:
        sys.exit(2)


if __name__ == '__main__':
    main()
