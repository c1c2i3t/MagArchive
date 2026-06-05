import os
import re
from pathlib import Path

def fix_md_newlines():
    root = Path('.')
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        for md_file in folder.glob('*.md'):
            if md_file.name == 'README.md':
                continue
            content = md_file.read_text(encoding='utf-8')
            lines = [line.rstrip() for line in content.splitlines() if line.strip()]
            if not lines:
                continue
            fixed_lines = []
            for line in lines:
                # 方法一 (推荐): 行末加两个空格 → 适用于标准Markdown渲染
                fixed_line = line + '  '
                fixed_lines.append(fixed_line)
                # 方法二 (备选): 行末加HTML换行标签, 将上面这行换成下面的, 或者两者都保留
                # fixed_line = line + ' <br>'
            new_content = '\n'.join(fixed_lines)
            if new_content != content:
                md_file.write_text(new_content, encoding='utf-8')
                print(f'Fixed: {md_file}')
            else:
                print(f'Already correct: {md_file}')

if __name__ == '__main__':
    fix_md_newlines()
