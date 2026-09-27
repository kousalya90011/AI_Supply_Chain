from __future__ import annotations

from typing import Any, Callable


class AnalyticsRegistry:
    """
    Central registry for deterministic supply-chain analytics.

    A registered analytics implementation can be:

    1. A normal callable/function
    2. An object exposing execute()
    3. An object exposing analyze()
    4. An object exposing run()
    """

    def __init__(self):
        self._registry: dict[str, Any] = {}

    def register(
        self,
        metric: str,
        analyzer: Any,
    ) -> None:
        """
        Register an analytics implementation.

        Supported implementations:

            callable
            object.execute()
            object.analyze()
            object.run()
        """

        if not metric:
            raise ValueError(
                "Analytics metric cannot be empty."
            )

        if not self._is_valid_analyzer(analyzer):
            raise TypeError(
                f"Analyzer for '{metric}' must be "
                "callable or provide execute(), "
                "analyze(), or run()."
            )

        self._registry[metric] = analyzer

    def get(
        self,
        metric: str,
    ) -> Any | None:
        return self._registry.get(metric)

    def has(
        self,
        metric: str,
    ) -> bool:
        return metric in self._registry

    def available_metrics(self) -> list[str]:
        return sorted(
            self._registry.keys()
        )

    def unregister(
        self,
        metric: str,
    ) -> None:
        self._registry.pop(
            metric,
            None,
        )

    def clear(self) -> None:
        self._registry.clear()

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(
        self,
        metric: str,
    ) -> bool:
        return self.has(metric)

    def __repr__(self) -> str:
        return (
            "AnalyticsRegistry("
            f"metrics={self.available_metrics()}"
            ")"
        )

    @staticmethod
    def _is_valid_analyzer(
        analyzer: Any,
    ) -> bool:
        """
        Check whether the registered analytics
        implementation can actually be executed.
        """

        if callable(analyzer):
            return True

        if hasattr(analyzer, "execute") and callable(
            analyzer.execute
        ):
            return True

        if hasattr(analyzer, "analyze") and callable(
            analyzer.analyze
        ):
            return True

        if hasattr(analyzer, "run") and callable(
            analyzer.run
        ):
            return True

        return False