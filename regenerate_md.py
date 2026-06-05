import re
from pathlib import Path

def parse_folder_name(folder_name):
    """从文件夹名提取英文名、中文名、起始年、结束年"""
    # 匹配模式：英文名 中文名 【起始年-结束年】
    # 例如：Reader读者文摘英文版杂志【1928-2026】
    pattern = r'^([A-Za-z0-9 &]+?)([^【]+?)【(\d{4})-(\d{4})】$'
    match = re.match(pattern, folder_name)
    if not match:
        return None
    english_name = match.group(1).strip()
    chinese_name = match.group(2).strip()
    start_year = int(match.group(3))
    end_year = int(match.group(4))
    return english_name, chinese_name, start_year, end_year

def regenerate_md_files():
    root = Path('.')
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        parsed = parse_folder_name(folder.name)
        if not parsed:
            print(f"Skipping {folder.name} (doesn't match pattern)")
            continue
        english_name, chinese_name, start_year, end_year = parsed
        # 生成逐年内容
        lines = []
        for year in range(start_year, end_year + 1):
            line = f"{chinese_name}{year}年电子版资源合集 {english_name} {year} full year pdf collection"
            lines.append(line)
        # 写入 .md 文件（覆盖）
        md_path = folder / f"{folder.name}目录.md"
        md_path.write_text("\r\n".join(lines), encoding='utf-8')
        print(f"Regenerated: {md_path}")

if __name__ == "__main__":
    regenerate_md_files()
