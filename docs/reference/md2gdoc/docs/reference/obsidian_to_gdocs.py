#!/usr/bin/env python3
"""
Полный экспорт из Obsidian в Google Docs с сохранением стилей
Использование: python obsidian_to_gdocs.py input.md output.docx
"""

import sys
import subprocess
import re
from pathlib import Path
from typing import Optional

# === КОНФИГУРАЦИЯ ===
CALLOUT_STYLES = {
    'note': {'emoji': '📝', 'title': 'Заметка', 'bg_color': '#E0F7FA', 'border_color': '#00BCD4'},
    'info': {'emoji': 'ℹ️', 'title': 'Информация', 'bg_color': '#E3F2FD', 'border_color': '#2196F3'},
    'important': {'emoji': '🔥', 'title': 'Важно', 'bg_color': '#D1ECF1', 'border_color': '#5BC0DE'},
    'tip': {'emoji': '💡', 'title': 'Совет', 'bg_color': '#E8F5E9', 'border_color': '#4CAF50'},
    'warning': {'emoji': '⚠️', 'title': 'Внимание', 'bg_color': '#FFF3E0', 'border_color': '#FF9800'},
    'danger': {'emoji': '⛔', 'title': 'Опасно', 'bg_color': '#FFEBEE', 'border_color': '#F44336'},
    'quote': {'emoji': '💬', 'title': 'Цитата', 'bg_color': '#F5F5F5', 'border_color': '#9E9E9E'},
}

def convert_callout_to_table(match):
    """Конвертирует каллаут Obsidian в HTML-таблицу для Word/Google Docs"""
    callout_type = match.group(1).lower()
    custom_title = match.group(2).strip()
    content = match.group(3)
    
    style = CALLOUT_STYLES.get(callout_type, CALLOUT_STYLES['note'])
    title = custom_title if custom_title else style['title']
    
    # Убираем > в начале строк
    content = re.sub(r'^> ?', '', content, flags=re.MULTILINE)
    
    # HTML-таблица с inline стилями (важно для Word/Docs)
    html = f'''<div style="border-left: 4px solid {style['border_color']}; background-color: {style['bg_color']}; padding: 12px; margin: 16px 0;">
<p style="margin: 0 0 8px 0; font-weight: bold;">
{style['emoji']} {title}
</p>
<div>
{content}
</div>
</div>

'''
    return html

def preprocess_markdown(content: str) -> str:
    """Предобработка markdown перед Pandoc"""
    
    # 1. Конвертируем каллауты
    callout_pattern = r'> \[!([a-zA-Z]+)\]\s*(.*?)\n((?:>.*(?:\n|$))+)'
    content = re.sub(callout_pattern, convert_callout_to_table, content, flags=re.MULTILINE)
    
    # 2. Конвертируем теги в бейджи
    def tag_to_badge(match):
        tag = match.group(1)
        return f'<span style="background-color: #E8EAF6; color: #5C6BC0; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; margin-right: 8px; display: inline-block;">#{tag}</span>'
    
    # Обрабатываем теги только в начале документа (первые строки)
    lines = content.split('\n')
    processed_lines = []
    in_frontmatter = False
    
    for i, line in enumerate(lines):
        # Пропускаем frontmatter
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
            
        # Обрабатываем теги в первых 5 строках после frontmatter
        if i < 10 and '#' in line and not line.startswith('#'):
            line = re.sub(r'#([а-яА-Яa-zA-Z0-9_-]+)', tag_to_badge, line)
        
        processed_lines.append(line)
    
    content = '\n'.join(processed_lines)
    
    # 3. Конвертируем внутренние ссылки [[link]] в обычные
    content = re.sub(r'\[\[([^\]|]+)(\|([^\]]+))?\]\]', r'[\3](\1)' if r'\3' else r'[\1]', content)
    
    return content

def run_pandoc(input_file: Path, output_file: Path, reference_doc: Optional[Path] = None):
    """Запускает Pandoc с нужными параметрами"""
    
    cmd = [
        'pandoc',
        str(input_file),
        '-o', str(output_file),
        '-f', 'markdown+raw_html',  # Важно! Разрешаем HTML в markdown
        '--wrap=none',
    ]
    
    # Добавляем reference.docx если есть
    if reference_doc and reference_doc.exists():
        cmd.extend(['--reference-doc', str(reference_doc)])
        print(f"📝 Используется шаблон: {reference_doc}")
    
    print(f"🔄 Запуск Pandoc...")
    print(f"   Команда: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Экспорт завершен: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Pandoc:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Pandoc не найден. Установите: https://pandoc.org/installing.html")
        return False

def main():
    if len(sys.argv) < 2:
        print("Использование: python obsidian_to_gdocs.py input.md [output.docx] [reference.docx]")
        print()
        print("Примеры:")
        print("  python obsidian_to_gdocs.py note.md")
        print("  python obsidian_to_gdocs.py note.md output.docx")
        print("  python obsidian_to_gdocs.py note.md output.docx reference.docx")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix('.docx')
    reference_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        sys.exit(1)
    
    print(f"📖 Чтение: {input_path}")
    
    # Читаем исходный файл
    content = input_path.read_text(encoding='utf-8')
    
    # Предобработка
    print("🔄 Обработка каллаутов и тегов...")
    processed = preprocess_markdown(content)
    
    # Сохраняем временный файл
    temp_file = input_path.with_stem(input_path.stem + '_temp')
    temp_file.write_text(processed, encoding='utf-8')
    print(f"💾 Временный файл: {temp_file}")
    
    # Запускаем Pandoc
    success = run_pandoc(temp_file, output_path, reference_path)
    
    # Удаляем временный файл
    temp_file.unlink()
    
    if success:
        print()
        print("=" * 60)
        print("✨ Готово!")
        print(f"📁 Результат: {output_path}")
        print()
        print("📤 Следующие шаги:")
        print("   1. Откройте файл в Word для проверки")
        print("   2. Загрузите на Google Drive")
        print("   3. Откройте через Google Docs")
        print("=" * 60)
    else:
        print("❌ Экспорт не удался")
        sys.exit(1)

if __name__ == '__main__':
    main()
