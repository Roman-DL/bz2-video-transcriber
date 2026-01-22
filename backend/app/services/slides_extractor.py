"""
Slides text extraction service.

Extracts structured text from presentation slides using Claude Vision API.
Supports images (JPEG, PNG, WebP) and PDF files.

v0.50+: Initial implementation for slides integration.
"""

import base64
import logging
import re
import time
from typing import Any

from app.config import Settings, load_prompt
from app.models.schemas import (
    PromptOverrides,
    SlideInput,
    SlidesExtractionResult,
    TokensUsed,
)
from app.services.ai_clients import ClaudeClient
from app.services.ai_clients.base import ChatUsage
from app.utils import calculate_cost, pdf_to_images

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Default model for slides extraction (fast and cheap)
DEFAULT_SLIDES_MODEL = "claude-haiku-4-5"

# Batch size for processing slides
# Limits context size per API call
DEFAULT_BATCH_SIZE = 5

# Supported image MIME types
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class SlidesExtractor:
    """
    Slides text extraction using Claude Vision API.

    Processes slides in batches to manage context size.
    Supports images and PDFs (converted to images).

    Example:
        async with ClaudeClient.from_settings(settings) as client:
            extractor = SlidesExtractor(client, settings)
            result = await extractor.extract(slides)
            print(result.extracted_text)
    """

    def __init__(
        self,
        ai_client: ClaudeClient,
        settings: Settings,
        prompt_overrides: PromptOverrides | None = None,
    ):
        """
        Initialize slides extractor.

        Args:
            ai_client: Claude client with vision support
            settings: Application settings
            prompt_overrides: Optional prompt file overrides
        """
        self.ai_client = ai_client
        self.settings = settings
        self.batch_size = DEFAULT_BATCH_SIZE

        # Load prompts with optional overrides
        overrides = prompt_overrides or PromptOverrides()
        self.system_prompt = load_prompt("slides", overrides.system or "system", settings)
        self.user_prompt = load_prompt("slides", overrides.user or "user", settings)

        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    async def extract(
        self,
        slides: list[SlideInput],
        model: str | None = None,
    ) -> SlidesExtractionResult:
        """
        Extract text from slides using vision API.

        Processes slides in batches and combines results.

        Args:
            slides: List of slides to process
            model: LLM model override (default: claude-haiku-4-5)

        Returns:
            SlidesExtractionResult with extracted text and metrics
        """
        start_time = time.time()
        model = model or DEFAULT_SLIDES_MODEL

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Prepare images from slides (handle PDF conversion)
        images = self._prepare_images(slides)
        total_slides = len(images)

        logger.info(f"Extracting text from {total_slides} slides using {model}")

        # Process in batches
        all_texts = []
        for batch_start in range(0, total_slides, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_slides)
            batch = images[batch_start:batch_end]

            logger.debug(f"Processing batch {batch_start + 1}-{batch_end}/{total_slides}")

            batch_text = await self._process_batch(
                batch,
                batch_start + 1,
                total_slides,
                model,
            )
            all_texts.append(batch_text)

        # Combine results
        extracted_text = "\n\n---\n\n".join(all_texts)

        # Calculate metrics
        chars_count = len(extracted_text)
        words_count = len(extracted_text.split())
        tables_count = self._count_tables(extracted_text)

        elapsed = time.time() - start_time

        # Calculate cost
        tokens_used = None
        cost = None
        if self._total_input_tokens > 0 or self._total_output_tokens > 0:
            tokens_used = TokensUsed(
                input=self._total_input_tokens,
                output=self._total_output_tokens,
            )
            cost = calculate_cost(
                model,
                self._total_input_tokens,
                self._total_output_tokens,
            )

        result = SlidesExtractionResult(
            extracted_text=extracted_text,
            slides_count=total_slides,
            chars_count=chars_count,
            words_count=words_count,
            tables_count=tables_count,
            model=model,
            tokens_used=tokens_used,
            cost=cost,
            processing_time_sec=elapsed,
        )

        cost_str = f"cost=${cost:.4f} | " if cost else ""
        logger.info(
            f"Slides extraction complete: {total_slides} slides, "
            f"{chars_count} chars, {tables_count} tables, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | slides | "
            f"slides={total_slides} | "
            f"chars={chars_count} | "
            f"tables={tables_count} | "
            f"tokens={self._total_input_tokens}+{self._total_output_tokens} | "
            f"{cost_str}time={elapsed:.1f}s"
        )

        return result

    def _prepare_images(
        self,
        slides: list[SlideInput],
    ) -> list[tuple[bytes, str, str]]:
        """
        Prepare images from slides, converting PDFs to images.

        Args:
            slides: Input slides

        Returns:
            List of (image_bytes, media_type, filename) tuples
        """
        images = []

        for slide in slides:
            data = base64.b64decode(slide.data)

            if slide.content_type == "application/pdf":
                # Convert PDF pages to images
                for png_bytes, page_filename in pdf_to_images(data):
                    # Use original filename + page number
                    base_name = slide.filename.rsplit(".", 1)[0]
                    filename = f"{base_name}_{page_filename}"
                    images.append((png_bytes, "image/png", filename))
            elif slide.content_type in IMAGE_MIME_TYPES:
                images.append((data, slide.content_type, slide.filename))
            else:
                logger.warning(f"Unsupported content type: {slide.content_type}")
                continue

        return images

    async def _process_batch(
        self,
        images: list[tuple[bytes, str, str]],
        start_num: int,
        total: int,
        model: str,
    ) -> str:
        """
        Process a batch of images using vision API.

        Args:
            images: List of (image_bytes, media_type, filename) tuples
            start_num: Starting slide number (1-based)
            total: Total number of slides
            model: LLM model to use

        Returns:
            Extracted text for this batch
        """
        # Build message content with images
        content: list[dict[str, Any]] = []

        # Add text prompt
        batch_prompt = self._build_batch_prompt(start_num, len(images), total)
        content.append({"type": "text", "text": batch_prompt})

        # Add images
        for idx, (img_bytes, media_type, filename) in enumerate(images):
            slide_num = start_num + idx
            # Add slide label
            content.append({
                "type": "text",
                "text": f"\n### Слайд {slide_num}: {filename}\n",
            })
            # Add image
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(img_bytes).decode("utf-8"),
                },
            })

        # Send to Claude
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content},
        ]

        response, usage = await self.ai_client.chat(
            messages=messages,
            model=model,
            temperature=0.3,  # Lower temperature for structured extraction
            num_predict=4096,
        )

        # Track tokens
        self._total_input_tokens += usage.input_tokens
        self._total_output_tokens += usage.output_tokens

        return response

    def _build_batch_prompt(
        self,
        start_num: int,
        batch_size: int,
        total: int,
    ) -> str:
        """
        Build prompt for batch processing.

        Args:
            start_num: Starting slide number
            batch_size: Number of slides in batch
            total: Total number of slides

        Returns:
            Formatted prompt text
        """
        end_num = start_num + batch_size - 1
        return (
            f"{self.user_prompt}\n\n"
            f"Обработай слайды {start_num}-{end_num} из {total}.\n"
            f"Для каждого слайда извлеки текст и структурируй данные."
        )

    def _count_tables(self, text: str) -> int:
        """
        Count markdown tables in text.

        Args:
            text: Extracted text

        Returns:
            Number of tables detected
        """
        # Count table separator lines (|---|---|)
        table_pattern = r"\|[-:]+\|[-:|\s]+"
        matches = re.findall(table_pattern, text)
        return len(matches)


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import os
    import sys

    async def run_tests():
        """Test slides extractor."""
        print("\nTesting SlidesExtractor...\n")

        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY not set, skipping tests")
            return 0

        from app.config import get_settings

        settings = get_settings()

        # Test 1: Create minimal test image
        print("Test 1: Prepare images from PDF...", end=" ")
        try:
            import fitz

            # Create test PDF
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Test slide with table:")
            page.insert_text((72, 100), "| Col1 | Col2 |")
            page.insert_text((72, 120), "|------|------|")
            page.insert_text((72, 140), "| A    | B    |")
            pdf_bytes = doc.tobytes()
            doc.close()

            # Create SlideInput
            slide = SlideInput(
                filename="test.pdf",
                content_type="application/pdf",
                data=base64.b64encode(pdf_bytes).decode("utf-8"),
            )

            async with ClaudeClient.from_settings(settings) as client:
                extractor = SlidesExtractor(client, settings)
                images = extractor._prepare_images([slide])

            assert len(images) == 1
            assert images[0][1] == "image/png"
            print("OK")
            print(f"  Converted to {len(images)} image(s)")

        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        # Test 2: Full extraction (requires API)
        print("\nTest 2: Full extraction with minimal image...", end=" ")
        try:
            # Create minimal PNG with text
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 100), "Slide Title: Test Product")
            page.insert_text((72, 140), "Price: $99.99")
            page.insert_text((72, 180), "Features:")
            page.insert_text((90, 200), "- Feature 1")
            page.insert_text((90, 220), "- Feature 2")
            pdf_bytes = doc.tobytes()
            doc.close()

            slide = SlideInput(
                filename="product.pdf",
                content_type="application/pdf",
                data=base64.b64encode(pdf_bytes).decode("utf-8"),
            )

            async with ClaudeClient.from_settings(settings) as client:
                extractor = SlidesExtractor(client, settings)
                result = await extractor.extract([slide])

            assert result.slides_count == 1
            assert result.chars_count > 0
            assert result.extracted_text

            print("OK")
            print(f"  Slides: {result.slides_count}")
            print(f"  Chars: {result.chars_count}")
            print(f"  Words: {result.words_count}")
            print(f"  Time: {result.processing_time_sec:.1f}s")
            if result.tokens_used:
                print(f"  Tokens: {result.tokens_used.input} in / {result.tokens_used.output} out")
            if result.cost:
                print(f"  Cost: ${result.cost:.4f}")

        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
