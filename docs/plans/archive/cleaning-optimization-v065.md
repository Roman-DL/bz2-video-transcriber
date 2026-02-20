# План: Оптимизация очистки транскриптов (v0.65)

## Контекст

Очистка — самый дорогой этап pipeline по токенам. Текущие пороги чанкования профиля `large` (100K символов) фактически отключают разбиение для Claude. Часовая запись (43K символов) потребляет ~180K input tokens из 200K контекста, а записи >1 часа — не помещаются. Глоссарий (34KB ≈ 77K токенов) отправляется целиком с каждым запросом.

**Цель:** корректные пороги чанкования + семантический глоссарий + причёсывание текста + Haiku вместо Sonnet для очистки. Результат: поддержка любой длительности, ~3.2x дешевле.

**Требования:** [docs/requirements/cleaning-optimization.md](../requirements/cleaning-optimization.md)

---

## Pre-flight: совместимость с архитектурой

**Вписывается полностью.** Все изменения — конфигурация и промпты, без изменений в архитектуре.

- Глоссарий загружается как raw text (`load_glossary_text()`) → изменение формата YAML не требует кода
- Чанкование уже реализовано в `TranscriptCleaner` → нужно только обновить пороги в `config/models.yaml`
- Промпты внешние (`config/prompts/`) → меняются без пересборки
- ADR-007 (Claude default) — Haiku валидная модель Claude, конфликта нет
- ADR-008 (External prompts) — формат промптов не меняется

**Rules проверены:** `pipeline.md` (chunk — детерминистический для H2, но clean stage — LLM-based chunking, это другое), `ai-clients.md` (без fallback), `infrastructure.md` (structured logging).

---

## Этап 1: Глоссарий — семантический формат + `people`

**Файл:** [config/glossary.yaml](../../config/glossary.yaml)

Полная замена содержимого. Версия 4.0.

### Принципы конвертации терминов (79 шт)

Для каждого термина:
- `english` → включить в `description`, поле убрать
- `variations` → `whisper_errors` (только неочевидные):
  - **Убрать:** lowercase canonical, английские формы, очевидные производные
  - **Оставить:** аббревиатуры (СВ, ГЕТ), фонетические искажения (скпервайзер), склейки (ворлдтим)
- `description` → расширить: числовые критерии, все сокращения (рус + англ), произношение аббревиатур
- `context` — оставить где есть, не добавлять принудительно

### Новый раздел `people`

~10 записей ключевых лидеров и амбассадоров (из requirements, секция 4):
- Марк Хьюз, Стефан Грациани, Джим Рон, Алан Лоренц, Джон Тартол и др.
- Для имён `whisper_errors` заполняется щедро — каждый реально встреченный вариант

**Целевой размер:** ~15KB термины + ~3KB люди = ~18KB (было 34KB)

---

## Этап 2: Промпт очистки — ЗАДАЧА 3 + новый формат глоссария

**Файл:** [config/prompts/cleaning/system.md](../../config/prompts/cleaning/system.md)

### Изменения

1. Заголовок: "Три задачи" вместо "Две задачи"
2. **ЗАДАЧА 2** — обновить описание полей глоссария:
   - `variations` → `whisper_errors` (только неочевидные ошибки транскрибации)
   - Добавить описание раздела `people` и инструкции по исправлению имён
   - Акцент: распознавать по `description` и смыслу, `whisper_errors` — подсказки для сложных случаев
3. **ЗАДАЧА 3** (новая) — причёсывание:
   - Технический шум: проверка микрофона, счёт, рассадка → удалить
   - Дословные повторы подряд → оставить один раз
   - Заикания: "сейчас, сейчас, сейчас" → "сейчас"
   - Обрывки с перезапуском фразы → удалить оборванную часть
4. КРИТИЧЕСКИ ВАЖНО п.1: `85-95%` → `80-95%` (задача 3 даёт больше редукции)
5. Обновить пример: добавить дубль, исправление имени, удаление тех. шума

**Файл `user.md` — без изменений** (шаблон `{glossary}` + `{transcript}` остаётся).

---

## Этап 3: Пороги чанкования

**Файл:** [config/models.yaml](../../config/models.yaml) — строки 101-107

```yaml
# БЫЛО:
cleaner:
  chunk_size: 100000
  chunk_overlap: 10000
  small_text_threshold: 150000

# СТАНЕТ:
cleaner:
  # Russian: ~2.3 tok/char. Target 70% of 200K = 140K tokens.
  # Overhead after glossary v4.0: ~49K tokens (system + glossary + people).
  # Max chunk: (140K - 49K) / 2.3 ≈ 40K chars.
  chunk_size: 40000
  chunk_overlap: 3000
  small_text_threshold: 40000
```

---

## Этап 4: Код cleaner.py — лог токенов + smoke test

**Файл:** [backend/app/services/cleaner.py](../../backend/app/services/cleaner.py)

### 4a. Лог estimated tokens (перед LLM вызовом, внутри цикла чанков)

Добавить после строки 106 (`if len(chunks) > 1:`), новый блок логирования для каждого чанка с оценкой токенов:

```python
# Estimate tokens (Russian: ~2.3 tok/char)
est_chunk_tokens = int(len(chunk) * 2.3)
est_total_tokens = est_chunk_tokens + int(len(self.glossary_text) * 2.3) + 7000  # +7K for system prompt
logger.info(
    f"Chunk {i + 1}/{len(chunks)}: {len(chunk):,} chars, "
    f"~{est_total_tokens:,} est. input tokens ({est_total_tokens * 100 // 200_000}% of 200K)"
)
```

### 4b. Smoke test — строка 414

```python
# БЫЛО:
assert "variations:" in cleaner.glossary_text, "Missing variations field"
# СТАНЕТ:
assert "canonical:" in cleaner.glossary_text, "Missing canonical field in glossary"
```

> Используем `canonical:` вместо `whisper_errors:` — canonical есть у каждого термина, а whisper_errors может отсутствовать.

---

## Этап 5: Default модель → Haiku

**Файл:** [backend/app/config.py](../../backend/app/config.py) — строка 20

```python
# БЫЛО:
cleaner_model: str = "claude-sonnet-4-6"  # Model for transcript cleaning
# СТАНЕТ:
cleaner_model: str = "claude-haiku-4-5"  # Model for transcript cleaning (v0.65: Haiku default)
```

> Пользователь может override через ENV `CLEANER_MODEL=claude-sonnet-4-6` или через UI.

---

## Этап 6: Обновление документации

### 6a. `docs/pipeline/03-clean.md`
- Обновить диаграмму: `(claude-sonnet)` → `(claude-haiku)`
- Обновить таблицу параметров: chunk_size 40000, overlap 3000, threshold 40000
- Обновить секцию "Глоссарий как контекст LLM": новый формат (description + whisper_errors)
- Добавить: ЗАДАЧА 3 (причёсывание)
- Обновить ожидаемые показатели: reduction 15-25% (было 5-20%) из-за задачи 3

### 6b. `CLAUDE.md` — текущий статус
- Добавить строку v0.65: "Оптимизация очистки: семантический глоссарий, Haiku default, chunk 40K"

### 6c. ADR-014: Haiku default для очистки (опционально)
- Создать `docs/decisions/014-haiku-default-cleaning.md`
- Контекст: механическая задача, Haiku и Sonnet дают одинаковый результат, 3x дешевле

---

## Разбивка на фазы (2 отдельные беседы)

### Фаза 1: Глоссарий v4.0 (отдельная беседа)

Самый большой объём работы — конвертация 79 терминов + создание раздела `people`.

**Scope:** Этап 1 (glossary.yaml)

**Коммит:** `feat: глоссарий v4.0 — семантический формат + раздел people`

### Фаза 2: Промпт + пороги + код + модель + docs (отдельная беседа)

Всё остальное — изменения небольшие, но взаимосвязанные.

**Scope:** Этапы 2-6 (system.md, models.yaml, cleaner.py, config.py, docs)

**Коммит:** `feat: оптимизация очистки — задача 3, Haiku default, chunk 40K (v0.65)`

---

## Потенциальные риски

| Риск | Митигация |
|------|-----------|
| Задача 3 увеличивает reduction → fallback на строке 171 (>40%) | Порог 40% достаточен: задача 3 даёт +5-10%, итого 15-25%. Мониторить логи |
| Merge chunks: задача 3 удаляет предложения в overlap зоне | `chunk_overlap: 3000` — достаточно запаса. Тестировать на часовой записи |
| Haiku хуже справляется с причёсыванием | Requirements doc подтверждает: Sonnet и Haiku дали одинаковый результат. Fallback через ENV |

---

## Верификация

```bash
# 1. Smoke test (локально, без LLM)
cd backend && python3 -m py_compile app/services/cleaner.py
python3 -c "from app.config import load_glossary_text; g = load_glossary_text(); print(f'{len(g)} chars'); assert 'canonical:' in g"

# 2. Деплой на сервер
./scripts/deploy.sh

# 3. Тест на реальном транскрипте (через Web UI)
# - Загрузить часовую запись
# - Выбрать Haiku для очистки (или оставить default)
# - Проверить: 2 чанка, estimated tokens в логах, reduction 15-25%
# - Проверить: имена исправлены (Mark Hughes → Марк Хьюз)
# - Проверить: технический шум удалён, дубли убраны
# - Проверить: стоимость ≤$0.30

# 4. Логи на сервере
source .env.local
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "sudo docker logs bz2-transcriber --tail 100 | grep -E 'est\. input tokens|Chunk|reduction'"
```

---

## Файлы для изменения (сводка)

| Файл | Тип изменения |
|------|---------------|
| `config/glossary.yaml` | Полная замена — semantic v4.0 + people |
| `config/prompts/cleaning/system.md` | Полная замена — 3 задачи + новый формат |
| `config/models.yaml` | Правка 3 строк — пороги large.cleaner |
| `backend/app/services/cleaner.py` | Добавление ~5 строк (лог) + правка 1 строки (smoke test) |
| `backend/app/config.py` | Правка 1 строки — default cleaner_model |
| `docs/pipeline/03-clean.md` | Обновление — параметры, формат, задача 3 |
| `CLAUDE.md` | Правка 1 строки — текущий статус v0.65 |
| `docs/decisions/014-haiku-default-cleaning.md` | Новый файл (опционально) |
