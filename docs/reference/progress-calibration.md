# Калибровка прогресса обработки

Справочник по настройке коэффициентов оценки времени выполнения этапов pipeline.

---

## Текущие коэффициенты (v2)

Файл: `config/performance.yaml`

| Этап | factor | base_time | Формула |
|------|--------|-----------|---------|
| transcribe | 0.29 / video_sec | 5.0 | `5 + duration * 0.29` |
| clean | 0.9 / 1k chars | 2.0 | `2 + chars/1000 * 0.9` |
| chunk | 4.0 / 1k chars | 2.0 | `2 + chars/1000 * 4.0` |
| summarize | 3.0 / 1k chars | 3.0 | `3 + chars/1000 * 3.0` |

### Пример расчёта

Для 5-минутного видео (301 сек, 4535 символов транскрипции):

```
transcribe: 5 + 301 * 0.29 = 92.3 сек (реально ~87 сек) → 94%
clean:      2 + 4.5 * 0.9  = 6.0 сек  (реально ~6 сек)  → 100%
chunk:      2 + 1.3 * 4.0  = 7.2 сек  (реально ~7 сек)  → 97%
summarize:  3 + 1.3 * 3.0  = 6.9 сек  (реально ~7 сек)  → 99%
```

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

### Причины изменения v1 → v2

Тест Step-by-Step показал что коэффициенты v1 были завышены:

| Этап | Прогресс при завершении | Ошибка | Корректировка |
|------|-------------------------|--------|---------------|
| clean | 49% | 2x завышен | 1.8 → 0.9 |
| chunk | 70% | 1.4x завышен | 6.0 → 4.0 |
| summarize | 37% | 2.7x завышен | 10.0 → 3.0 |

После v2 прогресс достигает 90-95% при завершении этапов.

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
