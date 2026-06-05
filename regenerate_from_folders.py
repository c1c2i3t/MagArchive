import re
from pathlib import Path

def extract_base_and_years(folder_name):
    """
    从文件夹名提取基础名和年份范围。
    例如：Scientific American科学美国人杂志历年电子版资源网盘合集杂志【1953-2026】
    返回：base_name = "Scientific American科学美国人杂志", start=1953, end=2026
    """
    # 找到“历年”的位置，取它之前的部分作为基础名
    if '历年' in folder_name:
        base_name = folder_name.split('历年')[0].strip()
    else:
        # 如果没有“历年”，则取【】之前的部分
        base_name = folder_name.split('【')[0].strip()
    # 提取年份区间
    year_match = re.search(r'【(\d{4})-(\d{4})】', folder_name)
    if not year_match:
        return None, None, None
    start_year = int(year_match.group(1))
    end_year = int(year_match.group(2))
    return base_name, start_year, end_year

def regenerate_md_files():
    root = Path('.')
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        if folder.name.startswith('.'):
            continue
        base_name, start, end = extract_base_and_years(folder.name)
        if base_name is None:
            print(f"Skipping {folder.name} (no year range)")
            continue
        # 生成逐年内容
        lines = []
        for year in range(start, end + 1):
            line = f"{base_name}{year}年电子版资源合集 {year} full year pdf collection"
            lines.append(line)
        # 写入 .md 文件（覆盖）
        md_path = folder / f"{folder.name}目录.md"
        md_path.write_text("\r\n".join(lines), encoding='utf-8')
        print(f"Regenerated: {md_path}")

if __name__ == "__main__":
    regenerate_md_files()
