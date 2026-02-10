# Fix 422 Error: Request Models camelCase Migration (v0.59.1)

## Проблема
После миграции API на camelCase (v0.59.0) Request модели не принимают camelCase входные данные от фронтенда, так как наследуют от `BaseModel` вместо `CamelCaseModel`.

## Архитектурное обоснование

Это **правильное архитектурное решение**, а не заплатка:

1. **ADR 013** определяет единый контракт: Python (snake_case) ↔ JSON API (camelCase)
2. **Response модели уже используют CamelCaseModel** — Request модели были пропущены при миграции
3. **Pydantic best practice** — `populate_by_name=True` позволяет принимать оба формата для обратной совместимости
4. **Консистентность** — единый паттерн для всех API моделей (request + response)

## Решение
Изменить наследование всех Request моделей с `BaseModel` на `CamelCaseModel`.

## Файлы для изменения

### 1. backend/app/models/schemas.py

10 моделей:

| Модель | Строка | Изменение |
|--------|--------|-----------|
| ProcessRequest | 1012 | `BaseModel` → `CamelCaseModel` |
| StepParseRequest | 1033 | `BaseModel` → `CamelCaseModel` |
| StepCleanRequest | 1043 | `BaseModel` → `CamelCaseModel` |
| StepChunkRequest | 1058 | `BaseModel` → `CamelCaseModel` |
| StepLongreadRequest | 1071 | `BaseModel` → `CamelCaseModel` |
| StepSummarizeRequest | 1095 | `BaseModel` → `CamelCaseModel` |
| StepStoryRequest | 1115 | `BaseModel` → `CamelCaseModel` |
| StepSlidesRequest | 1138 | `BaseModel` → `CamelCaseModel` |
| StepSaveRequest | 1155 | `BaseModel` → `CamelCaseModel` |
| PromptOverrides | 1217 | `BaseModel` → `CamelCaseModel` |

### 2. backend/app/models/cache.py

1 модель:

| Модель | Строка | Изменение |
|--------|--------|-----------|
| RerunRequest | 262 | `BaseModel` → `CamelCaseModel` |

Также добавить импорт `CamelCaseModel` из schemas.py.

## Верификация

1. Проверка синтаксиса:
   ```bash
   python3 -m py_compile backend/app/models/schemas.py
   python3 -m py_compile backend/app/models/cache.py
   ```

2. Деплой и тест:
   ```bash
   ./scripts/deploy.sh
   ```

3. Проверка API:
   ```bash
   curl -s -X POST http://100.64.0.1:8801/api/step/parse \
     -H "Content-Type: application/json" \
     -d '{"videoFilename": "test.mp4"}'
   # Ожидается: валидный ответ (не 422)
   ```

4. UI тест: загрузить видео → нажать "Пошагово" → проверить что парсинг работает.

## Версия
Обновить в `frontend/package.json`: `"version": "0.59.1"`
