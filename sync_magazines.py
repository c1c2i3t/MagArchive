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
    content = line.strip()
    # 去掉开头的 "### " 和可能的前导空格
    content = re.sub(r'^###\s*', '', content)

    # 如果是超链接格式，提取方括号内的内容
    link_match = re.match(r'^\[(.*?)\]\(.*?\)$', content)
    if link_match:
        content = link_match.group(1)
    else:
        # 去掉数字编号，如 "1、" 或 "1."
        content = re.sub(r'^\d+[、.]\s*', '', content)

    # 提取年份区间：支持有无“年”字，取第一个【...】
    year_pattern = r'【(\d{4})(?:年)?-(\d{4})(?:年)?】'
    year_match = re.search(year_pattern, content)
    if not year_match:
        return None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    # 分割中文名和英文名：以最后一个】为界
    parts = content.split('】')
    if len(parts) < 2:
        return None
    before_year = parts[0]   # 年份区间之前的部分（中文部分）
    after_year = parts[-1].strip()  # 最后一个】之后的部分（英文部分）

    # 清理中文名：去除常见冗余后缀
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

    # 清理英文名
    english_raw = after_year
    redundant_english = [
        'Full Year PDF Collection', 'PDF Collection', 'Collection',
        'Full Year', 'Magazine'
    ]
    for word in redundant_english:
        english_raw = re.sub(r'\s*' + re.escape(word) + r'\s*', ' ', english_raw, flags=re.I)
    english_raw = english_raw.strip()
    # 提取连续的英文、数字、&
    eng_match = re.match(r'^([A-Za-z0-9 &]+)', english_raw)
    if eng_match:
        english_name = eng_match.group(1).strip()
    else:
        english_name = english_raw
    english_name = re.sub(r'\s+Magazine$', '', english_name, flags=re.I).strip()

    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'start_year': start_year,
        'end_year': end_year,
    }

def build_folder_name(info):
    """根据杂志信息构造文件夹名"""
    folder = f"{info['english_name']}{info['chinese_name']}【{info['start_year']}-{info['end_year']}】"
    folder = re.sub(r'[\\/*?:"<>|]', '', folder)  # 移除非法字符
    folder = re.sub(r'\s+', ' ', folder).strip()  # 合并多余空格
    return folder

def encode_url_path(path):
    """对URL路径进行编码（空格->%20）"""
    if path.startswith('./'):
        prefix = './'
        rest = path[2:]
    else:
        prefix = ''
        rest = path
    encoded_rest = quote(rest, safe='/')
    return prefix + encoded_rest

def escape_markdown_link_text(text):
    """转义Markdown链接文本中的方括号"""
    return text.replace('[', r'\[').replace(']', r'\]')

def create_folder_and_md(info, base_dir):
    """为新增条目创建文件夹和目录.md文件（仅当不存在时）"""
    folder_name = build_folder_name(info)
    folder_path = base_dir / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ 新建文件夹: {folder_name}")

    md_path = folder_path / f"{folder_name}目录.md"
    lines = []
    for year in range(info['start_year'], info['end_year'] + 1):
        line = f"{info['chinese_name']}{year}年电子版资源合集 {info['english_name']} {year} full year pdf collection  "
        lines.append(line)
    md_path.write_text("\n".join(lines), encoding='utf-8')
    print(f"✅ 生成目录文件: {md_path}")

def add_link_to_line(line, info, base_dir):
    """为给定的原始标题行生成带超链接的新行"""
    folder_name = build_folder_name(info)
    raw_path = f"./{folder_name}"
    encoded_path = encode_url_path(raw_path)
    original_title = line.strip()[4:]  # 去掉开头的 "### "
    escaped_title = escape_markdown_link_text(original_title)
    return f"### [{escaped_title}]({encoded_path})\n"

def get_existing_folders(base_dir):
    """返回根目录下所有符合命名规范的文件夹名集合"""
    pattern = re.compile(r'.+【\d{4}-\d{4}】$')
    existing = set()
    for item in base_dir.iterdir():
        if item.is_dir() and pattern.match(item.name):
            existing.add(item.name)
    return existing

def sync_readme_and_folders(readme_path):
    if not os.path.exists(readme_path):
        raise FileNotFoundError(f"文件不存在: {readme_path}")
    base_dir = Path(readme_path).parent

    # 备份原文件
    backup_path = readme_path + ".sync_bak"
    shutil.copy2(readme_path, backup_path)
    print(f"📁 已备份到: {backup_path}")

    # 读取 README 所有行
    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 解析所有杂志条目，生成目标信息列表
    target_entries = []  # 每个元素为 (行号, 原始行, info)
    for idx, line in enumerate(lines):
        if line.startswith('### ') and '【' in line and ('历年电子版资源合集' in line or 'full year pdf collection' in line.lower()):
            info = extract_magazine_info(line)
            if info:
                target_entries.append((idx, line, info))
            else:
                print(f"⚠️ 警告：解析失败，行 {idx+1}: {line[:80]}")

    # 获取已存在的合法文件夹
    existing_folders = get_existing_folders(base_dir)
    print(f"📁 已存在 {len(existing_folders)} 个杂志文件夹")

    # 找出新增的条目（其文件夹名不在 existing_folders 中）
    new_entries = []
    for idx, line, info in target_entries:
        folder_name = build_folder_name(info)
        if folder_name not in existing_folders:
            new_entries.append((idx, line, info))
            print(f"🆕 新增条目: {info['english_name']} / {info['chinese_name']} ({info['start_year']}-{info['end_year']})")
        else:
            print(f"⏭️ 已存在，跳过: {folder_name}")

    if not new_entries:
        print("🎉 没有新增条目，无需操作。")
        return

    # 只处理新增条目：创建文件夹和 md 文件，并更新 README 中对应行的超链接
    new_lines = lines.copy()
    for idx, line, info in new_entries:
        create_folder_and_md(info, base_dir)
        new_line = add_link_to_line(line, info, base_dir)
        new_lines[idx] = new_line

    # 写回 README（仅当有变化）
    if new_lines != lines:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("✅ README.md 已更新（为新增条目添加超链接）")
    else:
        print("ℹ️ README.md 无需更新")

    print("✨ 增量同步完成！")

if __name__ == "__main__":
    sync_readme_and_folders(readme_path)
