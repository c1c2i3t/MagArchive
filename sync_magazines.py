#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote

readme_path = "README.md"

def extract_magazine_info(line):
    year_pattern = r'【(\d{4})(?:年)?-(\d{4})(?:年)?】'
    year_match = re.search(year_pattern, line)
    if not year_match:
        return None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    if start_year > end_year:
        start_year, end_year = end_year, start_year
    content = line.strip()
    content = re.sub(r'^###\s*\d+[、.]\s*', '', content)
    prefix = content.split('【')[0]
    chinese_temp = re.sub(r'[a-zA-Z\s/\\&]+', '', prefix)
    redundant = [
        '历年电子版资源合集', '电子版资源合集', 'PDF资源网盘合集',
        '英文杂志', '杂志历年电子版资源合集', '杂志电子版资源合集',
        '历年电子版PDF资源网盘合集'
    ]
    for rep in redundant:
        chinese_temp = chinese_temp.replace(rep, '')
    chinese_name = chinese_temp.strip()
    if not chinese_name:
        chinese_name = ''.join(re.findall(r'[\u4e00-\u9fa5]+', prefix))
    parts = content.split('】')
    after_year = parts[-1].strip() if len(parts) >= 2 else ""
    after_year = re.sub(r'\s*(Full Year PDF Collection|PDF Collection|Collection|Full Year|Magazine)$', '', after_year, flags=re.I)
    eng_match = re.match(r'^([A-Za-z0-9 &]+)', after_year)
    if eng_match:
        english_name = eng_match.group(1).strip()
    else:
        eng_fallback = re.search(r'([A-Za-z][A-Za-z\s&]+?)(?:【|$)', content)
        english_name = eng_fallback.group(1).strip() if eng_fallback else "Unknown"
    english_name = re.sub(r'\s*(Magazine)$', '', english_name, flags=re.I).strip()
    english_name = re.sub(r'杂志$', '', english_name).strip()
    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'start_year': start_year,
        'end_year': end_year,
    }

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
    md_path = folder_path / f"{folder_name}目录.md"
    # 检查是否需要生成/重新生成（如果文件不存在，或内容没有换行则重新生成）
    need_regenerate = False
    if md_path.exists():
        content = md_path.read_text(encoding='utf-8')
        # 正常文件应该每行一条记录，至少有两行，且包含换行符
        if '\n' not in content or len(content.splitlines()) < 2:
            need_regenerate = True
    else:
        need_regenerate = True
    if need_regenerate:
        lines = [f"{info['chinese_name']}{year}年电子版资源合集 {info['english_name']} {year} full year pdf collection"
                 for year in range(info['start_year'], info['end_year'] + 1)]
        md_path.write_text("\n".join(lines), encoding='utf-8')
        print(f"生成/修复目录文件: {md_path}")
        created = True
    return created

def add_link_to_title(line, info, base_dir):
    if re.search(r'\]\(\./', line):
        return line
    folder_name = build_folder_name(info)
    raw_path = f"./{folder_name}"
    encoded_path = encode_url_path(raw_path)
    original_title = line.strip()[4:]
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
        if line.startswith('### ') and '历年电子版资源合集' in line and '【' in line:
            info = extract_magazine_info(line)
            if info:
                ensure_folder_and_md(info, base_dir)
                new_line = add_link_to_title(line, info, base_dir)
                new_lines.append(new_line)
                print(f"处理条目: {info['english_name']} {info['chinese_name']}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("同步完成！")

if __name__ == "__main__":
    sync_readme_and_folders(readme_path)
