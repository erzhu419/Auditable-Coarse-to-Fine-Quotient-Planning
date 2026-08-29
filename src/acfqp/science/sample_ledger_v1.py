"""Typed evidence ledger for matched reinforcement-learning experiments.

The five evidence classes and four lanes follow
``specs/SAMPLE_EFFICIENCY_PROTOCOL.md``.  Replay-buffer draws and optimizer
work are diagnostics, not environment samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class EvidenceClass(str, Enum):
    ENVIRONMENT_INTERACTION = "ENVIRONMENT_INTERACTION"
    GENERATIVE_ORACLE_SAMPLE = "GENERATIVE_ORACLE_SAMPLE"
    EXACT_KERNEL_QUERY = "EXACT_KERNEL_QUERY"
    OFFLINE_LOGGED_OBSERVATION = "OFFLINE_LOGGED_OBSERVATION"
    SYNTHETIC_MODEL_ROLLOUT = "SYNTHETIC_MODEL_ROLLOUT"


class EvidenceLane(str, Enum):
    OFFLINE_SOURCE = "offline_source"
    ONLINE_TARGET = "online_target"
    OPERATIONAL_QUERY = "operational_query"
    STANDALONE_EVALUATION = "standalone_evaluation"


DIAGNOSTIC_COUNTERS = (
    "evaluation_episodes",
    "gradient_updates",
    "policy_forward_passes",
    "replay_buffer_draws",
    "simulator_transition_calls",
    "target_network_syncs",
    "training_episodes",
)


class SampleLedgerV1Error(ValueError):
    """A sample-ledger class, lane, count, or document is invalid."""


def _zero_evidence_counts() -> dict[tuple[EvidenceLane, EvidenceClass], int]:
    return {
        (lane, evidence_class): 0
        for lane in EvidenceLane
        for evidence_class in EvidenceClass
    }


@dataclass(slots=True)
class SampleLedgerV1:
    """Mutable during one run and serialized with all native-zero rows."""

    _evidence: dict[tuple[EvidenceLane, EvidenceClass], int] = field(
        default_factory=_zero_evidence_counts,
        repr=False,
    )
    _diagnostics: dict[str, int] = field(
        default_factory=lambda: {name: 0 for name in DIAGNOSTIC_COUNTERS},
        repr=False,
    )

    def charge(
        self,
        evidence_class: EvidenceClass,
        lane: EvidenceLane,
        count: int = 1,
    ) -> None:
        if type(evidence_class) is not EvidenceClass:
            raise SampleLedgerV1Error("evidence class must be exact")
        if type(lane) is not EvidenceLane:
            raise SampleLedgerV1Error("evidence lane must be exact")
        if type(count) is not int or count < 0:
            raise SampleLedgerV1Error("evidence count must be a nonnegative integer")
        self._evidence[(lane, evidence_class)] += count

    def increment_diagnostic(self, name: str, count: int = 1) -> None:
        if name not in self._diagnostics:
            raise SampleLedgerV1Error("unknown diagnostic counter")
        if type(count) is not int or count < 0:
            raise SampleLedgerV1Error("diagnostic count must be nonnegative")
        self._diagnostics[name] += count

    def evidence_count(
        self, evidence_class: EvidenceClass, lane: EvidenceLane
    ) -> int:
        if type(evidence_class) is not EvidenceClass or type(lane) is not EvidenceLane:
            raise SampleLedgerV1Error("evidence lookup must use exact enums")
        return self._evidence[(lane, evidence_class)]

    def to_document(self) -> dict[str, Any]:
        rows = [
            {
                "lane": lane.value,
                "evidence_class": evidence_class.value,
                "count": self._evidence[(lane, evidence_class)],
                "native_zero": self._evidence[(lane, evidence_class)] == 0,
            }
            for lane in EvidenceLane
            for evidence_class in EvidenceClass
        ]
        return {
            "schema": "acfqp.science.sample_ledger.v1",
            "evidence_rows": rows,
            "evidence_row_count": len(rows),
            "all_five_classes_reported_in_all_four_lanes": len(rows) == 20,
            "diagnostic_counters": dict(sorted(self._diagnostics.items())),
            "replay_and_optimizer_work_excluded_from_environment_interactions": True,
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "SampleLedgerV1":
        if type(document) is not dict:
            raise SampleLedgerV1Error("sample ledger must be a plain object")
        if set(document) != {
            "schema",
            "evidence_rows",
            "evidence_row_count",
            "all_five_classes_reported_in_all_four_lanes",
            "diagnostic_counters",
            "replay_and_optimizer_work_excluded_from_environment_interactions",
        }:
            raise SampleLedgerV1Error("sample-ledger fields changed")
        rows = document["evidence_rows"]
        diagnostics = document["diagnostic_counters"]
        if (
            document["schema"] != "acfqp.science.sample_ledger.v1"
            or type(rows) is not list
            or len(rows) != 20
            or document["evidence_row_count"] != 20
            or document["all_five_classes_reported_in_all_four_lanes"] is not True
            or type(diagnostics) is not dict
            or tuple(sorted(diagnostics)) != DIAGNOSTIC_COUNTERS
            or document[
                "replay_and_optimizer_work_excluded_from_environment_interactions"
            ]
            is not True
        ):
            raise SampleLedgerV1Error("sample-ledger contract changed")
        ledger = cls()
        seen: set[tuple[EvidenceLane, EvidenceClass]] = set()
        for row in rows:
            if type(row) is not dict or set(row) != {
                "lane",
                "evidence_class",
                "count",
                "native_zero",
            }:
                raise SampleLedgerV1Error("evidence row changed")
            try:
                lane = EvidenceLane(row["lane"])
                evidence_class = EvidenceClass(row["evidence_class"])
            except (TypeError, ValueError) as error:
                raise SampleLedgerV1Error("unknown evidence row authority") from error
            count = row["count"]
            key = (lane, evidence_class)
            if (
                key in seen
                or type(count) is not int
                or count < 0
                or row["native_zero"] is not (count == 0)
            ):
                raise SampleLedgerV1Error("evidence row count changed")
            seen.add(key)
            ledger._evidence[key] = count
        if seen != set(_zero_evidence_counts()):
            raise SampleLedgerV1Error("evidence matrix is incomplete")
        for name, count in diagnostics.items():
            if type(count) is not int or count < 0:
                raise SampleLedgerV1Error("diagnostic count changed")
            ledger._diagnostics[name] = count
        return ledger


__all__ = (
    "DIAGNOSTIC_COUNTERS",
    "EvidenceClass",
    "EvidenceLane",
    "SampleLedgerV1",
    "SampleLedgerV1Error",
)
