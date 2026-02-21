# Рефакторинг: единый источник правды для default моделей

## Контекст

Default модели дублируются в 4+ местах: `config.py`, `docker-compose.yml`, `slides_extractor.py`, `models.yaml`, документация. При переключении конспекта на Opus (ADR-019) обновили `config.py`, но забыли `docker-compose.yml` — Pydantic `BaseSettings` приоритет env > Python default → UI показывал Sonnet вместо Opus. Та же проблема была с `CLEANER_MODEL`.

**Цель:** единый источник default моделей в `config.py`, убрать все дубли.

## Решение: Вариант A — убрать дубли, оставить defaults только в `config.py`

Pydantic `BaseSettings` поддерживает env override из коробки. Если не задавать env var → используется Python default. Если нужно переопределить для тестирования → добавить env var в docker-compose или `.env`.

## Шаги реализации

### 1. `backend/app/config.py` — добавить `slides_model`
- Добавить поле `slides_model: str = "claude-haiku-4-5"` (строка ~22)
- Slides default переезжает из хардкода `slides_extractor.py` в единую систему Settings

### 2. `docker-compose.yml` — убрать дублирующие model env vars
- Удалить строки 19-20 (`SUMMARIZER_MODEL=...`, `CLEANER_MODEL=...`)
- Добавить комментарий-подсказку: `# Model defaults: backend/app/config.py. Override: SUMMARIZER_MODEL, CLEANER_MODEL, etc.`

### 3. `backend/app/services/slides_extractor.py` — убрать хардкод
- Удалить константу `DEFAULT_SLIDES_MODEL = "claude-haiku-4-5"` (строка 31)
- Строка 100: `model = model or DEFAULT_SLIDES_MODEL` → `model = model or self.settings.slides_model`

### 4. `backend/app/models/schemas.py` — добавить `slides` в `DefaultModelsResponse`
- Добавить поле `slides: str` в `DefaultModelsResponse` (строка 1346)

### 5. `backend/app/api/models_routes.py` — вернуть slides в API
- Добавить `slides=settings.slides_model` в `DefaultModelsResponse(...)`

### 6. `backend/app/services/pipeline/config_resolver.py` — добавить slides_model
- Добавить `"slides_model": self.settings.slides_model` и `"describe_model": self.settings.describe_model` в `settings_dict` (строка 71-88)
- Добавить `"slides": "slides_model"` в `field_map` (строка 106-110)
- Обновить `StageType` Literal (строка 14)
- Обновить `get_model_for_stage` (строка 123-127)

### 7. `frontend/src/api/types.ts` — добавить `slides`
- Добавить `slides: string;` в `DefaultModelsResponse` (строка 449)

### 8. `config/models.yaml` — комментарий
- Строка 41: добавить комментарий `# NOTE: actual default in backend/app/config.py (Settings.slides_model)`

### 9. Документация
- `docs/configuration.md` — добавить `SLIDES_MODEL`, `DESCRIBE_MODEL` в таблицу env vars
- `.claude/rules/ai-clients.md` — добавить правило "Все defaults в config.py, docker-compose НЕ содержит model env vars"
- Предложить ADR-020

## Файлы для изменения

| Файл | Что меняется |
|------|-------------|
| `backend/app/config.py:18-22` | +slides_model |
| `docker-compose.yml:19-20` | -SUMMARIZER_MODEL, -CLEANER_MODEL, +комментарий |
| `backend/app/services/slides_extractor.py:31,100` | -DEFAULT_SLIDES_MODEL, →settings.slides_model |
| `backend/app/models/schemas.py:1339-1347` | +slides field |
| `backend/app/api/models_routes.py` | +slides в response |
| `backend/app/services/pipeline/config_resolver.py:14,71-88,106-110,123-128` | +slides_model, +describe_model |
| `frontend/src/api/types.ts:444-450` | +slides field |
| `config/models.yaml:41` | +комментарий |
| `docs/configuration.md` | +SLIDES_MODEL, +DESCRIBE_MODEL |
| `.claude/rules/ai-clients.md` | +правило единого источника |

## Верификация

1. `python3 -m py_compile backend/app/config.py` — синтаксис
2. `python3 -m py_compile backend/app/services/slides_extractor.py` — синтаксис
3. `python3 -m py_compile backend/app/services/pipeline/config_resolver.py` — синтаксис
4. `/bin/bash scripts/deploy.sh` — деплой и проверка через UI что defaults корректны
5. `curl https://transcriber.home/api/models/default` — проверить что slides есть в ответе
