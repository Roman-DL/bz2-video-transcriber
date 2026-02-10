"""
Description generator service.

Generates description and short_description via Claude for BZ2-Bot export.
Extracted from saver.py in v0.62 to run during chunk stage instead of save.
"""

import json
import logging
import time

from app.config import Settings, load_events_config, load_prompt
from app.models.schemas import (
    Longread,
    Story,
    Summary,
    TokensUsed,
    VideoMetadata,
)
from app.services.ai_clients import ClaudeClient
from app.utils import calculate_cost
from app.utils.json_utils import extract_json

logger = logging.getLogger(__name__)


class DescriptionResult:
    """Result of description generation."""

    def __init__(
        self,
        description: str = "",
        short_description: str = "",
        model_name: str | None = None,
        tokens_used: TokensUsed | None = None,
        cost: float | None = None,
        processing_time_sec: float | None = None,
    ):
        self.description = description
        self.short_description = short_description
        self.model_name = model_name
        self.tokens_used = tokens_used
        self.cost = cost
        self.processing_time_sec = processing_time_sec


class DescriptionGenerator:
    """Generates semantic descriptions for BZ2-Bot export.

    Uses Claude to create:
    - description: semantic index for file search
    - short_description: brief description for Telegram

    Priority for source content: Summary > Longread/Story markdown.
    On error, returns empty result (does not fail the pipeline).

    Example:
        generator = DescriptionGenerator(settings)
        result = await generator.generate(
            summary=summary, longread=longread, story=None, metadata=metadata
        )
        print(result.description)
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.events_config = load_events_config(settings)

    async def generate(
        self,
        summary: Summary | None,
        longread: Longread | None,
        story: Story | None,
        metadata: VideoMetadata,
    ) -> DescriptionResult:
        """Generate description and short_description via Claude.

        Args:
            summary: Condensed summary (priority source)
            longread: Longread document (fallback)
            story: Leadership story (fallback)
            metadata: Video metadata for prompt context

        Returns:
            DescriptionResult with descriptions and LLM metrics
        """
        source_content = self._build_source_content(summary, longread, story)
        if not source_content:
            logger.warning("description_skip", extra={"reason": "no_source_content"})
            return DescriptionResult()

        stream_name = self._get_stream_name(metadata.event_type, metadata.stream)

        try:
            system_prompt = load_prompt("export", "system", self.settings)
            user_template = load_prompt("export", "user", self.settings)
        except FileNotFoundError:
            logger.warning("description_skip", extra={"reason": "prompts_not_found"})
            return DescriptionResult()

        user_prompt = user_template.format(
            material_title=metadata.title,
            speaker=metadata.speaker,
            event_name=stream_name,
            date=metadata.date.strftime("%d.%m.%Y"),
            source_content=source_content,
        )

        start = time.monotonic()
        try:
            async with ClaudeClient.from_settings(self.settings) as client:
                content, usage = await client.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=self.settings.describe_model,
                )

            elapsed = round(time.monotonic() - start, 2)
            parsed = json.loads(extract_json(content))
            description = parsed.get("description", "")
            short_description = parsed.get("short_description", "")

            tokens_used = TokensUsed(
                input=usage.input_tokens, output=usage.output_tokens
            )
            cost = calculate_cost(
                self.settings.describe_model,
                usage.input_tokens,
                usage.output_tokens,
            )

            logger.info(
                "description_generated",
                extra={
                    "model": self.settings.describe_model,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": cost,
                    "description_len": len(description),
                },
            )

            return DescriptionResult(
                description=description,
                short_description=short_description,
                model_name=self.settings.describe_model,
                tokens_used=tokens_used,
                cost=cost,
                processing_time_sec=elapsed,
            )

        except Exception as e:
            logger.warning(
                "description_generation_failed",
                extra={"error": str(e), "video_id": metadata.video_id},
            )
            return DescriptionResult()

    @staticmethod
    def _build_source_content(
        summary: Summary | None,
        longread: Longread | None,
        story: Story | None,
    ) -> str:
        """Build source content for description generation.

        Priority: Summary (most compact) > Longread/Story markdown.

        Args:
            summary: Condensed summary
            longread: Longread document
            story: Leadership story

        Returns:
            Source content string or empty string
        """
        if summary:
            parts = []
            if summary.essence:
                parts.append(summary.essence)
            if summary.key_concepts:
                parts.append("Ключевые концепции: " + ", ".join(summary.key_concepts))
            if summary.practical_tools:
                parts.append("Инструменты: " + ", ".join(summary.practical_tools))
            if parts:
                return "\n\n".join(parts)

        if longread:
            return longread.to_markdown()

        if story:
            return story.to_markdown()

        return ""

    def _get_stream_name(self, event_type: str, stream: str) -> str:
        """Get full stream name from events config.

        Args:
            event_type: Event type code (e.g., "ПШ")
            stream: Stream code (e.g., "SV"), can be empty

        Returns:
            Full stream name or just event name if stream is empty
        """
        event_types = self.events_config.get("event_types", {})
        event_info = event_types.get(event_type, {})
        event_name = event_info.get("name", event_type)

        if not stream:
            return event_name

        streams = event_info.get("streams", {})
        stream_desc = streams.get(stream, stream)

        return f"{event_name} — {stream_desc}"
