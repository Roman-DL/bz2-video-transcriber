# ADR-020: Единый источник default моделей

**Статус:** Принято
**Дата:** 2026-02-22

## Контекст

Default модели дублировались в 4+ местах: `config.py`, `docker-compose.yml`, `slides_extractor.py`, `models.yaml`, документация. При переключении конспекта на Opus (ADR-019) обновили `config.py`, но забыли `docker-compose.yml` — Pydantic `BaseSettings` приоритет env > Python default → UI показывал Sonnet вместо Opus. Та же проблема была с `CLEANER_MODEL`.

**Корень проблемы:** Pydantic BaseSettings берёт значение из env var (docker-compose.yml) с приоритетом над Python default (config.py). Дублирование в docker-compose создаёт скрытый конфликт при обновлении defaults.

## Решение

1. **Единый источник defaults:** `backend/app/config.py` → `Settings`
2. **docker-compose.yml НЕ содержит model env vars** — Pydantic Settings использует Python defaults
3. **Все сервисы** получают default через `settings.{stage}_model`, без локальных констант
4. **Добавлен `slides_model`** в Settings — ранее хардкодился в `slides_extractor.py`
5. **Переопределение при необходимости** — через env var в docker-compose или `.env`

### Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `backend/app/config.py` | +`slides_model` |
| `docker-compose.yml` | -`SUMMARIZER_MODEL`, -`CLEANER_MODEL`, +комментарий |
| `backend/app/services/slides_extractor.py` | -`DEFAULT_SLIDES_MODEL`, →`settings.slides_model` |
| `backend/app/models/schemas.py` | +`slides` в `DefaultModelsResponse` |
| `backend/app/api/models_routes.py` | +`slides` в response |
| `backend/app/services/pipeline/config_resolver.py` | +`slides_model`, +`describe_model` |
| `frontend/src/api/types.ts` | +`slides` в `DefaultModelsResponse` |

## Последствия

### Положительные
- Обновление default модели — одно место (`config.py`), нет рассинхронизации
- Переопределение через env по-прежнему работает (Pydantic BaseSettings)
- API `/api/models/default` теперь возвращает slides default

### Отрицательные
- При чтении docker-compose.yml не видно какие модели используются (нужно смотреть config.py)

## Альтернативы

### 1. Оставить дубли в docker-compose + добавить CI проверку
- ✗ Дублирование неизбежно ведёт к рассинхрону
- ✗ CI проверка — дополнительная сложность
- ✓ Видно модели прямо в docker-compose

### 2. Вынести defaults в models.yaml
- ✗ Pydantic Settings не читает YAML — нужен дополнительный код загрузки
- ✗ Env override станет нетривиальным
- ✓ Все модели в одном YAML

## Справочные материалы

- [ADR-007](007-remove-fallback-use-claude.md) — Claude default
- [ADR-014](014-haiku-default-cleaning.md) — Haiku default для очистки
- [ADR-018](018-opus-default-longread.md) — Opus default для лонгрида
- [ADR-019](019-opus-default-summary.md) — Opus default для конспекта
