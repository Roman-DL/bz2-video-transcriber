Ниже — сжатый обзор того, что сейчас реально есть по теме, плюс идеи, как усилить твою существующую систему.

## 1. Обзор подходов

### 1.1. Rules-файлы для IDE-агентов (Cursor, Claude Code)

- **Cursor Rules / .cursor/rules / .cursorrules**: рекомендуют модульные правила по доменам (backend, frontend, тесты, security), с фронтматтером (globs, alwaysApply), явное объявление архитектурных паттернов и запретных практик, итеративное развитие правил по мере выявления типичных ошибок ИИ.[1][2][3][4]
- **CLAUDE.md + .claude/rules/**: рекомендуют делить правила по слоям/модулям (api.md, database.md, testing.md, security.md), использовать path‑scoped правила (frontmatter с `paths:`) и хранить в корне с иерархией правил; короткий core-док, который ссылается на модульные файлы.[5][6]
- Паттерн из сообщества: для каждого крупного модуля держать локальный markdown с архитектурой папки, а в CLAUDE.md прописать, что агент обязан эти файлы смотреть и следовать им.[7]

По сути это **AI-native, но полу‑проактивный** подход: ты кодишь внутри IDE, ИИ видит правила *до* генерации и уже там ограничен архитектурой.

### 1.2. Agentic workflows с guardrails / MCP

- Современный паттерн — **“AI/CD pipeline” с агентами и guardrails**: один уровень агентов делает генерацию, другой — архитектурный контроль/валидацию, плюс интеграция в CI.[8]
- MCP даёт способ вынести архитектурный контекст в отдельный **MCP‑сервер**, который экспонирует:  
  - ресурсы (ADR, архитектурные summary, allowed dependencies),  
  - инструменты (проверка зависимостей, поиск нарушений),  
  - промпты (шаблоны для архитектурных решений).[9][10][11]
  Хост (Claude Code/Tasks) держит сессии с несколькими MCP‑серверами, каждый даёт специфический контекст и может быть архитектурным “мозгом”.[10][9]

Это уже ближе к **проактивному** и хорошо **интегрируемому** подходу: агент при работе всегда имеет доступ к централизованному серверу архитектуры.

### 1.3. Архитектурные линтеры и статический анализ

- **ArchUnit** (Java), **dependency-cruiser** / ESLint plugins для архитектуры в JS/TS и т.п. — классические архитектурные линтеры: проверяют forbidden/allowed зависимости между слоями, модульные границы, naming conventions.[2]
- Их обычно встраивают в CI/CD и/или pre-commit, чтобы не пропускать нарушения; это **универсальный**, не AI‑специфичный слой.  
- В ML/enterprise‑сеттингах часто есть собственные “quality gates” в CI для сложных систем, где проверяются стилевые и архитектурные требования до деплоя.[12][13]

Это чисто **реактивный** контроль, но даёт хорошую автоматизируемость и масштабируемость.

### 1.4. Практики команд и роль AI‑architect

- Из инженерных блогов: рекомендуют, чтобы **люди определяли архитектуру, а ИИ — реализовывал локальные задачи**; глобальное проектирование и кросс‑сервисные решения — ответственность человека.[14][15]
- В больших организациях существует набор архитектурных ролей (chief/enterprise/solution/technical architect), которые задают нормы, CI/CD‑гейты и архитектурные паттерны. Многие просто расширяют их зону ответственности на AI‑ассистентов (формулирование правил для ИИ, владение CLAUDE.md/.cursor/rules, ревью AI‑вкладов).[16][12]
- Растёт практика “single, context-aware assistant for entire repo” — вместо зоопарка плагинов используется один ассистент, индексирующий весь репозиторий и знающий архитектурные паттерны и кросс‑сервисные связи.[17][14]

Это больше про **организационные** паттерны: явный AI‑architect/maintainer, единый ассистент и строгие правила.

### 1.5. Академические и исследовательские идеи

- Существуют работы про **энтропию архитектуры**: показывают, что рост числа согласованно связанных элементов (consistency rules) уменьшает архитектурную энтропию и повышает упорядоченность; используются метрики типа AICC и Class Design Entropy (CDE).[18]
- В “диких” обсуждениях (блоги/форумы) для AI‑кода всё чаще используют термин **architectural entropy** или “vibe coding debt”: множество локально разумных AI‑решений приводит к потере глобальной согласованности и усложняет reasoning о системе.[19][20]
- Пока мало формализованных именно AI‑специфичных метрик, но логика такая: измеряют нарушение архитектурных зависимостей, рост “аномальных” паттернов и усложнение структуры (энтропийные/complexity‑метрики).[20][18]

Формальные метрики можно адаптировать к твоему arch‑audit.

***

## 2. Сравнительная таблица подходов

### Основные классы решений

| Подход | Проактивность | Интеграция | Overhead | Масштабируемость | AI-native |
|-------|---------------|------------|----------|------------------|----------|
| IDE rules (Cursor/.claude) | Средняя: влияют до генерации, но зависят от чтения правил агентом | Сильно встроены в workflow IDE | Средний: нужно писать/поддерживать правила | Хорошая: solo и команда (через git) | Да, специально под ИИ |
| MCP-сервер архитектуры | Высокая: агенты всегда ходят за контекстом перед действием | Встраивается в хост (Claude Code/Tasks) и workflows | Начальный высокий, потом средний | Очень хорошая: несколько агентов, несколько проектов | Да, нативно для agentic‑сценариев |
| Архитектурные линтеры (ArchUnit, dependency-cruiser) | Низкая/средняя: ловят постфактум, но до merge/deploy | В CI/CD, pre-commit, иногда в IDE | Низкий/средний: после начальной настройки правила стабильны | Высокая: стандартный DevOps‑паттерн | Нет, универсальный |
| AI‑architect + human guardrails | Средняя: человек задаёт архитектуру до генерации, но не контролирует каждую сессию | Через процессы: code review, архитектурные ревью, правила для ИИ | Средний/высокий, зависит от дисциплины | Хорошая для команды, избыточная для solo | Частично: человек управляет ИИ |
| AI/CD pipeline с multi‑agent guardrails | Высокая: один агент генерит, другой валидирует перед merge | Интегрируется в CI/CD и/или GitOps | Высокий на внедрение, потом средний | Хорошая для команд и больших реп | Да, многоагентный подход |
| Энтропийные/complexity‑метрики | Низкая: измерение деградации ex post | Обычно отдельные отчёты или дашборд | Средний: нужно считать и интерпретировать | Хорошая, если вычисление автоматизировано | Нет (но можно использовать на AI‑коде) |

***

## 3. Что можно внедрить в твою систему

У тебя уже есть ADR, arch-checker, arch-audit, architecture-summary, doc-sync. Это ядро. Что поверх:

### 3.1. “Architect MCP server” вместо разрозненных скриптов

С учётом MCP сейчас логично оформить твои arch‑инструменты как **один MCP‑сервер архитектуры**, который умеет:[11][9][10]

- Экспортировать ресурсы:  
  - `architecture-summary` (короткие карты по модулям),  
  - список ADR, сгруппированных по доменам,  
  - список допустимых зависимостей (слойность, модули, allowed imports).  
- Предоставлять инструменты:  
  - `check_change_against_adr(diff)` — то, что делает arch-checker,  
  - `suggest_adr_for_change(diff)` — генерация/шаблон нового ADR,  
  - `list_docs_to_update(diff)` — твой doc-sync, но как tool,  
  - `architectural_smell_scan(path)` — часть arch-audit.  

Claude Tasks и Claude Code тогда **обязаны** в промптах/CLAUDE.md пользоваться этим сервером перед генерацией или ревью. Это переводит твою систему в **проактивный и AI‑native** режим.

### 3.2. Заземлить IDE-агентов на архитектуру через CLAUDE.md/.claude/rules и Cursor Rules

- Разложить архитектуру по модульным markdown‑файлам (на уровне папок/слоёв), как советуют для Claude.[5][7]
- В CLAUDE.md и .claude/rules прописать:  
  - обязательный вызов MCP‑инструментов при изменении определённых путей,  
  - явные правила по слоям (например: UI не может импортировать data‑access напрямую).  
- Для Cursor — .cursor/rules с аналогичной структурой и frontmatter‑глобами по слоям (backend, frontend, infra).[1][2]

Это уменьшит твою текущую “реактивность”: ИИ будет видеть архитектурные границы до генерации.

### 3.3. Вынести линтеры в CI как “non-AI guardrails”

- Добавить language‑specific архитектурные линтеры (ArchUnit, dependency-cruiser или свои AST‑проверки) и привязать их к тем же правилам, что и MCP‑сервер.[2][12]
- В CI сделать gate: PR не мержится, если нарушены архитектурные зависимости или не обновлены нужные doc‑файлы (doc-sync‑логика).  

Так твой arch-checker/arch-audit перестают быть только “ручными” и входят в pipeline.

### 3.4. Multi-agent patterns: “Architect agent” + “Coder agent”

В рамках Claude Tasks / других оркестраторов можно формализовать паттерн:

- **Architect Task**: читает ADR и MCP‑ресурсы, планирует архитектурное решение и создаёт “implementation brief” + обновления ADR (если нужно).  
- **Coder Task**: берёт brief и уже генерирует код, при этом IDE‑агент ограничен правилами (.claude/rules / .cursor/rules) и обращается к MCP‑серверу для локальных проверок.  

Это отвечает на вопрос про сохранение согласованности в multi‑agent: у тебя один “источник архитектуры” (MCP + ADR), вокруг которого крутятся задачи.

### 3.5. Метрики архитектурной деградации

Можно добавить простые, но полезные метрики, вдохновляясь энтропийными работами:[18][20]

- Количество нарушенных архитектурных правил (по линтерам) на 1k строк кода.  
- Доля файлов/модулей с аномальными зависимостями (по сравнению с основной массой).  
- “Entropy proxy”: количество различных типов зависимостей/слоёв в среднем модуле (рост часто сигнализирует о размывании границ).  

Это можно привязать к регулярному arch-audit и рисовать графики “энтропии”/нарушений во времени.

***

## 4. Gaps — что остаётся нерешённым

- **Полностью проактивный, “замкнутый” контроль при генерации**. IDE‑агенты всё равно могут частично игнорировать правила или не всегда их загружать; нет гарантий, что любая сессия идеально соблюдает архитектуру.[7][20]
- **Память архитектуры между сессиями** решается смесью CLAUDE.md/.cursor/rules, MCP и индексированием репозитория, но модель всё равно не удерживает “ментальную модель” как человек; решения часто остаются локальными, если не построить явный план на уровне Architect Task.[15][14][17]
- **Формальные AI‑специфичные метрики архитектурной энтропии** пока в зачаточном состоянии: есть классические entropy/complexity‑метрики и эмпирические наблюдения, но нет общепринятого стандарта “AI architecture quality score”.[19][20][18]
- **Параллельная работа нескольких агентов по разным веткам/фичам**: пока нет полностью автоматизированного “архитектурного merge‑brain”; конфликтующие локальные решения всё равно требуют человеческого архитектурного ревью.  

Если кратко: лучшее, что сейчас есть, — это комбинация архитектурного MCP‑сервера, IDE‑rules (CLAUDE.md/.claude/rules, .cursor/rules), архитектурных линтеров в CI и явной роли/агента‑архитектора. Всё остальное — либо исследования, либо практики уровня “дисциплина команды” без сильной автоматизации.

Источники
[1] Using Cursor Rules Effectively: Best Practices and Common ... https://cursor.fan/tutorial/HowTo/using-cursor-rules-effectively/
[2] Comprehensive Cursor Rules Best Practices Guide - Lambda Curry https://www.lambdacurry.dev/blog/comprehensive-cursor-rules-best-practices-guide
[3] Mastering Cursor Rules: Your Complete Guide to AI- ... https://dev.to/anshul_02/mastering-cursor-rules-your-complete-guide-to-ai-powered-coding-excellence-2j5h
[4] Good examples of .cursorrules file? - Cursor - Community Forum https://forum.cursor.com/t/good-examples-of-cursorrules-file/4346
[5] CLAUDE.md Patterns That Actually Work https://www.elegantsoftwaresolutions.com/blog/claude-code-mastery-claude-md-patterns
[6] CLAUDE.md for .NET Developers - Complete Guide with ... https://codewithmukesh.com/blog/claude-md-mastery-dotnet/
[7] How do you get Claude Code to actually follow your ... https://www.reddit.com/r/ClaudeAI/comments/1lbvqza/how_do_you_get_claude_code_to_actually_follow/
[8] Building an AI/CD Pipeline: Architecture, Agents & Guardrails https://pub.towardsai.net/building-an-ai-cd-pipeline-architecture-agents-guardrails-01b1744e1f5a
[9] Architecture overview - Model Context Protocol https://modelcontextprotocol.io/docs/learn/architecture
[10] Architecture https://modelcontextprotocol.io/specification/2025-06-18/architecture
[11] Architectural Components of MCP https://huggingface.co/learn/mcp-course/unit1/architectural-components
[12] CI/CD for microservices architectures - Azure https://learn.microsoft.com/en-us/azure/architecture/microservices/ci-cd
[13] 4 Ways Machine Learning Teams Use CI/CD in Production https://neptune.ai/blog/ways-ml-teams-use-ci-cd-in-production
[14] AI Coding Assistants for Large Codebases: A Complete ... https://www.augmentcode.com/tools/ai-coding-assistants-for-large-codebases-a-complete-guide
[15] Best Practices for AI-Assisted Coding https://engineering.axur.com/2025/05/09/best-practices-for-ai-assisted-coding.html
[16] Building a robust IT architecture team: Roles and structure https://rightpeoplegroup.com/blog/building-robust-it-architecture-team-roles-structure
[17] Design System Success with AI Coding Assistants https://blog.bitsrc.io/design-system-success-with-ai-coding-assistants-78b13443ca23
[18] Entropy as a Measure of Consistency in Software Architecture - PMC https://pmc.ncbi.nlm.nih.gov/articles/PMC9955753/
[19] Vibe Coding Debt - My experience implementing projects ... https://www.reddit.com/r/vibecoding/comments/1npa9lo/vibe_coding_debt_my_experience_implementing/
[20] AI Makes You Code Faster, But Ship Slower | N's Blog https://nmn.gl/blog/ai-code-review
