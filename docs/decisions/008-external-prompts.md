---
doc_type: adr
status: accepted
created: 2025-01-21
updated: 2026-01-24
audience: [developer]
tags:
  - architecture
  - adr
  - llm
---

# ADR-008: Внешние промпты с приоритетом загрузки

## Статус

Принято (2025-01-21)

## Контекст

Промпты для LLM требуют частой итерации для улучшения качества результатов.
Текущий подход с промптами внутри Docker-образа имеет проблемы:

1. **Медленная итерация** — для изменения промпта нужен redeploy
2. **Потеря экспериментов** — при каждом деплое промпты перезаписываются
3. **Нет A/B тестирования** — невозможно быстро сравнить разные версии
4. **Неудобное редактирование** — промпты нельзя редактировать через SMB

## Решение

### Иерархическая структура промптов

Реорганизовать плоскую структуру `config/prompts/` в иерархическую:

```
prompts/
├── cleaning/
│   ├── system.md             # default
│   ├── system_v2.md          # вариант (опционально)
│   └── user.md
├── longread/
│   ├── system.md
│   ├── instructions.md
│   ├── template.md
│   ├── section.md
│   └── combine.md
├── summary/
│   ├── system.md
│   ├── instructions.md
│   └── template.md
├── story/
│   ├── system.md
│   ├── instructions.md
│   └── template.md
├── outline/
│   └── map.md
└── glossary.yaml
```

### Новая сигнатура load_prompt() (v0.31+)

```python
def load_prompt(
    stage: str,           # "cleaning", "longread", "summary", "story", "outline"
    name: str,            # "system", "system_v2", "instructions", "template", "user", "map"
    settings: Settings | None = None
) -> str:
```

### Приоритет загрузки (первый найденный)

1. `prompts_dir/{stage}/{name}.md` (внешняя папка)
2. `config_dir/prompts/{stage}/{name}.md` (встроенная)

### Конфигурация

```python
class Settings(BaseSettings):
    prompts_dir: Path | None = None  # External prompts directory
```

```yaml
# docker-compose.yml
volumes:
  - /mnt/main/work/bz2/video/prompts:/data/prompts:ro
environment:
  - PROMPTS_DIR=/data/prompts
```

## Механизм работы

```
┌─────────────────────────────────────────────────────────┐
│                    load_prompt()                         │
├─────────────────────────────────────────────────────────┤
│  1. Проверить prompts_dir/{stage}/{name}.md             │
│     └─ Есть? → Использовать                             │
│                                                          │
│  2. Fallback: config_dir/prompts/{stage}/{name}.md      │
│     └─ Использовать встроенный из образа                │
└─────────────────────────────────────────────────────────┘
```

**При деплое:**
- `docker build` → встроенные промпты в образе **обновляются**
- `/mnt/.../prompts/` (внешняя папка) → **не затрагивается**

**Workflow эксперимента:**
1. Начальное состояние: внешняя папка пустая → используются встроенные
2. Хочу изменить `cleaning/system.md`:
   - Копирую из образа во внешнюю папку
   - Редактирую через SMB
3. Система использует версию из внешней папки
4. Деплой нового кода → встроенный обновился, мой во внешней папке остался

## Преимущества

1. **Быстрая итерация** — изменения без деплоя
2. **Сохранение экспериментов** — внешние промпты переживают деплой
3. **Простой откат** — удалить файл из внешней папки → используется встроенный
4. **SMB доступ** — редактирование через файловый менеджер

## Изменённые файлы

### Код

| Файл | Изменение |
|------|-----------|
| `config/prompts/` | Реорганизация в подпапки |
| `backend/app/config.py` | `prompts_dir`, `load_prompt(stage, component)`, `load_glossary_text()` |
| `backend/app/services/cleaner.py` | Новая сигнатура `load_prompt()` |
| `backend/app/services/longread_generator.py` | Новая сигнатура |
| `backend/app/services/summary_generator.py` | Новая сигнатура |
| `backend/app/services/story_generator.py` | Новая сигнатура |
| `backend/app/services/outline_extractor.py` | Новая сигнатура |
| `docker-compose.yml` | Volume + env var |

### Документация

- `docs/configuration.md` — секция "Внешние промпты"
- `CLAUDE.md` — обновлённая структура промптов

## Альтернативы

### 1. Hot-reload промптов при изменении файла

Отклонено: избыточная сложность, риск race conditions.

### 2. Промпты в базе данных

Отклонено: overhead, потеря version control для промптов.

### 3. Environment variables для промптов

Отклонено: неудобно для многострочных текстов.

## Следствия

- Функция `load_prompt()` получает breaking change в сигнатуре
- Все сервисы требуют обновления вызовов
- При первом деплое нужно создать папку на сервере (будет пустой)
