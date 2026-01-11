# Калибровка прогресса обработки

Справочник по настройке коэффициентов оценки времени выполнения этапов pipeline.

---

## Текущие коэффициенты (v4)

Файл: `config/performance.yaml`

| Этап | factor | base_time | Формула |
|------|--------|-----------|---------|
| transcribe | 0.06 / video_sec | 5.0 | `5 + duration * 0.06` |
| clean | 1.2 / 1k chars | 2.0 | `2 + chars/1000 * 1.2` |
| chunk | 2.9 / 1k chars | 2.0 | `2 + chars/1000 * 2.9` |
| summarize | 0.9 / 1k chars | 3.0 | `3 + chars/1000 * 0.9` |

### Пример расчёта

Для 55-минутного видео (3308 сек, 47233 символов транскрипции, 20939 после очистки):

```
transcribe: 5 + 3308 * 0.06 = 203.5 сек (реально ~199 сек) → 98%
clean:      2 + 47.2 * 1.2  = 58.6 сек  (реально ~59 сек)  → 101%
chunk:      2 + 20.9 * 2.9  = 62.6 сек  (реально ~63 сек)  → 101%
summarize:  3 + 20.9 * 0.9  = 21.8 сек  (реально ~22 сек)  → 101%
```

### Отображение ETA (v0.7.0+)

Начиная с версии 0.7.0 в UI отображается примерное оставшееся время:

```
32%                                 ~2 мин 30 сек
```

SSE события теперь включают `estimated_seconds` и `elapsed_seconds` для расчёта ETA на клиенте.

---

## Инструкция по калибровке

### Когда калибровать

- После изменения модели LLM (другой размер, другой provider)
- После изменения модели Whisper
- Если прогресс систематически завершается раньше/позже 100%
- При переходе на другое оборудование

### Шаги калибровки

**1. Подготовить тестовые файлы**

Рекомендуется использовать файлы разной длительности:
- Короткий: 2-3 минуты
- Средний: 5-10 минут
- Длинный: 30+ минут

**2. Запустить обработку**

```bash
# Через Web UI или API
curl -X POST http://localhost:8801/api/process \
  -H "Content-Type: application/json" \
  -d '{"video_filename": "test-file.mp4"}'
```

**3. Получить PERF логи**

```bash
# На сервере
docker logs bz2-transcriber | grep "PERF |"

# Пример вывода:
PERF | transcribe | size=50.3MB | duration=301s | time=87.0s
PERF | clean | input_chars=4535 | output_chars=1335 | time=6.0s
PERF | chunk | input_chars=1335 | chunks=6 | time=7.4s
PERF | summarize | input_chars=1335 | time=7.1s
```

**4. Рассчитать новые коэффициенты**

```python
# transcribe
factor = time / duration  # 87.0 / 301 = 0.289

# clean/chunk/summarize
factor = time / (input_chars / 1000)  # 6.0 / 4.535 = 1.32
```

**5. Обновить performance.yaml**

```yaml
# config/performance.yaml
version: 3
updated: "2026-XX-XX"
notes: "Описание изменений"

transcribe:
  factor_per_video_second: 0.29
  base_time: 5.0

clean:
  factor_per_1k_chars: 1.3  # Новое значение
  base_time: 2.0
```

**6. Задеплоить и проверить**

```bash
./scripts/deploy.sh

# Проверить прогресс в UI или через логи
docker logs bz2-transcriber | grep "Ticker"
```

---

## История калибровок

| Версия | Дата | Тест файл | Изменения |
|--------|------|-----------|-----------|
| v1 | 2026-01-09 | 5 мин (Full Pipeline) | Начальные значения: clean=1.8, chunk=6.0, summarize=10.0 |
| v2 | 2026-01-10 | 5 мин (Step-by-Step) | clean 1.8→0.9, chunk 6.0→4.0, summarize 10.0→3.0 |
| v3 | 2026-01-11 | 55 мин (Step-by-Step) | transcribe 0.29→0.08, clean 0.9→1.4, chunk 4.0→3.2, summarize 3.0→1.2 |
| v4 | 2026-01-12 | 55 мин (Step-by-Step) | transcribe 0.08→0.06, clean 1.4→1.2, chunk 3.2→2.9, summarize 1.2→0.9 |

### Причины изменения v3 → v4

v3 использовал запас 20-30% что приводило к раннему завершению прогресса:

| Этап | Прогресс при завершении | Ratio | Корректировка |
|------|-------------------------|-------|---------------|
| transcribe | 74% (~70сек осталось) | 0.74 | 0.08 → 0.06 |
| clean | 85% (~9сек осталось) | 0.87 | 1.4 → 1.2 |
| chunk | 91% (~6сек осталось) | 0.91 | 3.2 → 2.9 |
| summarize | 75% (~7сек осталось) | 0.78 | 1.2 → 0.9 |

После v4 прогресс достигает 95-100% при завершении этапов (точная оценка).

### Причины изменения v2 → v3

Тест на длинном 55-минутном видео показал существенные отклонения:

| Этап | Прогресс при завершении | Ошибка | Корректировка |
|------|-------------------------|--------|---------------|
| transcribe | 20.5% | 4.8x завышен | 0.29 → 0.08 |
| clean | 95% (застрял 14.5s) | 1.3x занижен | 0.9 → 1.4 |
| chunk | 70% | 1.4x завышен | 4.0 → 3.2 |
| summarize | 33% | 2.9x завышен | 3.0 → 1.2 |

v3 использовал запас 20-30% для безопасности.

### Причины изменения v1 → v2

Тест Step-by-Step на 5-минутном видео показал что коэффициенты v1 были завышены:

| Этап | Прогресс при завершении | Ошибка | Корректировка |
|------|-------------------------|--------|---------------|
| clean | 49% | 2x завышен | 1.8 → 0.9 |
| chunk | 70% | 1.4x завышен | 6.0 → 4.0 |
| summarize | 37% | 2.7x завышен | 10.0 → 3.0 |

---

## Команды отладки

```bash
# PERF логи (реальное время выполнения)
docker logs bz2-transcriber | grep "PERF |"

# Ticker логи (обновления прогресса)
docker logs bz2-transcriber | grep "Ticker"

# Все логи в реальном времени
docker logs -f bz2-transcriber

# Проверить ffprobe (для длительности видео)
docker exec bz2-transcriber ffprobe -version

# SSH доступ на сервер
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "docker logs bz2-transcriber | grep 'PERF'"
```

---

## Связанные документы

- [Pipeline Orchestrator](../pipeline/07-orchestrator.md#progressestimator) — архитектура ProgressEstimator
- [Pipeline API](../pipeline/08-api.md) — SSE прогресс для Step-by-Step
- [config/performance.yaml](../../config/performance.yaml) — конфигурация коэффициентов
