"""
Stage abstraction for pipeline processing.

Provides base classes for defining processing stages that can be composed
into pipelines. Each stage has:
- A unique name for identification
- Dependencies on other stages (defined in depends_on)
- Optional flag for stages that can be skipped
- Execute method that performs the actual work

Example:
    class TelegramSummaryStage(BaseStage):
        name = "telegram_summary"
        depends_on = ["longread"]
        optional = True

        async def execute(self, context: StageContext) -> TelegramSummary:
            longread = context.get_result("longread")
            # Generate summary...
            return TelegramSummary(...)

    # Register and use
    registry.register(TelegramSummaryStage())
    stages = registry.build_pipeline(["parse", "transcribe", ..., "telegram_summary"])
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from app.models.schemas import ProcessingStatus


T = TypeVar("T", bound=BaseModel)


class StageError(Exception):
    """Error during stage execution.

    Attributes:
        stage_name: Name of the stage that failed
        message: Error description
        cause: Original exception (if any)
    """

    def __init__(
        self,
        stage_name: str,
        message: str,
        cause: Exception | None = None,
    ):
        self.stage_name = stage_name
        self.message = message
        self.cause = cause
        super().__init__(f"[{stage_name}] {message}")


@dataclass
class StageContext:
    """Context passed between pipeline stages.

    Holds results from previous stages and provides type-safe access.
    Immutable once created - stages add results by returning new context.

    Attributes:
        results: Dictionary of stage_name -> result mapping
        metadata: Shared metadata accessible by all stages

    Example:
        context = StageContext()
        context = context.with_result("parse", metadata)
        context = context.with_result("transcribe", (raw_transcript, audio_path))

        # Later stages access previous results
        metadata = context.get_result("parse")
        raw, audio = context.get_result("transcribe")
    """

    results: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_result(self, stage_name: str) -> Any:
        """Get result from a completed stage.

        Args:
            stage_name: Name of the stage whose result to retrieve

        Returns:
            Result from the specified stage

        Raises:
            KeyError: If stage result not found
        """
        if stage_name not in self.results:
            raise KeyError(
                f"Stage '{stage_name}' result not found. "
                f"Available: {list(self.results.keys())}"
            )
        return self.results[stage_name]

    def has_result(self, stage_name: str) -> bool:
        """Check if a stage result exists.

        Args:
            stage_name: Name of the stage to check

        Returns:
            True if result exists, False otherwise
        """
        return stage_name in self.results

    def with_result(self, stage_name: str, result: Any) -> "StageContext":
        """Create new context with added result.

        Args:
            stage_name: Name of the stage
            result: Result to store

        Returns:
            New StageContext with the added result
        """
        new_results = {**self.results, stage_name: result}
        return StageContext(results=new_results, metadata=self.metadata)

    def with_metadata(self, key: str, value: Any) -> "StageContext":
        """Create new context with added metadata.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            New StageContext with the added metadata
        """
        new_metadata = {**self.metadata, key: value}
        return StageContext(results=self.results, metadata=new_metadata)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)


class BaseStage(ABC):
    """Abstract base class for pipeline stages.

    Subclasses must implement:
    - name: Unique stage identifier
    - execute(): Async method that performs the work

    Optional overrides:
    - depends_on: List of stage names this stage depends on
    - optional: Whether stage can be skipped
    - status: ProcessingStatus for progress tracking
    - estimate_time(): Time estimation for progress display

    Example:
        class CleanStage(BaseStage):
            name = "clean"
            depends_on = ["transcribe"]
            status = ProcessingStatus.CLEANING

            async def execute(self, context: StageContext) -> CleanedTranscript:
                raw, _ = context.get_result("transcribe")
                metadata = context.get_result("parse")
                return await self.cleaner.clean(raw, metadata)
    """

    name: str
    depends_on: list[str] = []
    optional: bool = False
    status: ProcessingStatus | None = None

    @abstractmethod
    async def execute(self, context: StageContext) -> Any:
        """Execute the stage.

        Args:
            context: Context with results from previous stages

        Returns:
            Stage result (Pydantic model or tuple of models)

        Raises:
            StageError: If execution fails
        """
        pass

    def should_skip(self, context: StageContext) -> bool:
        """Check if stage should be skipped based on context.

        Override in subclasses for conditional stage execution.
        Used for content_type branching (e.g., skip LongreadStage for leadership).

        Args:
            context: Context with results from previous stages

        Returns:
            True if stage should be skipped, False otherwise
        """
        return False

    def estimate_time(self, input_size: int) -> float:
        """Estimate execution time in seconds.

        Override in subclasses for accurate progress display.

        Args:
            input_size: Size of input (chars, bytes, etc.)

        Returns:
            Estimated time in seconds
        """
        return 5.0  # Default estimate

    def validate_context(self, context: StageContext) -> None:
        """Validate that all dependencies are satisfied.

        Args:
            context: Context to validate

        Raises:
            StageError: If dependencies are missing
        """
        missing = [dep for dep in self.depends_on if not context.has_result(dep)]
        if missing:
            raise StageError(
                self.name,
                f"Missing dependencies: {missing}",
            )


class StageRegistry:
    """Central registry for pipeline stages.

    Manages stage registration and builds execution order based on
    dependency graph.

    Example:
        registry = StageRegistry()
        registry.register(ParseStage())
        registry.register(TranscribeStage())
        registry.register(CleanStage())

        # Build pipeline for specific stages
        stages = registry.build_pipeline(["parse", "transcribe", "clean"])

        # Or get all registered stages
        all_stages = registry.get_all()
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._stages: dict[str, BaseStage] = {}

    def register(self, stage: BaseStage) -> None:
        """Register a stage.

        Args:
            stage: Stage instance to register

        Raises:
            ValueError: If stage with same name already registered
        """
        if stage.name in self._stages:
            raise ValueError(f"Stage '{stage.name}' already registered")
        self._stages[stage.name] = stage

    def get(self, name: str) -> BaseStage:
        """Get stage by name.

        Args:
            name: Stage name

        Returns:
            Registered stage instance

        Raises:
            KeyError: If stage not found
        """
        if name not in self._stages:
            raise KeyError(
                f"Stage '{name}' not found. "
                f"Available: {list(self._stages.keys())}"
            )
        return self._stages[name]

    def get_all(self) -> list[BaseStage]:
        """Get all registered stages in dependency order.

        Returns:
            List of stages sorted by dependencies
        """
        return self._topological_sort(list(self._stages.keys()))

    def build_pipeline(self, stage_names: list[str]) -> list[BaseStage]:
        """Build ordered pipeline from stage names.

        Resolves dependencies and returns stages in execution order.

        Args:
            stage_names: List of stage names to include

        Returns:
            List of stages in execution order

        Raises:
            KeyError: If any stage not found
            ValueError: If circular dependency detected
        """
        # Validate all stages exist
        for name in stage_names:
            if name not in self._stages:
                raise KeyError(f"Stage '{name}' not found")

        # Expand dependencies
        all_needed = self._expand_dependencies(stage_names)

        # Topological sort
        return self._topological_sort(all_needed)

    def _expand_dependencies(self, stage_names: list[str]) -> set[str]:
        """Expand stage list to include all dependencies.

        Args:
            stage_names: Initial list of stages

        Returns:
            Set of all stages including dependencies
        """
        needed: set[str] = set()
        stack = list(stage_names)

        while stack:
            name = stack.pop()
            if name in needed:
                continue
            needed.add(name)

            stage = self._stages.get(name)
            if stage:
                for dep in stage.depends_on:
                    if dep not in needed:
                        stack.append(dep)

        return needed

    def _topological_sort(self, stage_names: list[str]) -> list[BaseStage]:
        """Sort stages by dependencies using Kahn's algorithm.

        Args:
            stage_names: Stages to sort

        Returns:
            Stages in dependency order

        Raises:
            ValueError: If circular dependency detected
        """
        # Build adjacency list and in-degree count
        in_degree: dict[str, int] = {name: 0 for name in stage_names}
        graph: dict[str, list[str]] = {name: [] for name in stage_names}

        for name in stage_names:
            stage = self._stages.get(name)
            if stage:
                for dep in stage.depends_on:
                    if dep in stage_names:
                        graph[dep].append(name)
                        in_degree[name] += 1

        # Start with nodes that have no dependencies
        queue = [name for name in stage_names if in_degree[name] == 0]
        result: list[BaseStage] = []

        while queue:
            # Sort queue for deterministic order
            queue.sort()
            name = queue.pop(0)
            result.append(self._stages[name])

            for neighbor in graph[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(stage_names):
            processed = {s.name for s in result}
            remaining = set(stage_names) - processed
            raise ValueError(
                f"Circular dependency detected among stages: {remaining}"
            )

        return result

    def __contains__(self, name: str) -> bool:
        """Check if stage is registered."""
        return name in self._stages

    def __len__(self) -> int:
        """Return number of registered stages."""
        return len(self._stages)


# Global registry instance
_default_registry: StageRegistry | None = None


def get_registry() -> StageRegistry:
    """Get or create the default stage registry.

    Returns:
        Global StageRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = StageRegistry()
    return _default_registry


def register_stage(stage: BaseStage) -> BaseStage:
    """Decorator/function to register a stage in the default registry.

    Can be used as decorator:
        @register_stage
        class MyStage(BaseStage):
            ...

    Or as function:
        register_stage(MyStage())

    Args:
        stage: Stage class or instance

    Returns:
        The registered stage
    """
    registry = get_registry()
    if isinstance(stage, type):
        # It's a class, instantiate it
        instance = stage()
        registry.register(instance)
        return instance
    else:
        # It's an instance
        registry.register(stage)
        return stage


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    print("\nRunning Stage abstraction tests...\n")
    errors = []

    # Test 1: StageContext basic operations
    print("Test 1: StageContext basic operations...", end=" ")
    try:
        ctx = StageContext()
        assert not ctx.has_result("test")

        ctx2 = ctx.with_result("test", {"data": 1})
        assert ctx2.has_result("test")
        assert ctx2.get_result("test") == {"data": 1}

        # Original context unchanged
        assert not ctx.has_result("test")

        ctx3 = ctx2.with_metadata("key", "value")
        assert ctx3.get_metadata("key") == "value"
        assert ctx3.get_metadata("missing", "default") == "default"

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("StageContext", e))

    # Test 2: StageContext missing result
    print("Test 2: StageContext missing result...", end=" ")
    try:
        ctx = StageContext()
        try:
            ctx.get_result("nonexistent")
            print("FAILED: Should have raised KeyError")
            errors.append(("Missing result", "No KeyError"))
        except KeyError as e:
            assert "nonexistent" in str(e)
            print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Missing result", e))

    # Test 3: StageRegistry registration
    print("Test 3: StageRegistry registration...", end=" ")
    try:
        # Create test stage
        class TestStage(BaseStage):
            name = "test_stage"
            depends_on = []

            async def execute(self, context: StageContext) -> dict:
                return {"executed": True}

        registry = StageRegistry()
        stage = TestStage()
        registry.register(stage)

        assert "test_stage" in registry
        assert registry.get("test_stage") is stage
        assert len(registry) == 1

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Registration", e))

    # Test 4: Duplicate registration
    print("Test 4: Duplicate registration...", end=" ")
    try:
        registry = StageRegistry()

        class DupStage(BaseStage):
            name = "dup"

            async def execute(self, context):
                pass

        registry.register(DupStage())
        try:
            registry.register(DupStage())
            print("FAILED: Should have raised ValueError")
            errors.append(("Duplicate", "No ValueError"))
        except ValueError as e:
            assert "already registered" in str(e)
            print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Duplicate", e))

    # Test 5: Dependency resolution
    print("Test 5: Dependency resolution...", end=" ")
    try:
        registry = StageRegistry()

        class StageA(BaseStage):
            name = "a"
            depends_on = []

            async def execute(self, context):
                return "a"

        class StageB(BaseStage):
            name = "b"
            depends_on = ["a"]

            async def execute(self, context):
                return "b"

        class StageC(BaseStage):
            name = "c"
            depends_on = ["b"]

            async def execute(self, context):
                return "c"

        registry.register(StageA())
        registry.register(StageB())
        registry.register(StageC())

        # Build pipeline with just "c" - should include a, b, c
        pipeline = registry.build_pipeline(["c"])
        names = [s.name for s in pipeline]
        assert names == ["a", "b", "c"], f"Expected ['a', 'b', 'c'], got {names}"

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Dependencies", e))

    # Test 6: Circular dependency detection
    print("Test 6: Circular dependency detection...", end=" ")
    try:
        registry = StageRegistry()

        class CycleA(BaseStage):
            name = "cycle_a"
            depends_on = ["cycle_b"]

            async def execute(self, context):
                pass

        class CycleB(BaseStage):
            name = "cycle_b"
            depends_on = ["cycle_a"]

            async def execute(self, context):
                pass

        registry.register(CycleA())
        registry.register(CycleB())

        try:
            registry.build_pipeline(["cycle_a", "cycle_b"])
            print("FAILED: Should have raised ValueError")
            errors.append(("Circular", "No ValueError"))
        except ValueError as e:
            assert "Circular" in str(e)
            print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Circular", e))

    # Test 7: Stage execution
    print("Test 7: Stage execution...", end=" ")
    try:

        class ExecuteStage(BaseStage):
            name = "execute_test"
            depends_on = []

            async def execute(self, context: StageContext) -> dict:
                return {"result": context.get_metadata("input", 0) * 2}

        stage = ExecuteStage()
        ctx = StageContext().with_metadata("input", 21)

        result = asyncio.run(stage.execute(ctx))
        assert result == {"result": 42}, f"Expected 42, got {result}"

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Execution", e))

    # Test 8: validate_context
    print("Test 8: validate_context...", end=" ")
    try:

        class ValidateStage(BaseStage):
            name = "validate_test"
            depends_on = ["dep1", "dep2"]

            async def execute(self, context):
                pass

        stage = ValidateStage()

        # Context without dependencies
        ctx = StageContext()
        try:
            stage.validate_context(ctx)
            print("FAILED: Should have raised StageError")
            errors.append(("Validate", "No StageError"))
        except StageError as e:
            assert "dep1" in str(e) or "dep2" in str(e)

        # Context with dependencies
        ctx = ctx.with_result("dep1", 1).with_result("dep2", 2)
        stage.validate_context(ctx)  # Should not raise

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Validate", e))

    # Test 9: StageError
    print("Test 9: StageError...", end=" ")
    try:
        cause = ValueError("original")
        error = StageError("test_stage", "something failed", cause)

        assert error.stage_name == "test_stage"
        assert error.message == "something failed"
        assert error.cause is cause
        assert "[test_stage]" in str(error)

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("StageError", e))

    # Summary
    print("\n" + "=" * 40)
    if errors:
        print(f"FAILED: {len(errors)} test(s)")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
