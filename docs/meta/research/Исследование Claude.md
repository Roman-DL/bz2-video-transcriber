# Исследование: Управление архитектурной целостностью при AI-assisted разработке

> Дата: 2026-01-28  
> Контекст: bz2-video-transcriber, система документации Diátaxis+

---

## Executive Summary

Проблема архитектурной деградации при AI-assisted разработке **признана индустрией**. Основные направления решений:

|Подход|Проактивность|Интеграция|Зрелость|
|---|---|---|---|
|**Cursor Rules / CLAUDE.md**|Средняя|Встроено|Высокая|
|**Spec-Driven Development**|Высокая|Требует инструментов|Ранняя|
|**Architecture Linters**|Низкая (постфактум)|CI/CD|Высокая|
|**Multi-Agent Coordination**|Высокая|Сложная|Экспериментальная|

**Ключевой инсайт:** Твоя система (ADR + arch-checker + architecture-summary) уже реализует ~70% найденных паттернов. Главный gap — **проактивное enforcement** до генерации кода.

---

## 1. Cursor Rules / .cursorrules

### Суть

Файлы инструкций, загружаемые в контекст при каждой сессии.

### Ключевые находки

**Структура (2025+):**

- Deprecated: `.cursorrules` в корне
- Актуально: `.cursor/rules/*.mdc` с glob patterns и `alwaysApply`

**Best practices:**

- Keep rules < 500 строк (после ~150-200 инструкций качество падает)
- Не дублировать линтеры — LLM плохо справляется с style enforcement
- Разделять по scope: глобальные vs domain-specific

**Проблема context drift:**

> "После нескольких сообщений правила игнорируются из-за оптимизации context window. Нужен Periodic Rule Reinforcement — явно напоминать о правилах."

### Релевантность для твоей системы

|Твой компонент|Cursor эквивалент|Статус|
|---|---|---|
|CLAUDE.md|.cursorrules / .cursor/rules/|✅ Есть|
|architecture-summary.md|Нет прямого аналога|✅ Преимущество|
|arch-checker|Нет (только ручной)|✅ Преимущество|

---

## 2. CLAUDE.md Best Practices

### Официальные рекомендации Anthropic

**Структура:**

```
# Bash commands
# Code style (минимум!)
# Architecture overview
# Important warnings
```

**Критичные принципы:**

1. **Меньше = лучше.** Bloated CLAUDE.md → Claude игнорирует инструкции
2. **Не дублировать линтеры.** "Never send an LLM to do a linter's job"
3. **Progressive disclosure.** Не всё сразу — указывать где найти детали
4. **Тестировать как код.** Если правило игнорируется — скорее всего файл слишком длинный

**Иерархия:**

```
~/.claude/CLAUDE.md          # глобальные
project/CLAUDE.md            # проектные
project/subdir/CLAUDE.md     # директорные (on-demand)
```

### Продвинутые паттерны

**Subagents для изоляции контекста:**

```
"Use a subagent to perform security review of that code"
```

Subagent работает в отдельном context window — не загрязняет основную сессию.

**Plan.md как external memory:**

```
Создай файл PLAN.md с планом реализации, затем используй его как чеклист.
```

Сохраняется между сессиями, даёт persistence.

**Skills vs CLAUDE.md:**

- CLAUDE.md: загружается всегда
- Skills: загружаются on-demand
- Для редко используемых знаний → Skills

---

## 3. Architecture Linters

### dependency-cruiser (JavaScript/TypeScript)

**Возможности:**

- Правила `forbidden` / `allowed` для импортов
- Детекция циклических зависимостей
- Валидация Clean Architecture / DDD
- Визуализация графа зависимостей

**Пример правила:**

```javascript
{
  "name": "no-client-server-mixing",
  "severity": "error",
  "from": { "path": "^src/client" },
  "to": { "path": "^src/server" }
}
```

**Интеграция:**

- Pre-commit hooks (husky)
- CI/CD pipeline
- VS Code extension

### Применимость

|Критерий|Оценка|
|---|---|
|Проактивность|❌ Постфактум (после написания кода)|
|Интеграция с AI|❌ Не специфичен для AI|
|Overhead|✅ Низкий после настройки|
|Для Python/FastAPI|⚠️ Нужен аналог (import-linter, pydeps)|

**Вердикт:** Полезен как **последний рубеж**, но не решает проблему AI-генерации.

---

## 4. Spec-Driven Development (SDD)

### Концепция

> "Спецификация — не документация, а исполняемый контракт."

**5-слойная модель:**

1. Intent Layer — бизнес-намерение
2. Contract Layer — API спецификации (OpenAPI, etc.)
3. Validation Layer — drift detection
4. Generation Layer — AI создаёт код по спеке
5. Governance Layer — compliance, audit

### Ключевая идея: Bidirectional Sync

Amazon Kiro (2025):

> "Developers can update code and request specification changes, OR update specs to trigger implementation tasks."

Это **предотвращает drift** — спека и код синхронизированы автоматически.

### Drift Detection типы

|Тип|Пример|
|---|---|
|Structural|API возвращает поля, не описанные в спеке|
|Behavioral|Сервис молча игнорирует required поля|
|Semantic|Error handling отличается от контракта|
|Security|Scopes деградировали относительно политики|

### Применимость

**Плюсы:**

- Проактивный подход
- Архитектура становится executable

**Минусы:**

- Требует инструментария (пока emerging)
- Cognitive shift для разработчиков
- Сложность для non-API частей (UI, business logic)

---

## 5. Multi-Agent Coordination

### Проблема

> "SyncMind tackles the common issue of 'out-of-sync' states when multiple agents update a shared codebase."

При параллельной работе агентов:

- State drift между агентами
- Error propagation (галлюцинации распространяются)
- Conflicting decisions

### Архитектурные паттерны

**Orchestrator Agent:**

- Понимает system-level objectives
- Разрешает конфликты между агентами
- Определяет порядок выполнения

**Specialized Agents:**

- Planner → decompose requirements
- Coder → implementation
- Reviewer → validate against specs
- Tester → generate tests

**CANDOR framework:** Координирует planners и reviewers для снижения error propagation.

### Применимость

|Критерий|Оценка|
|---|---|
|Зрелость|❌ Экспериментальная|
|Сложность|❌ Высокая|
|Solo-developer|⚠️ Overkill|
|Enterprise|✅ Потенциал|

---

## 6. Сравнительная таблица

|Подход|Проактивность|Встроенность|Overhead|Solo-friendly|AI-native|
|---|---|---|---|---|---|
|**Cursor Rules**|⚠️ Средняя|✅ Высокая|✅ Низкий|✅ Да|✅ Да|
|**CLAUDE.md**|⚠️ Средняя|✅ Высокая|✅ Низкий|✅ Да|✅ Да|
|**Твоя система**|⚠️ Средняя|⚠️ Ручная|⚠️ Средний|✅ Да|⚠️ Частично|
|**dependency-cruiser**|❌ Постфактум|✅ CI/CD|✅ Низкий|✅ Да|❌ Нет|
|**Spec-Driven**|✅ Высокая|❌ Требует tooling|❌ Высокий|⚠️ Сложно|✅ Да|
|**Multi-Agent**|✅ Высокая|❌ Сложная|❌ Высокий|❌ Нет|✅ Да|

---

## 7. Рекомендации

### Quick Wins (интегрировать сейчас)

1. **Slim down CLAUDE.md**
    
    - Оставить только критичные правила
    - Перенести детали в Skills / отдельные файлы
    - Использовать `@path/to/file.md` для ссылок
2. **Добавить Plan.md workflow**
    
    ```
    Перед реализацией создай PLAN.md с:
    1. Затрагиваемые модули
    2. Релевантные ADR
    3. Чеклист изменений
    ```
    
3. **Subagents для архитектурного review**
    
    ```
    После реализации: "Use subagent to review this code against ADR-001, ADR-004"
    ```
    

### Medium-term (следующий квартал)

4. **Architecture linter для Python**
    
    - Исследовать: `import-linter`, `pydeps`, `layers`
    - Интегрировать в pre-commit hooks
5. **Drift Detection lite**
    
    - Автоматическая проверка: код соответствует architecture-summary?
    - Возможно: custom MCP server

### Long-term (когда появятся инструменты)

6. **Spec-Driven для API**
    - OpenAPI как source of truth
    - AI генерирует код по спеке
    - Автоматический drift detection

---

## 8. Gaps (нерешённые проблемы)

|Проблема|Статус индустрии|
|---|---|
|AI "забывает" архитектуру между сессиями|Частично решается CLAUDE.md, Skills|
|Проактивное enforcement до генерации|Spec-Driven (emerging)|
|Метрики архитектурной деградации|Нет стандартов|
|Multi-agent consistency|Исследовательская стадия|
|Человек как bottleneck ревью|Не решена|

---

## Источники

### Cursor Rules

- [Cursor Docs: Rules](https://cursor.com/docs/context/rules)
- [awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)
- [Cursor Rules Best Practices](https://medium.com/elementor-engineers/cursor-rules-best-practices-for-developers-16a438a4935c)

### CLAUDE.md

- [Anthropic: Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude Code Docs: Best Practices](https://code.claude.com/docs/en/best-practices)
- [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [The Complete Guide to CLAUDE.md](https://www.builder.io/blog/claude-md-guide)

### Architecture Linters

- [dependency-cruiser](https://github.com/sverweij/dependency-cruiser)
- [Validate Dependencies According to Clean Architecture](https://betterprogramming.pub/validate-dependencies-according-to-clean-architecture-743077ea084c)

### Spec-Driven Development

- [InfoQ: Spec Driven Development](https://www.infoq.com/articles/spec-driven-development/)
- [Augment Code: Spec-Driven AI Code Generation](https://www.augmentcode.com/guides/spec-driven-ai-code-generation-with-multi-agent-systems)

### Multi-Agent Systems

- [ACM DIS 2025: Designing with Multi-Agent GenAI](https://dl.acm.org/doi/10.1145/3715336.3735823)
- [A Survey on Code Generation with LLM-based Agents](https://arxiv.org/html/2508.00083v1)
- [Springer: Agentic AI Comprehensive Survey](https://link.springer.com/article/10.1007/s10462-025-11422-4)

---

## 9. Практический Action Plan для твоей системы

### Немедленно (эта неделя)

1. **Оптимизировать CLAUDE.md**
    
    ```markdown
    # Project: bz2-video-transcriber
    
    ## Architecture (MUST READ)
    See @docs/audit/architecture-summary.md
    
    ## Before implementing features
    1. Check @docs/adr/ for relevant decisions
    2. Use arch-checker: "Проверь соответствие ADR для: {feature}"
    
    ## Commands
    npm run dev | test | build
    ```
    
    Всё остальное — в architecture-summary.md или Skills.
    
2. **Добавить Plan.md паттерн в workflow**
    
    ```
    Перед реализацией создай PLAN.md:
    - Затрагиваемые модули
    - Релевантные ADR (номера)
    - Изменения в документации (doc-sync)
    ```
    

### Следующий месяц

3. **Создать Skills для редких случаев**
    
    ```
    .claude/skills/
    ├── new-stage.md      # Как добавить stage (из arch-checker)
    ├── new-provider.md   # Как добавить AI provider
    └── api-endpoint.md   # Как добавить endpoint
    ```
    
4. **Pre-commit hook для Python архитектуры**
    
    ```bash
    pip install import-linter
    # Правила в setup.cfg или pyproject.toml
    ```
    

### Вывод

Твоя система **опережает** большинство подходов из индустрии:

- ADR-based decisions → лучше чем просто rules
- arch-checker → то, чего нет в Cursor/Claude по умолчанию
- architecture-summary → компактная карта (progressive disclosure)

Главный gap: **проактивность**. Сейчас система реактивная (проверяет после). Решение: Plan.md + обязательный arch-checker ДО начала кодирования.