from typing import Protocol

from edgerunners_contracts import Assessment


class ContextDetector(Protocol):
    async def assess(self, turns: list[tuple[str, str]]) -> Assessment:
        """Assess (turn_id, text) pairs without blocking audio ingestion."""
        ...


class DetectorUnavailable(RuntimeError):
    pass


class UnconfiguredDetector:
    async def assess(self, turns: list[tuple[str, str]]) -> Assessment:
        raise DetectorUnavailable("No contextual AI provider is configured")
