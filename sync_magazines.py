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
    从杂志标题行提取信息。
    行示例：
    ### 1、经济学人杂志历年电子版资源合集【1843年-2026年】 The Economist Full Year PDF Collection
    ### 26、航空力量月刊杂志历年电子版资源网盘合集【1988年-2026年】 Air Forces Monthly Full Year PDF Collection
    """
    # 1) 提取年份区间（第一个匹配的区间，且支持有无“年”字）
    year_pattern = r'【(\d{4})(?:年)?-(\d{4})(?:年)?】'
    year_match = re.search(year_pattern, line)
    if not year_match:
        return None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    if start_year > end_year:
        start_year, end_year = end_year, start_year

    # 2) 移除开头的 "### " 和数字编号（例如 "### 1、"）
    content = re.sub(r'^###\s*\d+[、.]\s*', '', line.strip())

    # 3) 分离年份区间之前的部分（中文部分）和之后的部分（英文部分）
    # 找到第一个 '【' 的位置，其前面的内容为中文名（含冗余词）
    parts_before_year = content.split('【')[0]  # "经济学人杂志历年电子版资源合集"
    # 找到最后一个 '】' 的位置，其后面的内容为英文名（含冗余词）
    parts_after_year = content.split('】')[-1].strip()  # "The Economist Full Year PDF Collection"

    # 4) 清理中文名：移除常见的冗余后缀
    chinese_raw = parts_before_year.strip()
    redundant_chinese = [
        '历年电子版资源合集', '电子版资源合集', 'PDF资源网盘合集',
        '英文杂志', '杂志历年电子版资源合集', '杂志电子版资源合集',
        '历年电子版PDF资源网盘合集', '资源网盘合集'
    ]
    for word in redundant_chinese:
        chinese_raw = chinese_raw.replace(word, '')
    # 进一步去除可能残留的“杂志”末尾，但保留“杂志”如果它是名称一部分？多数情况下要去掉
    chinese_raw = re.sub(r'杂志$', '', chinese_raw).strip()
    # 如果中文名为空，则尝试提取所有中文字符
    if not chinese_raw:
        chinese_raw = ''.join(re.findall(r'[\u4e00-\u9fa5]+', parts_before_year))
    chinese_name = chinese_raw

    # 5) 清理英文名：移除常见的冗余后缀
    english_raw = parts_after_year
    redundant_english = [
        'Full Year PDF Collection', 'PDF Collection', 'Collection',
        'Full Year', 'Magazine', 'Magazine$'
    ]
    for word in redundant_english:
        english_raw = re.sub(r'\s*' + re.escape(word) + r'\s*', ' ', english_raw, flags=re.I)
    english_raw = english_raw.strip()
    # 只提取连续的英文单词、数字、&、空格（取第一部分）
    eng_match = re.match(r'^([A-Za-z0-9 &]+)', english_raw)
    if eng_match:
        english_name = eng_match.group(1).strip()
    else:
        # 降级：取整个清理后的字符串
        english_name = english_raw
    # 去掉末尾可能的杂志后缀
    english_name = re.sub(r'\s+Magazine$', '', english_name, flags=re.I).strip()
    # 如果英文名为空，则尝试从原标题中提取
    if not english_name:
        fallback = re.search(r'([A-Za-z][A-Za-z\s&]+?)(?:【|$)', content)
        if fallback:
            english_name = fallback.group(1).strip()
        else:
            english_name = "Unknown"

    return {
        'chinese_name': chinese_name,
        'english_name': english_name,
        'start_year': start_year,
        'end_year': end_year,
    }

def build_folder_name(info):
    """构造文件夹名：英文名+中文名+【起始年-结束年】"""
    folder = f"{info['english_name']}{info['chinese_name']}【{info['start_year']}-{info['end_year']}】"
    # 移除非法文件名字符
    folder = re.sub(r'[\\/*?:"<>|]', '', folder)
    # 合并多个空格为一个空格
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
    # 如果文件夹存在但名字异常（比如包含冗余词），可以删除重新创建？为避免风险，此处不自动删除。
    folder_path.mkdir(parents=True, exist_ok=True)
    md_path = folder_path / f"{folder_name}目录.md"
    # 检查并生成/修复内容
    need_write = True
    if md_path.exists():
        content = md_path.read_text(encoding='utf-8')
        # 如果内容已经包含正确的换行且条目数正确，可跳过，但为了安全我们总是重新生成
        # 为简单起见，总是重新生成（因为已修复格式）
        need_write = True
    if need_write:
        lines = [f"{info['chinese_name']}{year}年电子版资源合集 {info['english_name']} {year} full year pdf collection"
                 for year in range(info['start_year'], info['end_year'] + 1)]
        # 使用 CRLF 换行保证 GitHub Markdown 正确渲染
        md_path.write_text("\r\n".join(lines), encoding='utf-8')
        print(f"生成/更新目录文件: {md_path}")
    return True

def add_link_to_title(line, info, base_dir):
    if re.search(r'\]\(\./', line):
        return line
    folder_name = build_folder_name(info)
    raw_path = f"./{folder_name}"
    encoded_path = encode_url_path(raw_path)
    original_title = line.strip()[4:]  # 去掉 "### "
    escaped_title = escape_markdown_link_text(original_title)
    return f"### [{escaped_title}]({encoded_path})\n"

def sync_readme_and_folders(readme_path):
    if not os.path.exists(readme_path):
        raise FileNotFoundError(f"文件不存在: {readme_path}")
    base_dir = Path(readme_path).parent
    # 备份
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
                print(f"处理条目: {info['english_name']} / {info['chinese_name']} ({info['start_year']}-{info['end_year']})")
            else:
                print(f"警告：解析失败，保留原行: {line[:80]}")
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("同步完成！")

if __name__ == "__main__":
    sync_readme_and_folders(readme_path)
