"""Plug-ins that never warn: the default until a real phrase engine and detector are plugged in."""

from __future__ import annotations

from ..adapter import PluginOptions, detector, phrase_engine
from ..schemas import AssessmentContext, Turn


@phrase_engine("none")
class NoPhrases:
    def __init__(self, options: PluginOptions) -> None:
        pass

    def match(self, turn: Turn) -> None:
        return None


@detector("none")
class NoDetector:
    def __init__(self, options: PluginOptions) -> None:
        pass

    async def assess(self, context: AssessmentContext) -> None:
        return None
