"""
Story generator service.

Creates leadership story documents (8 blocks) from cleaned transcript.
Used for leadership content_type instead of longread + summary.

v0.23+: New document type for leadership content.
v0.42+: Added tokens_used, cost, and processing_time_sec metrics.
v0.53+: Added slides_text parameter for slides integration.
"""

import logging
import time
from typing import Any

from app.config import Settings, load_prompt, get_model_config
from app.utils.json_utils import extract_and_parse_json
from app.utils import calculate_cost
from app.models.schemas import (
    CleanedTranscript,
    PromptOverrides,
    Story,
    StoryBlock,
    TokensUsed,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient

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
        async with ClaudeClient.from_settings(settings) as client:
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
        slides_text: str | None = None,
    ) -> Story:
        """
        Generate story from cleaned transcript.

        v0.53+: Added slides_text parameter for slides integration.

        Args:
            cleaned_transcript: Cleaned transcript from CleanStage
            metadata: Video metadata (should have content_type=LEADERSHIP)
            slides_text: Optional extracted text from slides (v0.53+)

        Returns:
            Story with 8 blocks structure
        """
        start_time = time.time()

        logger.info(
            f"Generating story for: {metadata.speaker} "
            f"(event: {metadata.event_name or metadata.event_type})"
        )

        # Build prompt with optional slides context
        prompt = self._build_prompt(cleaned_transcript, metadata, slides_text)

        # v0.43+: Unified interface - all clients return (response, usage)
        response, usage = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

        # Parse response
        data = self._parse_json_response(response)

        elapsed = time.time() - start_time

        # Calculate cost if we have token data (v0.42+)
        tokens_used = None
        cost = None
        if input_tokens > 0 or output_tokens > 0:
            tokens_used = TokensUsed(input=input_tokens, output=output_tokens)
            cost = calculate_cost(
                self.settings.summarizer_model,
                input_tokens,
                output_tokens,
            )

        # Build Story object with validation and metrics
        story = self._build_story(data, metadata, tokens_used, cost, elapsed)

        logger.info(
            f"Story complete: {story.total_blocks} blocks, "
            f"speed={story.speed}, {elapsed:.1f}s"
        )

        cost_str = f"cost=${cost:.4f} | " if cost else ""
        perf_logger.info(
            f"PERF | story | "
            f"blocks={story.total_blocks} | "
            f"speed={story.speed} | "
            f"tokens={input_tokens}+{output_tokens} | "
            f"{cost_str}time={elapsed:.1f}s"
        )

        return story

    def _build_prompt(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        slides_text: str | None = None,
    ) -> str:
        """
        Build story generation prompt.

        v0.53+: Added slides_text parameter for slides integration.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            slides_text: Optional extracted text from slides (v0.53+)

        Returns:
            Combined prompt string
        """
        # If slides_text provided, append to transcript for context
        transcript_with_slides = cleaned_transcript.text
        if slides_text:
            transcript_with_slides = (
                f"{cleaned_transcript.text}\n\n"
                "---\n\n"
                "## Дополнительная информация со слайдов презентации\n\n"
                f"{slides_text}"
            )
            logger.info(f"Added slides context: {len(slides_text)} chars")

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
            transcript_with_slides,
            "",
            "### Формат ответа",
            "",
            self.template,
        ]
        return "\n".join(prompt_parts)

    def _build_story(
        self,
        data: dict[str, Any],
        metadata: VideoMetadata,
        tokens_used: TokensUsed | None = None,
        cost: float | None = None,
        processing_time: float | None = None,
    ) -> Story:
        """
        Build Story object from parsed data with validation.

        Args:
            data: Parsed JSON from LLM
            metadata: Video metadata
            tokens_used: Token usage statistics (v0.42+)
            cost: Estimated cost in USD (v0.42+)
            processing_time: Processing time in seconds (v0.42+)

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
            tokens_used=tokens_used,
            cost=cost,
            processing_time_sec=processing_time,
        )

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict
        """
        return extract_and_parse_json(response, json_type="object", default={})
