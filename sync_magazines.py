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
    从原始杂志标题行提取纯英文名、纯中文名和年份范围。
    例如：### 1、经济学人杂志历年电子版资源合集【1843年-2026年】 The Economist Full Year PDF Collection
    返回：{'english_name':'The Economist', 'chinese_name':'经济学人', 'start_year':1843, 'end_year':2026}
    """
    # 去掉开头的 "### " 和数字编号
    content = re.sub(r'^###\s*\d*[、.]?\s*', '', line.strip())
    
    # 提取年份区间（兼容有/无“年”字）
    year_match = re.search(r'【(\d{4})(?:年)?-(\d{4})(?:年)?】', content)
    if not year_match:
        return None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    # 去掉年份区间，剩下的字符串用于提取中英文名
    temp = re.sub(r'【.*?】', '', content).strip()
    
    # 提取英文名（通常是最后一段连续的英文、数字、&、空格）
    eng_match = re.search(r'([A-Za-z0-9 &]+?)(?:\s*Full Year PDF Collection)?$', temp)
    if eng_match:
        english_name = eng_match.group(1).strip()
    else:
        english_name = "Unknown"
    # 清理英文名末尾多余的 "Magazine" 等
    english_name = re.sub(r'\s+Magazine$', '', english_name, flags=re.I).strip()
    
    # 提取中文名（年份区间之前的部分，去掉英文和冗余词）
    before_year = content.split('【')[0]
    chinese_temp = re.sub(r'[A-Za-z0-9 &/]+', '', before_year)
    redundant = [
        '历年电子版资源合集', '电子版资源合集', 'PDF资源网盘合集',
        '英文杂志', '杂志历年电子版资源合集', '杂志电子版资源合集',
        '历年电子版PDF资源网盘合集', '资源网盘合集', '杂志'
    ]
    for word in redundant:
        chinese_temp = chinese_temp.replace(word, '')
    chinese_name = chinese_temp.strip()
    if not chinese_name:
        chinese_name = ''.join(re.findall(r'[\u4e00-\u9fa5]+', before_year))
    
    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'start_year': start_year,
        'end_year': end_year,
    }

def build_folder_name(info):
    """构造文件夹名：英文名+中文名+【起始年-结束年】"""
    folder = f"{info['english_name']}{info['chinese_name']}【{info['start_year']}-{info['end_year']}】"
    folder = re.sub(r'[\\/*?:"<>|]', '', folder)  # 移除非法字符
    folder = re.sub(r'\s+', ' ', folder).strip()  # 合并多余空格
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

def create_folder_and_md(info, base_dir):
    """为新增条目创建文件夹和目录.md文件（每行末尾加两个空格）"""
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

def add_link_to_line(original_line, info, base_dir):
    """为原始标题行生成带超链接的新行"""
    folder_name = build_folder_name(info)
    raw_path = f"./{folder_name}"
    encoded_path = encode_url_path(raw_path)
    title_text = original_line.strip()[4:]  # 去掉 "### "
    escaped_title = escape_markdown_link_text(title_text)
    return f"### [{escaped_title}]({encoded_path})\n"

def has_existing_link(line):
    """检查该行是否已经包含我们格式的超链接"""
    return '](./' in line

def get_existing_folders(base_dir):
    """返回根目录下所有合法杂志文件夹名集合（格式：...【数字-数字】）"""
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

    # 备份
    backup_path = readme_path + ".sync_bak"
    shutil.copy2(readme_path, backup_path)
    print(f"📁 已备份到: {backup_path}")

    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    existing_folders = get_existing_folders(base_dir)
    print(f"📁 已存在 {len(existing_folders)} 个杂志文件夹")

    new_lines = []
    entries_to_link = []  # (行号, 原始行, info)

    for idx, line in enumerate(lines):
        # 如果已经有超链接，直接保留
        if has_existing_link(line):
            new_lines.append(line)
            continue

        # 检查是否是杂志原始行（没有链接）
        if line.startswith('### ') and '【' in line and ('历年电子版资源合集' in line or 'full year pdf collection' in line.lower()):
            info = extract_magazine_info(line)
            if info:
                folder_name = build_folder_name(info)
                if folder_name not in existing_folders:
                    # 新增条目：创建文件夹和 md 文件
                    create_folder_and_md(info, base_dir)
                    entries_to_link.append((idx, line, info))
                    print(f"🆕 新增条目: {info['english_name']} / {info['chinese_name']} ({info['start_year']}-{info['end_year']})")
                else:
                    # 文件夹已存在但标题没有链接 -> 仅补充链接
                    print(f"⚠️ 文件夹已存在，补充链接: {folder_name}")
                    entries_to_link.append((idx, line, info))
            else:
                print(f"⚠️ 解析失败，保留原行: {line[:80]}")
            new_lines.append(line)
        else:
            new_lines.append(line)

    # 为需要添加链接的行替换为超链接版本
    for idx, original_line, info in entries_to_link:
        new_link_line = add_link_to_line(original_line, info, base_dir)
        new_lines[idx] = new_link_line
        print(f"🔗 添加超链接: {info['english_name']}")

    # 写回 README
    if new_lines != lines:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("✅ README.md 已更新")
    else:
        print("ℹ️ README.md 无需更新")

    print("✨ 增量同步完成！")

if __name__ == "__main__":
    sync_readme_and_folders(readme_path)
