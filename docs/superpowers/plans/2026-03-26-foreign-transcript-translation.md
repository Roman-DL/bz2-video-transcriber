# Foreign Transcript Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support processing of foreign-language (EN, ES, mixed) MD transcripts with automatic translation to Russian during Longread/Story generation.

**Architecture:** Language auto-detected by Cyrillic ratio in Parse step. Clean stage skipped for foreign transcripts. Longread/Story prompts receive dynamic translation instructions + glossary as terminology reference. No new pipeline stages.

**Tech Stack:** Python, Pydantic, existing LLM pipeline (Claude Sonnet 4.6)

---

### Task 1: Language Detection Utility

**Files:**
- Create: `backend/app/utils/language_utils.py`

- [ ] **Step 1: Create language detection module**

```python
"""
Language detection for MD transcripts.

Detects whether transcript is Russian or foreign based on Cyrillic character ratio.
Specific language (EN, ES, etc.) is not determined — only ru vs foreign matters
for pipeline routing (Clean skip, translation instructions).
"""

import re


def detect_language(text: str) -> str:
    """Detect transcript language by Cyrillic character ratio.

    Analyzes first ~500 chars of content text (skipping markdown headers
    and speaker labels) to determine dominant language.

    Args:
        text: Full MD transcript text

    Returns:
        "ru" if >50% letters are Cyrillic, "foreign" otherwise
    """
    # Strip markdown headers and speaker labels, take first 500 chars
    content = _extract_content_text(text)
    sample = content[:500]

    if not sample.strip():
        return "ru"  # Default for empty text

    # Count only letter characters (skip digits, punctuation, whitespace)
    letters = [c for c in sample if c.isalpha()]
    if not letters:
        return "ru"

    cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04ff")
    ratio = cyrillic / len(letters)

    return "ru" if ratio > 0.5 else "foreign"


def _extract_content_text(text: str) -> str:
    """Extract content text, skipping headers and speaker labels.

    Removes:
    - Markdown headers (lines starting with #)
    - Speaker labels (SpeakerN or "Фамилия Имя" on standalone lines)

    Args:
        text: Raw MD transcript text

    Returns:
        Content text without headers and speaker labels
    """
    speaker_pattern = re.compile(
        r"^(Speaker\d+|[A-ZА-ЯЁ][a-zа-яё]+ [A-ZА-ЯЁ][a-zа-яё]+)$"
    )
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if speaker_pattern.match(stripped):
            continue
        if stripped:
            lines.append(stripped)
    return " ".join(lines)
```

- [ ] **Step 2: Verify with inline self-tests**

Add at the bottom of `backend/app/utils/language_utils.py`:

```python
if __name__ == "__main__":
    tests = [
        # (text, expected)
        ("Добрый день! Сегодня мы поговорим о бизнесе.", "ru"),
        ("Good morning everyone! Today we'll talk about business.", "foreign"),
        ("Speaker1\nHello everyone, welcome to our event.\nSpeaker2\nThank you!", "foreign"),
        ("Беркин Андрей\nДобрый день! Сегодня мы поговорим.\n", "ru"),
        (
            "Buenos días! Hoy vamos a hablar sobre el negocio. "
            "And now let me switch to English for a moment.",
            "foreign",
        ),
        ("", "ru"),  # Empty defaults to ru
        ("123 456 789", "ru"),  # No letters defaults to ru
    ]

    passed = 0
    for text, expected in tests:
        result = detect_language(text)
        ok = result == expected
        status = "OK" if ok else "FAIL"
        preview = text[:40].replace("\n", "\\n")
        if not ok:
            print(f"  {status}: detect_language('{preview}...') = {result!r}, expected {expected!r}")
        else:
            print(f"  {status}: '{preview}...' → {result!r}")
        passed += ok

    print(f"\n{passed}/{len(tests)} tests passed")
```

- [ ] **Step 3: Run self-tests**

Run: `cd backend && source .venv/bin/activate && python -m app.utils.language_utils`
Expected: `7/7 tests passed`

- [ ] **Step 4: Export from utils package**

Modify `backend/app/utils/__init__.py` — add `detect_language` to imports:

```python
from app.utils.language_utils import detect_language
```

Add `"detect_language"` to the `__all__` list.

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/language_utils.py backend/app/utils/__init__.py
git commit -m "feat: утилита detect_language для определения языка транскрипта"
```

---

### Task 2: Add `language` Field to VideoMetadata

**Files:**
- Modify: `backend/app/models/schemas.py:134`

- [ ] **Step 1: Add language field to VideoMetadata**

In `backend/app/models/schemas.py`, after line 134 (`speaker_info: SpeakerInfo | None = None`), add:

```python
    language: str = "ru"  # v0.83+: "ru" or "foreign", for pipeline routing
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile backend/app/models/schemas.py`
Expected: no output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: поле language в VideoMetadata для маршрутизации pipeline"
```

---

### Task 3: Detect Language in Parse Step

**Files:**
- Modify: `backend/app/api/step_routes.py:238-242`

- [ ] **Step 1: Add language detection to parse endpoint**

In `backend/app/api/step_routes.py`, update the import line to include `detect_language`:

```python
from app.utils import estimate_duration_from_text, get_media_duration, is_transcript_file, detect_language
```

Then modify the MD transcript handling block (around line 238-242). Current code:

```python
        if is_transcript_file(video_path):
            text = video_path.read_text(encoding="utf-8")
            metadata.duration_seconds = estimate_duration_from_text(text)
            metadata.speaker_info = parse_speakers(text)
```

Replace with:

```python
        if is_transcript_file(video_path):
            text = video_path.read_text(encoding="utf-8")
            metadata.duration_seconds = estimate_duration_from_text(text)
            metadata.speaker_info = parse_speakers(text)
            metadata.language = detect_language(text)
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile backend/app/api/step_routes.py`
Expected: no output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/step_routes.py
git commit -m "feat: определение языка транскрипта при парсинге MD файла"
```

---

### Task 4: Clean Stage Pass-Through for Foreign Transcripts

**Files:**
- Modify: `backend/app/services/stages/clean_stage.py:45-65`

- [ ] **Step 1: Add pass-through logic**

In `backend/app/services/stages/clean_stage.py`, add `logging` import at the top:

```python
import logging
```

Add logger after imports:

```python
logger = logging.getLogger(__name__)
```

Modify the `execute` method. Current code (lines 45-65):

```python
    async def execute(self, context: StageContext) -> CleanedTranscript:
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript, _ = context.get_result("transcribe")

        try:
            return await self.cleaner.clean(raw_transcript, metadata)
        except Exception as e:
            raise StageError(self.name, f"Cleaning failed: {e}", e)
```

Replace with:

```python
    async def execute(self, context: StageContext) -> CleanedTranscript:
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript, _ = context.get_result("transcribe")

        # Foreign transcripts: skip glossary cleaning, pass-through original text
        if metadata.language == "foreign":
            logger.info("skip_clean_foreign", language=metadata.language)
            return CleanedTranscript(
                text=raw_transcript.text,
                tokens_used=TokensUsed(input=0, output=0),
            )

        try:
            return await self.cleaner.clean(raw_transcript, metadata)
        except Exception as e:
            raise StageError(self.name, f"Cleaning failed: {e}", e)
```

Add `TokensUsed` to the imports from `app.models.schemas`:

```python
from app.models.schemas import CleanedTranscript, ProcessingStatus, RawTranscript, TokensUsed, VideoMetadata
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile backend/app/services/stages/clean_stage.py`
Expected: no output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/stages/clean_stage.py
git commit -m "feat: пропуск Clean stage для иностранных транскриптов (pass-through)"
```

---

### Task 5: Language Context Builder

**Files:**
- Modify: `backend/app/utils/language_utils.py`

- [ ] **Step 1: Add build_language_context function**

Append to `backend/app/utils/language_utils.py` (before the `if __name__` block):

```python
def build_language_context(language: str) -> list[str]:
    """Build language context block for LLM prompts.

    Returns list of strings for unpacking into prompt_parts via
    ``*build_language_context(...)``. Empty list for Russian
    transcripts (prompt unchanged).

    Follows same pattern as build_speaker_context() in speaker_utils.py.

    Args:
        language: "ru" or "foreign" from VideoMetadata.language

    Returns:
        List of prompt lines, empty for Russian transcripts
    """
    if language == "ru":
        return []

    return [
        "",
        "## Иностранный транскрипт",
        "",
        "Транскрипт содержит речь на иностранном языке (возможно несколько языков).",
        "- Генерируй текст ПОЛНОСТЬЮ на русском языке",
        "- Используй глоссарий как справочник терминов — применяй canonical формы",
        "- Имена собственные транслитерируй (John Smith → Джон Смит)",
        "- Если в транскрипте есть ошибки транскрибации — исправляй по контексту",
        "- Если спикеры обозначены как Speaker1, Speaker2 — определи их имена из контекста (представление, самопрезентация) и используй в тексте",
    ]
```

- [ ] **Step 2: Add self-tests for build_language_context**

Add to the `if __name__` block, after existing tests:

```python
    # Tests for build_language_context
    print("\n--- build_language_context tests ---")
    ctx_tests = [
        ("ru", True),      # Empty for Russian
        ("foreign", False), # Non-empty for foreign
    ]
    ctx_passed = 0
    for lang, expect_empty in ctx_tests:
        result = build_language_context(lang)
        if expect_empty:
            ok = result == []
        else:
            ok = len(result) > 0 and "Иностранный транскрипт" in "\n".join(result)
        status = "OK" if ok else "FAIL"
        print(f"  {status}: build_language_context({lang!r}) → {'[]' if not result else f'{len(result)} lines'}")
        ctx_passed += ok
    print(f"\n{ctx_passed}/{len(ctx_tests)} build_language_context tests passed")
```

- [ ] **Step 3: Run self-tests**

Run: `cd backend && source .venv/bin/activate && python -m app.utils.language_utils`
Expected: All tests pass (including new build_language_context tests)

- [ ] **Step 4: Export build_language_context from utils**

In `backend/app/utils/__init__.py`, update the import:

```python
from app.utils.language_utils import detect_language, build_language_context
```

Add `"build_language_context"` to `__all__`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/language_utils.py backend/app/utils/__init__.py
git commit -m "feat: build_language_context для инжекции инструкций перевода в промпты"
```

---

### Task 6: Inject Language Context into Longread Generator

**Files:**
- Modify: `backend/app/services/longread_generator.py`

- [ ] **Step 1: Add import**

In `backend/app/services/longread_generator.py`, add to imports (next to the `build_speaker_context` import):

```python
from app.utils.language_utils import build_language_context
```

- [ ] **Step 2: Inject into single-pass prompt (line ~315)**

Find the `_build_single_pass_prompt` method. After the line:

```python
            *build_speaker_context(metadata.speaker_info, metadata.speaker),
```

Add:

```python
            *build_language_context(metadata.language),
```

- [ ] **Step 3: Inject into section prompt (line ~536)**

Find the `_build_section_prompt` method. After the line:

```python
            *build_speaker_context(metadata.speaker_info, metadata.speaker),
```

Add:

```python
            *build_language_context(metadata.language),
```

- [ ] **Step 4: Inject into frame prompt (line ~627)**

Find the `_build_frame_prompt` method. After the line:

```python
            *build_speaker_context(metadata.speaker_info, metadata.speaker),
```

Add:

```python
            *build_language_context(metadata.language),
```

- [ ] **Step 5: Verify syntax**

Run: `python3 -m py_compile backend/app/services/longread_generator.py`
Expected: no output (success)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/longread_generator.py
git commit -m "feat: инжекция language_context в промпты Longread генератора"
```

---

### Task 7: Inject Language Context into Story Generator

**Files:**
- Modify: `backend/app/services/story_generator.py`

- [ ] **Step 1: Add import**

In `backend/app/services/story_generator.py`, add to imports (next to the `build_speaker_context` import):

```python
from app.utils.language_utils import build_language_context
```

- [ ] **Step 2: Inject into prompt (line ~211)**

Find the `_build_prompt` method. After the line:

```python
            *build_speaker_context(metadata.speaker_info, metadata.speaker),
```

Add:

```python
            *build_language_context(metadata.language),
```

- [ ] **Step 3: Verify syntax**

Run: `python3 -m py_compile backend/app/services/story_generator.py`
Expected: no output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/story_generator.py
git commit -m "feat: инжекция language_context в промпт Story генератора"
```

---

### Task 8: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `.claude/rules/pipeline.md`

- [ ] **Step 1: Update CLAUDE.md**

In the "Ключевые ограничения" section, add item 8:

```markdown
8. **Foreign transcripts** — Clean пропускается, перевод в Longread/Story промптах. Язык определяется автоматически
```

In the "Архитектура" section, add note:

```markdown
> **v0.83+:** Поддержка иностранных транскриптов: автодетекция языка, пропуск Clean, перевод в Longread/Story.
```

Update version in "Текущий статус":

```markdown
**Версия:** v0.83 • [Полная история изменений](CHANGELOG.md) (v0.1–v0.83)
```

- [ ] **Step 2: Update pipeline rules**

In `.claude/rules/pipeline.md`, add section after "## MD Transcripts":

```markdown
## Foreign Transcripts (v0.83+)
- Язык определяется в parse step по доле кириллицы (`detect_language()`)
- `VideoMetadata.language`: `"ru"` (default) или `"foreign"`
- Clean stage: pass-through для `language == "foreign"` (глоссарий не применим)
- `build_language_context(language)` → `list[str]` для unpacking в prompt_parts (аналог `build_speaker_context`)
- Инжектируется во ВСЕ prompt builder методы Longread и Story генераторов
- Перевод + коррекция ошибок происходят неявно при генерации LLM
```

- [ ] **Step 3: Update ARCHITECTURE.md**

Add mention of foreign transcript support in the relevant section of `docs/ARCHITECTURE.md`.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md .claude/rules/pipeline.md docs/ARCHITECTURE.md
git commit -m "docs: поддержка иностранных транскриптов (v0.83)"
```

---

### Task 9: Deploy and Test on Server

**Files:** None (deployment only)

- [ ] **Step 1: Deploy**

```bash
/bin/bash scripts/deploy.sh
```

- [ ] **Step 2: Health check**

```bash
curl -s https://transcriber.home/health | python3 -m json.tool
```

Expected: healthy response with updated version.

- [ ] **Step 3: Test with English transcript**

Upload an English MD transcript through the UI. Verify:
1. Parse step detects `language: "foreign"`
2. Clean step shows pass-through (no LLM call, instant)
3. Longread/Story generates text in Russian with correct terminology from glossary

- [ ] **Step 4: Test with Russian transcript (regression)**

Upload a Russian MD transcript. Verify:
1. Parse step detects `language: "ru"`
2. Clean step runs normally (glossary applied)
3. Longread/Story generates as before — no regressions
