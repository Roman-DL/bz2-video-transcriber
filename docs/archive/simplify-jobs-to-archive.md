# RFC: Упрощение архитектуры — удаление системы задач

> **Статус:** ✅ Completed
> **Автор:** Claude + Roman
> **Дата:** 2026-01-10

---

## Мотивация

Текущая система задач (Jobs) добавляет сложность без существенной пользы:

1. **Параллельная обработка не нужна** — делит ресурсы сервера, замедляет работу
2. **In-memory storage** — задачи теряются при каждом деплое
3. **Избыточный UI** — модальное окно + панель задач дублируют информацию
4. **Сложность поддержки** — WebSocket, JobManager, множество компонентов

---

## Предлагаемые изменения

### 1. Удаление системы задач ✅

### 2. Унификация режимов обработки

Два режима с **разными целями**:

| Режим | Назначение | Возможности |
|-------|------------|-------------|
| **Step-by-step** | Отладка промптов | Просмотр результатов каждого шага, повтор отдельных шагов |
| **Auto-run** | Продакшн | Только прогресс, автоматическое выполнение всех шагов |

**Auto-run** — упрощённый UI:
- Показывает только прогресс (без промежуточных результатов)
- Шаги запускаются автоматически один за другим
- Нет возможности повтора шагов (не нужно — всё отлажено)
- Модальное окно незакрываемое до завершения/отмены

### 3. Замена панели задач на каталог архива

**Новый компонент:** `ArchiveCatalog`

**Функционал (минимальный MVP):**
- Показывает иерархию папок архива (год → мероприятие → тема)
- Отражает реальную структуру `archive/`
- Позволяет открыть файлы (summary.md, transcript)
- Главная цель: увидеть, что появилась новая папка после обработки

**Не реализуем в MVP:**
- Поиск
- Удаление
- Статистика

**API эндпоинт:**
```
GET /api/archive — возвращает дерево папок архива
```

---

## Этапы реализации

### Этап 1: Удаление системы задач ✅ ЗАВЕРШЁН

**Удалённые файлы (backend):**
- [x] `backend/app/services/job_manager.py`
- [x] `backend/app/api/websocket.py`

**Удалённые файлы (frontend):**
- [x] `frontend/src/api/websocket.ts`
- [x] `frontend/src/api/hooks/useJobs.ts`
- [x] `frontend/src/api/hooks/useProcess.ts`
- [x] `frontend/src/components/jobs/JobList.tsx`
- [x] `frontend/src/components/jobs/JobCard.tsx`
- [x] `frontend/src/components/processing/FullPipeline.tsx`

**Упрощённые файлы:**
- [x] `backend/app/main.py` — убран WebSocket роутер
- [x] `backend/app/api/__init__.py` — убран websocket импорт
- [x] `backend/app/api/routes.py` — только `/api/inbox`
- [x] `frontend/src/App.tsx` — убрана панель задач
- [x] `frontend/src/components/processing/ProcessingModal.tsx` — только step-by-step
- [x] `frontend/src/api/types.ts` — убраны ProcessingJob, ProcessingResult, ProgressMessage, ProcessRequest, ProcessingStatus, STATUS_LABELS
- [x] `frontend/src/components/common/Badge.tsx` — убран StatusBadge

---

### Этап 2: Auto-run режим ✅ ЗАВЕРШЁН

**Изменённые файлы:**
- [x] `frontend/src/components/common/Modal.tsx` — добавлен prop `closable`
- [x] `frontend/src/components/processing/StepByStep.tsx` — добавлен prop `autoRun`, useEffect для авто-запуска, условный UI
- [x] `frontend/src/components/processing/ProcessingModal.tsx` — экран выбора режима (Пошагово / Автоматически)

---

### Этап 3: Каталог архива ✅ ЗАВЕРШЁН

**Изменённые файлы:**
- [x] `backend/app/api/routes.py` — добавлен эндпоинт `GET /api/archive`
- [x] `frontend/src/api/types.ts` — добавлены типы `ArchiveItem`, `ArchiveResponse`
- [x] `frontend/src/api/hooks/useArchive.ts` — новый hook
- [x] `frontend/src/components/archive/ArchiveCatalog.tsx` — новый компонент
- [x] `frontend/src/App.tsx` — интеграция ArchiveCatalog

---

### Этап 4: Документация

**Задачи:**
- [ ] Обновить `docs/architecture.md`
- [ ] Обновить `docs/web-ui.md`
- [ ] Обновить `CLAUDE.md`
- [ ] Переместить RFC в `docs/archive/`

---

## Текущее состояние

| Метрика | До | Сейчас | Цель |
|---------|-----|--------|------|
| Файлы системы задач | ~12 | 0 | 0 ✅ |
| Протоколы реального времени | WebSocket + SSE | Только SSE | Только SSE ✅ |
| Компоненты обработки | 2 | 1 (step-by-step + auto-run) | 1 ✅ |
| Главная страница | Inbox + Tasks | Inbox + Archive | Inbox + Archive ✅ |
