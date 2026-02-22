# Этап 2: API changelog + UI страница /changelog

## Контекст

Этап 1 версионирования (v0.80) выполнен: VERSION файл, Commitizen, version.py, HealthResponse, BUILD_NUMBER, deploy. Этап 2 добавляет пользовательскую видимость: endpoint для отдачи CHANGELOG.md в JSON, UI-страницу с карточками версий и кликабельную версию в Header.

Требования: [docs/requirements/versioning.md](../requirements/versioning.md) → §4 UI, §5 API, §8 Этап 2.

---

## Pre-flight: совместимость

- **ADR/ограничения:** конфликтов нет. CamelCaseModel обязателен (✓), Pydantic для endpoint (✓)
- **Rules:** `api.md` (CamelCaseModel ✓), `frontend.md` (типы в types.ts ✓, хуки в hooks/ ✓, Tailwind ✓)
- **Dockerfile:** CHANGELOG.md уже копируется (`COPY CHANGELOG.md .`)
- **Вписывается в архитектуру** без изменений существующих абстракций

---

## План реализации

### 1. Backend: Pydantic модели

**Файл:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py) — добавить после `HealthResponse` (строка ~1391)

```python
class ChangelogEntry(CamelCaseModel):
    type: Literal["feat", "fix", "refactor", "docs", "perf"]
    description: str

class ChangelogVersion(CamelCaseModel):
    version: str       # "0.80.0"
    date: str          # "2026-02-22"
    changes: list[ChangelogEntry]

class ChangelogResponse(CamelCaseModel):
    versions: list[ChangelogVersion]
```

`Literal` уже импортирован (строка 13).

### 2. Backend: changelog_routes.py (создать)

**Файл:** `backend/app/api/changelog_routes.py` — новый

- `router = APIRouter(prefix="/api", tags=["changelog"])`
- `find_changelog()` — поиск CHANGELOG.md по parents (3→2→1→0), аналогично version.py но на 1 уровень глубже (файл в `api/`)
- `parse_changelog(content: str) → list[ChangelogVersion]` — regex-парсер формата Commitizen:
  - Версии: `## X.Y.Z (YYYY-MM-DD)`
  - Типы: `### Feat`, `### Fix` и т.д. → lowercase маппинг
  - Элементы: `- описание`
  - Неизвестные секции (Breaking, Style) — игнорируются
- `GET /api/changelog` → `ChangelogResponse` — если файл не найден или пуст, возвращает `{"versions": []}`

### 3. Backend: регистрация роутера

**Файл:** [backend/app/main.py](../../backend/app/main.py)

- Строка 13: добавить `changelog_routes` в import
- После строки 73: `app.include_router(changelog_routes.router)`

### 4. Frontend: TypeScript типы

**Файл:** [frontend/src/api/types.ts](../../frontend/src/api/types.ts) — добавить в конец

```typescript
// Changelog Types (v0.81+)
export interface ChangelogEntry {
  type: 'feat' | 'fix' | 'refactor' | 'docs' | 'perf';
  description: string;
}
export interface ChangelogVersion {
  version: string;
  date: string;
  changes: ChangelogEntry[];
}
export interface ChangelogResponse {
  versions: ChangelogVersion[];
}
```

### 5. Frontend: TanStack Query хук (создать)

**Файл:** `frontend/src/api/hooks/useChangelog.ts` — новый

По паттерну `useServices.ts`: `useQuery({ queryKey: ['changelog'], queryFn, staleTime: 5 * 60 * 1000 })`. Changelog меняется редко → staleTime 5 минут, без refetchInterval.

### 6. Frontend: NavigationContext (создать)

**Файл:** `frontend/src/contexts/NavigationContext.tsx` — новый

По паттерну `SettingsContext.tsx`:
- `type Page = 'dashboard' | 'changelog'`
- `NavigationProvider` с `useState<Page>('dashboard')`
- `useNavigation()` → `{ page, navigateTo, goBack }`
- НЕ персистируется в localStorage (при перезагрузке → dashboard)

**Почему context а не props:** Header не принимает props, Layout прокидывает только `children`. Context позволяет Header получить навигацию без изменения Layout.

### 7. Frontend: ChangelogPage (создать)

**Файл:** `frontend/src/components/changelog/ChangelogPage.tsx` — новый

Размещается в `components/changelog/` (не `pages/`) — в проекте нет директории pages, все компоненты в доменных папках components.

Содержимое:
- Кнопка «← Назад» (`ArrowLeft` из lucide-react) + заголовок «Журнал изменений»
- 4 состояния: загрузка (`Spinner`), ошибка (текст + `Button variant="secondary"` повторить), пусто (текст), данные
- Карточки версий: `Card` с `v{version}` + дата + список изменений с бейджами
- Бейджи: feat=«Новое» зелёный, fix=«Исправление» красный, refactor/docs/perf=серые
- `formatDate()` — кириллические месяцы (без date-fns, проще для русских падежей)

Переиспользуемые компоненты: `Card`, `Spinner`, `Button` из `components/common/`.

### 8. Frontend: интеграция App.tsx + Header.tsx

**[App.tsx](../../frontend/src/App.tsx):**
- Обернуть в `NavigationProvider` (внутри SettingsProvider, снаружи Layout)
- Добавить `PageRouter` компонент: `page === 'changelog' ? <ChangelogPage /> : <Dashboard />`
- `<Layout><PageRouter /></Layout>` вместо `<Layout><Dashboard /></Layout>`

**[Header.tsx](../../frontend/src/components/layout/Header.tsx):**
- Заменить `<span>` версии на `<button>` с `onClick={() => navigateTo('changelog')}`
- Добавить hover-стили: `hover:text-blue-500 hover:underline`
- Импортировать `useNavigation` из NavigationContext

**Layout.tsx** — без изменений.

---

## Новые файлы (4)

| Файл | Назначение |
|------|-----------|
| `backend/app/api/changelog_routes.py` | Парсер CHANGELOG.md + endpoint GET /api/changelog |
| `frontend/src/api/hooks/useChangelog.ts` | TanStack Query хук |
| `frontend/src/contexts/NavigationContext.tsx` | Навигация dashboard/changelog |
| `frontend/src/components/changelog/ChangelogPage.tsx` | UI страница с карточками |

## Изменяемые файлы (4)

| Файл | Изменение |
|------|-----------|
| `backend/app/models/schemas.py` | +3 Pydantic модели (ChangelogEntry, ChangelogVersion, ChangelogResponse) |
| `backend/app/main.py` | +import changelog_routes, +include_router |
| `frontend/src/api/types.ts` | +3 TypeScript интерфейса |
| `frontend/src/components/layout/Header.tsx` | span → кликабельная button + useNavigation |
| `frontend/src/App.tsx` | +NavigationProvider, +PageRouter |

---

## Верификация

1. **Backend парсер:** `curl http://localhost:8801/api/changelog` → JSON с версией 0.80.0
2. **Frontend:** `npm run dev` → Header показывает версию с hover-эффектом → клик → страница changelog с карточкой v0.80.0
3. **Пустой CHANGELOG:** удалить содержимое CHANGELOG.md → "История изменений пока недоступна"
4. **Кнопка «Назад»:** на странице changelog → возврат на dashboard
5. **TypeScript:** `npm run build` без ошибок

---

## Документация (предварительно)

- `docs/api-reference.md` — добавить `GET /api/changelog`
- `CLAUDE.md` — обновить "Текущий статус" (v0.81)
- ADR — не требуется (нет архитектурных решений)
