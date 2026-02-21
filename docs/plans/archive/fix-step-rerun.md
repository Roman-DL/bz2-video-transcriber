# Исправление перезапуска шага в пошаговом режиме

## Контекст

При нажатии кнопки "Перезапустить" в пошаговом режиме, данные шага сбрасываются (`resetDataFromStep`), но `currentStep` **не возвращается** к перезапускаемому шагу. В результате:

1. CTA кнопка продолжает показывать **следующий** шаг
2. Вкладка с результатом очищается — пользователь видит пустой экран
3. Перезапуск фактически не происходит

Дополнительно: в интерфейсе две кнопки перезапуска (круговая стрелка без подписи + "Перезапустить"), что избыточно.

## Решение

### 1. Вернуть `currentStep` при сбросе данных

**Файл:** `frontend/src/hooks/usePipelineProcessor.ts`

В `resetDataFromStep` (строка 367) добавить `setCurrentStep(step)`:

```typescript
  setError(null);
  setCurrentStep(step);  // ← ДОБАВИТЬ
}, [pipelineSteps]);
```

### 2. Убрать дублирующую кнопку RefreshCw из строки шага

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

- Удалить блок с кнопкой RefreshCw (строки 497-507) — оставить только "Перезапустить" в панели настроек
- Расширить `hasSettings` — показывать не только для `isCurrent` (activeTab + completed), а для всех завершённых LLM-шагов, чтобы пользователь мог перезапустить любой пройденный шаг

### 3. ADR-017: Перезапуск шагов с настройками

**Файл:** `docs/decisions/017-step-rerun-with-overrides.md`

Документирует архитектуру перезапуска:

- **Два механизма перезапуска:**
  1. **Step-by-Step UI** (используется) — `resetDataFromStep()` + `runStep()` через обычный `/api/step/{stage}` с `modelOverrides` и `promptOverrides`
  2. **Cache API** (`/api/cache/rerun`) — предусмотрен для будущего архивного режима, сохраняет версию в `.cache/`

- **Выбор модели** — `ModelSelector` → `modelOverrides[step]` → `getModelForStage()` → передаётся в API

- **Выбор промпта** — `ComponentPromptSelector` → `promptOverrides[step]` → `getPromptOverridesForApi()` → передаётся в API. Селектор виден когда `variants.length > 1`. Варианты промптов сканируются API из двух директорий:
  1. `PROMPTS_DIR/{stage}/` — внешние (приоритет), см. ADR-008
  2. `config_dir/prompts/{stage}/` — встроенные

- **Как добавить вариант промпта:** положить файл `{component}_v2.md` в `/mnt/main/work/bz2/video/prompts/{stage}/` — UI автоматически покажет селектор

## Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `frontend/src/hooks/usePipelineProcessor.ts` | +1 строка: `setCurrentStep(step)` |
| `frontend/src/components/processing/StepByStep.tsx` | Убрать RefreshCw, расширить hasSettings |
| `docs/decisions/017-step-rerun-with-overrides.md` | **Новый** ADR |
| `docs/decisions/README.md` | Добавить ссылку на ADR-017 |

## Проверка

1. Выполнить пошаговую обработку до шага "Генерация лонгрида"
2. Нажать "Настройки" у шага лонгрида → сменить модель → "Перезапустить"
3. **Ожидаемое:** CTA показывает "Генерация лонгрида", таб пуст
4. Нажать "Выполнить" — лонгрид генерируется с новой моделью
5. Проверить перезапуск шага "Очистка" — настройки доступны для завершённого шага
