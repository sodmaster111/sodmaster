"""Wrapper for prometheus_client with an offline-friendly fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

try:  # pragma: no cover - exercised only when dependency is available
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST as CONTENT_TYPE_LATEST,
        Counter as Counter,
        Gauge as Gauge,
        Histogram as Histogram,
        Info as Info,
        generate_latest as generate_latest,
    )
except Exception:  # pragma: no cover - fallback for minimal environments
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _MetricRegistry:
        def __init__(self) -> None:
            self._metrics: List["_BaseMetric"] = []

        def register(self, metric: "_BaseMetric") -> None:
            self._metrics.append(metric)

        def collect(self) -> Iterable["_BaseMetric"]:
            return list(self._metrics)

    REGISTRY = _MetricRegistry()

    def _format_labels(label_names: Tuple[str, ...], label_values: Tuple[str, ...]) -> str:
        if not label_names:
            return ""
        parts = [f'{name}="{value}"' for name, value in zip(label_names, label_values)]
        return "{" + ",".join(parts) + "}"

    class _MetricChild:
        def __init__(self, metric: "_BaseMetric", label_values: Tuple[str, ...]):
            self._metric = metric
            self._label_values = label_values

        def inc(self, amount: float = 1.0) -> None:
            raise NotImplementedError

        def observe(self, amount: float) -> None:
            raise NotImplementedError

    class _BaseMetric:
        type_name = "counter"

        def __init__(self, name: str, documentation: str, labelnames: Optional[Iterable[str]] = None):
            self.name = name
            self.documentation = documentation
            self.labelnames: Tuple[str, ...] = tuple(labelnames or ())
            self._children: Dict[Tuple[str, ...], _MetricChild] = {}
            REGISTRY.register(self)

        def labels(self, *args: str, **kwargs: str) -> _MetricChild:
            if args and kwargs:
                raise ValueError("Cannot use both args and kwargs for labels")
            if kwargs:
                label_values = tuple(kwargs[name] for name in self.labelnames)
            else:
                if len(args) != len(self.labelnames):
                    raise ValueError("Incorrect number of labels provided")
                label_values = tuple(args)
            if len(label_values) != len(self.labelnames):
                raise ValueError("Incorrect number of labels provided")
            if label_values not in self._children:
                self._children[label_values] = self._new_child(label_values)
            return self._children[label_values]

        def _new_child(self, label_values: Tuple[str, ...]) -> _MetricChild:
            raise NotImplementedError

        def collect(self) -> List[str]:
            raise NotImplementedError

        def _render_header(self) -> List[str]:
            return [
                f"# HELP {self.name} {self.documentation}",
                f"# TYPE {self.name} {self.type_name}",
            ]

        def render(self) -> List[str]:
            return self._render_header() + self.collect()

    class CounterChild(_MetricChild):
        def __init__(self, metric: "Counter", label_values: Tuple[str, ...]):
            super().__init__(metric, label_values)
            self._value = 0.0

        def inc(self, amount: float = 1.0) -> None:
            self._value += amount
            self._metric._values[self._label_values] = self._value

    class GaugeChild(_MetricChild):
        def __init__(self, metric: "Gauge", label_values: Tuple[str, ...]):
            super().__init__(metric, label_values)
            self._value = 0.0

        def set(self, value: float) -> None:
            self._value = value
            self._metric._values[self._label_values] = self._value

        def inc(self, amount: float = 1.0) -> None:
            self.set(self._value + amount)

        def dec(self, amount: float = 1.0) -> None:
            self.set(self._value - amount)

    class Counter(_BaseMetric):
        type_name = "counter"

        def __init__(self, name: str, documentation: str, labelnames: Optional[Iterable[str]] = None):
            super().__init__(name, documentation, labelnames)
            self._values: Dict[Tuple[str, ...], float] = {}

        def inc(self, amount: float = 1.0) -> None:
            self.labels().inc(amount)

        def _new_child(self, label_values: Tuple[str, ...]) -> CounterChild:
            return CounterChild(self, label_values)

        def collect(self) -> List[str]:
            lines: List[str] = []
            for label_values, value in self._values.items():
                labels = _format_labels(self.labelnames, label_values)
                lines.append(f"{self.name}{labels} {value}")
            return lines

    class Gauge(_BaseMetric):
        type_name = "gauge"

        def __init__(self, name: str, documentation: str, labelnames: Optional[Iterable[str]] = None):
            super().__init__(name, documentation, labelnames)
            self._values: Dict[Tuple[str, ...], float] = {}

        def _new_child(self, label_values: Tuple[str, ...]) -> GaugeChild:
            return GaugeChild(self, label_values)

        def set(self, value: float) -> None:
            self.labels().set(value)

        def inc(self, amount: float = 1.0) -> None:
            self.labels().inc(amount)

        def dec(self, amount: float = 1.0) -> None:
            self.labels().dec(amount)

        def collect(self) -> List[str]:
            lines: List[str] = []
            for label_values, value in self._values.items():
                labels = _format_labels(self.labelnames, label_values)
                lines.append(f"{self.name}{labels} {value}")
            return lines

    class HistogramChild(_MetricChild):
        def __init__(self, metric: "Histogram", label_values: Tuple[str, ...]):
            super().__init__(metric, label_values)
            self.count = 0
            self.total = 0.0

        def observe(self, amount: float) -> None:
            self.count += 1
            self.total += amount
            self._metric._values[self._label_values] = (self.count, self.total)

    class Histogram(_BaseMetric):
        type_name = "histogram"

        def __init__(self, name: str, documentation: str, labelnames: Optional[Iterable[str]] = None):
            super().__init__(name, documentation, labelnames)
            self._values: Dict[Tuple[str, ...], Tuple[int, float]] = {}

        def observe(self, amount: float) -> None:
            self.labels().observe(amount)

        def _new_child(self, label_values: Tuple[str, ...]) -> HistogramChild:
            return HistogramChild(self, label_values)

        def collect(self) -> List[str]:
            lines: List[str] = []
            for label_values, (count, total) in self._values.items():
                labels = _format_labels(self.labelnames, label_values)
                lines.append(f"{self.name}_count{labels} {count}")
                lines.append(f"{self.name}_sum{labels} {total}")
            return lines

    @dataclass
    class _InfoValue:
        labels: Tuple[str, ...]
        value: float = 1.0

    class Info(_BaseMetric):
        type_name = "gauge"

        def __init__(self, name: str, documentation: str):
            super().__init__(name, documentation, [])
            self._info: Optional[_InfoValue] = None

        def info(self, data: Dict[str, str]) -> None:
            labels = tuple(f'{key}="{value}"' for key, value in sorted(data.items()))
            self._info = _InfoValue(labels=labels)

        def collect(self) -> List[str]:
            if self._info is None:
                return []
            label_str = "{" + ",".join(self._info.labels) + "}" if self._info.labels else ""
            return [f"{self.name}{label_str} {self._info.value}"]

    def generate_latest() -> bytes:
        lines: List[str] = []
        for metric in REGISTRY.collect():
            lines.extend(metric.render())
        return ("\n".join(lines) + "\n").encode("utf-8")


__all__ = [
    "CONTENT_TYPE_LATEST",
    "Counter",
    "Gauge",
    "Histogram",
    "Info",
    "generate_latest",
]
