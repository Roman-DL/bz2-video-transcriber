"""
Story generator service.

Creates leadership story documents (8 blocks) from cleaned transcript.
Used for leadership content_type instead of longread + summary.

v0.23+: New document type for leadership content.
"""

import json
import logging
import time
from typing import Any

from app.config import Settings, get_settings, load_prompt, get_model_config
from app.utils.json_utils import extract_json
from app.models.schemas import (
    CleanedTranscript,
    PromptOverrides,
    Story,
    StoryBlock,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient, OllamaClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Valid access_level values
VALID_ACCESS_LEVELS = ["consultant", "leader", "personal"]

# Valid speed values
VALID_SPEEDS = ["быстро", "средне", "долго", "очень долго"]

# Valid business_format values
VALID_BUSINESS_FORMATS = ["клуб", "онлайн", "гибрид"]

# Block names in order
BLOCK_NAMES = [
    "Кто они",
    "Путь в бизнес",
    "Рост и вызовы",
    "Ключ к статусу",
    "Как устроен бизнес",
    "Принципы и советы",
    "Итоги",
    "Заметки аналитика",
]


class StoryGenerator:
    """
    Story generation service for leadership content.

    Generates a structured 8-block document analyzing a leader's journey.
    Used instead of longread + summary for leadership content_type.

    Example:
        async with OllamaClient.from_settings(settings) as client:
            generator = StoryGenerator(client, settings)
            story = await generator.generate(cleaned_transcript, metadata)
            markdown = story.to_markdown()
    """

    def __init__(
        self,
        ai_client: BaseAIClient,
        settings: Settings,
        prompt_overrides: PromptOverrides | None = None,
    ):
        """
        Initialize story generator.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
            prompt_overrides: Optional prompt file overrides (v0.32+)
        """
        self.ai_client = ai_client
        self.settings = settings

        # Load prompt architecture with optional overrides
        overrides = prompt_overrides or PromptOverrides()
        self.system_prompt = load_prompt("story", overrides.system or "system", settings)
        self.instructions = load_prompt("story", overrides.instructions or "instructions", settings)
        self.template = load_prompt("story", overrides.template or "template", settings)

        logger.debug("StoryGenerator initialized")

    async def generate(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Story:
        """
        Generate story from cleaned transcript.

        Args:
            cleaned_transcript: Cleaned transcript from CleanStage
            metadata: Video metadata (should have content_type=LEADERSHIP)

        Returns:
            Story with 8 blocks structure
        """
        start_time = time.time()

        logger.info(
            f"Generating story for: {metadata.speaker} "
            f"(event: {metadata.event_name or metadata.event_type})"
        )

        # Build prompt
        prompt = self._build_prompt(cleaned_transcript, metadata)

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
        data = self._parse_json_response(response)

        elapsed = time.time() - start_time

        # Build Story object with validation
        story = self._build_story(data, metadata)

        logger.info(
            f"Story complete: {story.total_blocks} blocks, "
            f"speed={story.speed}, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | story | "
            f"blocks={story.total_blocks} | "
            f"speed={story.speed} | "
            f"time={elapsed:.1f}s"
        )

        return story

    def _build_prompt(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> str:
        """
        Build story generation prompt.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata

        Returns:
            Combined prompt string
        """
        prompt_parts = [
            self.system_prompt,
            "",
            "---",
            "",
            self.instructions,
            "",
            "---",
            "",
            "## Задание",
            "",
            "Создай конспект лидерской истории по шаблону 8 блоков.",
            "",
            f"**Имена:** {metadata.speaker}",
            f"**Событие:** {metadata.event_name or metadata.event_type}",
            f"**Дата:** {metadata.date.isoformat()}",
            "",
            "### Транскрипт",
            "",
            cleaned_transcript.text,
            "",
            "### Формат ответа",
            "",
            self.template,
        ]
        return "\n".join(prompt_parts)

    def _build_story(self, data: dict[str, Any], metadata: VideoMetadata) -> Story:
        """
        Build Story object from parsed data with validation.

        Args:
            data: Parsed JSON from LLM
            metadata: Video metadata

        Returns:
            Validated Story object
        """
        # Parse blocks
        blocks_data = data.get("blocks", [])
        blocks = []
        for block_data in blocks_data:
            block_num = block_data.get("block_number", len(blocks) + 1)
            if 1 <= block_num <= 8:
                blocks.append(StoryBlock(
                    block_number=block_num,
                    block_name=block_data.get("block_name", BLOCK_NAMES[block_num - 1]),
                    content=block_data.get("content", ""),
                ))

        # Sort blocks by number
        blocks.sort(key=lambda b: b.block_number)

        # Validate speed
        speed = data.get("speed", "средне")
        if speed not in VALID_SPEEDS:
            speed = "средне"

        # Validate business_format
        business_format = data.get("business_format", "гибрид")
        if business_format not in VALID_BUSINESS_FORMATS:
            business_format = "гибрид"

        # Validate access_level
        access_level = data.get("access_level", "consultant")
        if access_level not in VALID_ACCESS_LEVELS:
            access_level = "consultant"

        return Story(
            video_id=metadata.video_id,
            names=data.get("names", metadata.speaker),
            current_status=data.get("current_status", ""),
            event_name=metadata.event_name or metadata.event_type,
            date=metadata.date,
            main_insight=data.get("main_insight", ""),
            blocks=blocks,
            time_in_business=data.get("time_in_business", ""),
            time_to_status=data.get("time_to_status", ""),
            speed=speed,
            business_format=business_format,
            is_family=data.get("is_family", False),
            had_stagnation=data.get("had_stagnation", False),
            stagnation_years=data.get("stagnation_years", 0),
            had_restart=data.get("had_restart", False),
            key_pattern=data.get("key_pattern", ""),
            mentor=data.get("mentor", ""),
            tags=data.get("tags", []),
            access_level=access_level,
            related=data.get("related", []),
            model_name=self.settings.summarizer_model,
        )

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict
        """
        json_str = extract_json(response, json_type="object")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return {}


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    from datetime import date
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all story generator tests."""
        print("\nRunning story generator tests...\n")

        settings = get_settings()

        # Test 1: Load prompts (v0.30+ hierarchical structure)
        print("Test 1: Load prompts (v0.30+ hierarchical)...", end=" ")
        try:
            system_prompt = load_prompt("story", "system", settings)
            instructions = load_prompt("story", "instructions", settings)
            template = load_prompt("story", "template", settings)
            assert "Story Generator" in system_prompt
            assert "8 блоков" in instructions
            assert "blocks" in template
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Story model
        print("\nTest 2: Story model...", end=" ")
        try:
            story = Story(
                video_id="test-video",
                names="Иванов Иван и Иванова Мария",
                current_status="President's Team",
                event_name="Форум TABTeam",
                date=date(2025, 1, 20),
                main_insight="Стагнация — не приговор",
                blocks=[
                    StoryBlock(
                        block_number=1,
                        block_name="Кто они",
                        content="**Иван:** врач, 45 лет",
                    ),
                    StoryBlock(
                        block_number=2,
                        block_name="Путь в бизнес",
                        content="Пришли в 2010 году через продукт",
                    ),
                ],
                time_in_business="15 лет",
                time_to_status="12 лет",
                speed="долго",
                business_format="гибрид",
                is_family=True,
                had_stagnation=True,
                stagnation_years=10,
                tags=["стагнация", "семейная-пара"],
                model_name="test",
            )
            assert story.total_blocks == 2
            markdown = story.to_markdown()
            assert "leadership-story" in markdown
            assert "Иванов Иван" in markdown
            print("OK")
            print(f"  Blocks: {story.total_blocks}")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        # Test 3: Full generation (requires Ollama)
        print("\nTest 3: Full generation...", end=" ")
        async with OllamaClient.from_settings(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    from app.models.schemas import ContentType, EventCategory

                    generator = StoryGenerator(client, settings)

                    mock_metadata = VideoMetadata(
                        date=date(2025, 1, 20),
                        event_type="Выездные",
                        stream="",
                        title="Тест Лидер",
                        speaker="Тест Лидер",
                        original_filename="test.mp4",
                        video_id="test-video",
                        source_path=Path("/test/test.mp4"),
                        archive_path=Path("/archive/test"),
                        content_type=ContentType.LEADERSHIP,
                        event_category=EventCategory.OFFSITE,
                        event_name="Форум TABTeam",
                    )

                    mock_transcript = CleanedTranscript(
                        text="Меня зовут Иван Иванов, я President's Team. "
                             "В бизнесе 15 лет. Пришёл через продукт, похудел на 20 кг. "
                             "Первые 5 лет были сложными, потом 10 лет стагнации. "
                             "Ключ к прорыву — работа с командой. "
                             "Сейчас у меня клуб и онлайн.",
                        original_length=1000,
                        cleaned_length=500,
                        model_name=settings.cleaner_model,
                    )

                    story = await generator.generate(mock_transcript, mock_metadata)

                    assert story.total_blocks > 0
                    assert story.access_level in VALID_ACCESS_LEVELS

                    print("OK")
                    print(f"  Blocks: {story.total_blocks}")
                    print(f"  Names: {story.names}")
                    print(f"  Speed: {story.speed}")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    import asyncio
    sys.exit(asyncio.run(run_tests()))
