# Фаза 6: Инфраструктура промптов

> Цель: возможность менять промпты без деплоя — через SMB-доступ к папке на сервере

## Архитектурное решение: иерархическая структура

Промпты организуются по подпапкам этапов — и в проекте, и во внешней папке:

```
prompts/
├── cleaning/
│   ├── system.md
│   ├── system_gemma2.md      # model-specific
│   ├── user.md
│   └── user_gemma2.md
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

## Изменения

### 1. Реорганизовать `config/prompts/` в проекте

**Было:** `config/prompts/cleaner_system.md`
**Стало:** `config/prompts/cleaning/system.md`

Переименования:
| Было | Стало |
|------|-------|
| `cleaner_system.md` | `cleaning/system.md` |
| `cleaner_system_gemma2.md` | `cleaning/system_gemma2.md` |
| `cleaner_user.md` | `cleaning/user.md` |
| `cleaner_user_gemma2.md` | `cleaning/user_gemma2.md` |
| `longread_system.md` | `longread/system.md` |
| `longread_instructions.md` | `longread/instructions.md` |
| `longread_template.md` | `longread/template.md` |
| `longread_section.md` | `longread/section.md` |
| `longread_combine.md` | `longread/combine.md` |
| `summary_system.md` | `summary/system.md` |
| `summary_instructions.md` | `summary/instructions.md` |
| `summary_template.md` | `summary/template.md` |
| `story_system.md` | `story/system.md` |
| `story_instructions.md` | `story/instructions.md` |
| `story_template.md` | `story/template.md` |
| `map_outline.md` | `outline/map.md` |
| `summarizer.md` | (удалить — legacy) |

### 2. Settings — добавить `prompts_dir`

**Файл:** [backend/app/config.py](backend/app/config.py)

```python
class Settings(BaseSettings):
    # ... existing ...

    # External prompts directory (optional, overrides built-in)
    prompts_dir: Path | None = None
```

### 3. `load_prompt()` — новая сигнатура с подпапками

**Файл:** [backend/app/config.py](backend/app/config.py)

```python
def load_prompt(
    stage: str,           # "cleaning", "longread", "summary", "story", "outline"
    component: str,       # "system", "instructions", "template", "user", "map"
    model: str | None = None,
    settings: Settings | None = None
) -> str:
```

Порядок загрузки:
1. `prompts_dir/{stage}/{component}_{model_family}.md`
2. `prompts_dir/{stage}/{component}.md`
3. `config_dir/prompts/{stage}/{component}_{model_family}.md`
4. `config_dir/prompts/{stage}/{component}.md`

### 4. `load_glossary_text()` — вынести в config.py

**Файл:** [backend/app/config.py](backend/app/config.py)

```python
def load_glossary_text(settings: Settings | None = None) -> str:
    """Load glossary.yaml as text with external folder priority."""
```

Порядок:
1. `prompts_dir/glossary.yaml`
2. `config_dir/prompts/glossary.yaml`

### 5. Обновить все сервисы — новая сигнатура

**Файлы:**
- [backend/app/services/cleaner.py](backend/app/services/cleaner.py)
- [backend/app/services/longread_generator.py](backend/app/services/longread_generator.py)
- [backend/app/services/summary_generator.py](backend/app/services/summary_generator.py)
- [backend/app/services/story_generator.py](backend/app/services/story_generator.py)
- [backend/app/services/outline_extractor.py](backend/app/services/outline_extractor.py)

Пример изменения в cleaner.py:
```python
# Было:
self.system_prompt = load_prompt("cleaner_system", model, settings)
self.user_template = load_prompt("cleaner_user", model, settings)

# Стало:
self.system_prompt = load_prompt("cleaning", "system", model, settings)
self.user_template = load_prompt("cleaning", "user", model, settings)
```

### 6. `docker-compose.yml` — добавить volume

**Файл:** [docker-compose.yml](docker-compose.yml)

```yaml
volumes:
  - /mnt/main/work/bz2/video/prompts:/data/prompts:ro
environment:
  - PROMPTS_DIR=/data/prompts
```

### 7. Создать папку на сервере

```bash
mkdir -p /mnt/main/work/bz2/video/prompts/{cleaning,longread,summary,story,outline}
```

Скопировать промпты в иерархическую структуру.

### 8. Документация

**Документы для обновления:**

| Документ | Что добавить |
|----------|--------------|
| [docs/configuration.md](docs/configuration.md) | Новая секция "Внешние промпты" с описанием механизма приоритета |
| [CLAUDE.md](CLAUDE.md) | Обновить структуру промптов, добавить PROMPTS_DIR |
| [docs/research/pipeline-optimization-for-rag.md](docs/research/pipeline-optimization-for-rag.md) | Обновить статус Фазы 6 на "реализовано" |
| [docs/adr/](docs/adr/) | ADR-007: External prompts infrastructure (новый) |

## Механизм приоритета загрузки

**Ключевой принцип:** внешняя папка полностью отдельна от образа и не затрагивается при деплое.

```
┌─────────────────────────────────────────────────────────┐
│                    load_prompt()                         │
├─────────────────────────────────────────────────────────┤
│  1. Проверить prompts_dir/{stage}/{component}.md        │
│     └─ Есть? → Использовать                             │
│                                                          │
│  2. Fallback: config_dir/prompts/{stage}/{component}.md │
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

**Преимущества:**
- Эксперименты не теряются при деплое
- Можно откатить к встроенному (удалить файл из внешней папки)
- Чёткое разделение: встроенные = проверенные, внешние = эксперименты

## Файлы для изменения

### Код

| Файл | Изменение |
|------|-----------|
| `config/prompts/` | Реорганизация в подпапки |
| [backend/app/config.py](backend/app/config.py) | `prompts_dir`, `load_prompt(stage, component)`, `load_glossary_text()` |
| [backend/app/services/cleaner.py](backend/app/services/cleaner.py) | Новая сигнатура `load_prompt()`, использовать `load_glossary_text()` |
| [backend/app/services/longread_generator.py](backend/app/services/longread_generator.py) | Новая сигнатура |
| [backend/app/services/summary_generator.py](backend/app/services/summary_generator.py) | Новая сигнатура |
| [backend/app/services/story_generator.py](backend/app/services/story_generator.py) | Новая сигнатура |
| [backend/app/services/outline_extractor.py](backend/app/services/outline_extractor.py) | Новая сигнатура |
| [docker-compose.yml](docker-compose.yml) | Volume + env var |

### Документация

| Документ | Изменение |
|----------|-----------|
| [docs/configuration.md](docs/configuration.md) | Новая секция "Внешние промпты" |
| [CLAUDE.md](CLAUDE.md) | Обновить структуру промптов, PROMPTS_DIR |
| [docs/research/pipeline-optimization-for-rag.md](docs/research/pipeline-optimization-for-rag.md) | Статус Фазы 6 → реализовано |
| [docs/adr/007-external-prompts.md](docs/adr/007-external-prompts.md) | Новый ADR |

## Тестирование

1. **Локальный тест** — unit test для `load_prompt()` с temporary directory
2. **После деплоя:**
   - `docker exec bz2-transcriber ls -la /data/prompts/`
   - Изменить промпт через SMB → запустить обработку → проверить результат

## Версия

После успешной реализации: обновить версию в [frontend/package.json](frontend/package.json) до **v0.30**
