#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote

readme_path = "README.md"

def extract_magazine_info(line):
    """
    从杂志标题行提取中英文名、起止年份。
    兼容两种格式：
      1. 原始格式：### 1、经济学人杂志...【1843-2026】 The Economist...
      2. 超链接格式：### [1、经济学人杂志...【1843-2026】 The Economist...](./文件夹)
    """
    # 去除行首的 "### " 和可能的编号
    content = line.strip()
    content = re.sub(r'^###\s*', '', content)

    # 检测是否为 Markdown 链接格式： [文本](链接)
    link_match = re.match(r'^\[(.*?)\]\(.*?\)$', content)
    if link_match:
        # 如果是链接格式，提取方括号内的原始文本
        content = link_match.group(1)
    else:
        # 否则去除开头的数字编号（如 "1、"）
        content = re.sub(r'^\d+[、.]\s*', '', content)

    # 提取年份区间（第一个匹配的区间，支持有无“年”字）
    year_pattern = r'【(\d{4})(?:年)?-(\d{4})(?:年)?】'
    year_match = re.search(year_pattern, content)
    if not year_match:
        return None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    # 分割中文名和英文名：年份区间之前的部分为中文名（含冗余词），之后的部分为英文名
    parts = content.split('】')
    if len(parts) < 2:
        return None
    before_year = parts[0]               # 例如 "经济学人杂志历年电子版资源合集"
    after_year = parts[1].strip()        # 例如 "The Economist Full Year PDF Collection"

    # 清理中文名：移除常见冗余词
    chinese_raw = before_year
    redundant_chinese = [
        '历年电子版资源合集', '电子版资源合集', 'PDF资源网盘合集',
        '英文杂志', '杂志历年电子版资源合集', '杂志电子版资源合集',
        '历年电子版PDF资源网盘合集', '资源网盘合集'
    ]
    for word in redundant_chinese:
        chinese_raw = chinese_raw.replace(word, '')
    chinese_raw = re.sub(r'杂志$', '', chinese_raw).strip()
    if not chinese_raw:
        chinese_raw = ''.join(re.findall(r'[\u4e00-\u9fa5]+', before_year))
    chinese_name = chinese_raw

    # 清理英文名：移除常见冗余词，只保留主要英文名
    english_raw = after_year
    redundant_english = [
        'Full Year PDF Collection', 'PDF Collection', 'Collection',
        'Full Year', 'Magazine'
    ]
    for word in redundant_english:
        english_raw = re.sub(r'\s*' + re.escape(word) + r'\s*', ' ', english_raw, flags=re.I)
    english_raw = english_raw.strip()
    eng_match = re.match(r'^([A-Za-z0-9 &]+)', english_raw)
    if eng_match:
        english_name = eng_match.group(1).strip()
    else:
        english_name = "Unknown"
    english_name = re.sub(r'\s+Magazine$', '', english_name, flags=re.I).strip()

    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'start_year': start_year,
        'end_year': end_year,
    }

# ================== 以下函数保持不变 ==================
def build_folder_name(info):
    folder = f"{info['english_name']}{info['chinese_name']}【{info['start_year']}-{info['end_year']}】"
    folder = re.sub(r'[\\/*?:"<>|]', '', folder)
    folder = re.sub(r'\s+', ' ', folder).strip()
    return folder

def encode_url_path(path):
    if path.startswith('./'):
        prefix = './'
        rest = path[2:]
    else:
        prefix = ''
        rest = path
    encoded_rest = quote(rest, safe='/')
    return prefix + encoded_rest

def escape_markdown_link_text(text):
    return text.replace('[', r'\[').replace(']', r'\]')

def ensure_folder_and_md(info, base_dir):
    folder_name = build_folder_name(info)
    folder_path = base_dir / folder_name
    created = False
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        created = True
        print(f"新建文件夹: {folder_name}")
    else:
        print(f"文件夹已存在，跳过: {folder_name}")

    md_path = folder_path / f"{folder_name}目录.md"
    if not md_path.exists():
        lines = []
        for year in range(info['start_year'], info['end_year'] + 1):
            line = f"{info['chinese_name']}{year}年电子版资源合集 {info['english_name']} {year} full year pdf collection"
            line_with_spaces = line + '  '
            lines.append(line_with_spaces)
        md_path.write_text("\n".join(lines), encoding='utf-8')
        print(f"生成目录文件: {md_path}")
        created = True
    else:
        print(f"目录文件已存在，跳过: {md_path}")
    return created

def add_link_to_title(line, info, base_dir):
    if re.search(r'\]\(\./', line):
        return line
    folder_name = build_folder_name(info)
    raw_path = f"./{folder_name}"
    encoded_path = encode_url_path(raw_path)
    # 注意：此时 line 是原始行（可能没有链接），我们需要提取原始标题文本
    original_title = line.strip()[4:]  # 去掉 "### "
    escaped_title = escape_markdown_link_text(original_title)
    return f"### [{escaped_title}]({encoded_path})\n"

def sync_readme_and_folders(readme_path):
    if not os.path.exists(readme_path):
        raise FileNotFoundError(f"文件不存在: {readme_path}")
    base_dir = Path(readme_path).parent

    backup_path = readme_path + ".sync_bak"
    shutil.copy2(readme_path, backup_path)
    print(f"已备份到: {backup_path}")

    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith('### ') and '【' in line and ('历年电子版资源合集' in line or 'full year pdf collection' in line.lower()):
            info = extract_magazine_info(line)
            if info:
                ensure_folder_and_md(info, base_dir)
                new_line = add_link_to_title(line, info, base_dir)
                new_lines.append(new_line)
                print(f"处理条目: {info['english_name']} / {info['chinese_name']} ({info['start_year']}-{info['end_year']})")
            else:
                print(f"警告：解析失败，保留原行: {line[:80]}")
                new_lines.append(line)
        else:
            new_lines.append(line)

    if new_lines != lines:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("README.md 已更新（添加了缺失的超链接）")
    else:
        print("README.md 无需更新")

    print("同步完成！")

if __name__ == "__main__":
    sync_readme_and_folders(readme_path)
