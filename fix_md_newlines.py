import os
from pathlib import Path

def fix_md_files():
    """遍历所有一级子目录，修复其中的 .md 文件换行"""
    for folder in Path('.').iterdir():
        if not folder.is_dir():
            continue
        for md_file in folder.glob('*.md'):
            if md_file.name == 'README.md':
                continue
            content = md_file.read_text(encoding='utf-8')
            # 按行拆分（兼容所有换行符）
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                continue
            # 用 CRLF 重新连接
            fixed = '\r\n'.join(lines)
            if fixed != content:
                md_file.write_text(fixed, encoding='utf-8')
                print(f'Fixed: {md_file}')
            else:
                print(f'Already correct: {md_file}')

if __name__ == '__main__':
    fix_md_files()
