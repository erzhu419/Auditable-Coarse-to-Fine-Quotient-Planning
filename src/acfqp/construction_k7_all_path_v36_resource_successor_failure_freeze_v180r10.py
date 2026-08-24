"""Exact V180r10 failure and the complete retained V36 accounting tree."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r10 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = "6e313718e2ac29c76f47d4c3d38d0eddef2140d1ed1be5400142ffd541fa6fa9"
EXPECTED_CANONICAL_BYTE_COUNT = 696
EXPECTED_CANONICAL_SHA256 = "14d939c2d038cb81b09d8a191ce4697e94235c8f956092ec2a0606b2ead8c39c"
EXPECTED_OUTPUT_FACTS: tuple[dict[str, Any], ...] = (
    {"relative_path": "campaign-aggregation.json", "byte_count": 210070, "sha256": "c1987ccac3733829df673b65c9200680d3ceaa8c3ee33775f6cadfc70841b2b0"},
    {"relative_path": "episodes/episode-0000-evaluation.json", "byte_count": 207958, "sha256": "e8fd1f16789f45ec9bf25a8eca236a7c14beed874895a8ffb9f50e1e1a831647"},
    {"relative_path": "episodes/episode-0000-execution-operational.json", "byte_count": 221969, "sha256": "cbc419ab34c0d954fd191a43fedc26430cb5da71515db8a7e9628d0962778a48"},
    {"relative_path": "episodes/episode-0000-planning-operational.json", "byte_count": 571402, "sha256": "700f9a10a2eb84fb54ab61c89c094140c39a132a564aff46e90270c415c0f320"},
    {"relative_path": "episodes/episode-0001-evaluation.json", "byte_count": 207958, "sha256": "7a8b6c2527a6095abf89741b17f8f8c19ca452f276d3951808c0546ec1333039"},
    {"relative_path": "episodes/episode-0001-execution-operational.json", "byte_count": 221969, "sha256": "06143438195cca02e864962a96c127a52e24c4f52d98a221fa602359b5d58e04"},
    {"relative_path": "episodes/episode-0001-planning-operational.json", "byte_count": 571510, "sha256": "c470877a8948e6228733fb260b5ee10e0ebe653a111c426086246ee372066cea"},
    {"relative_path": "episodes/episode-0002-evaluation.json", "byte_count": 207958, "sha256": "acafa284f7fd484aff6e8528ce037035c8b3066e433b56319f0436b9a5fc47f7"},
    {"relative_path": "episodes/episode-0002-execution-operational.json", "byte_count": 221969, "sha256": "dab6c28fbe7e508858141c43fd904d032d3ea1af6903ade849119a22e57b6d6e"},
    {"relative_path": "episodes/episode-0002-planning-operational.json", "byte_count": 571430, "sha256": "3a82e4d1c28e14ffc5c62bc4d097063141b5a085f5944a8064cf293721a85a53"},
    {"relative_path": "episodes/episode-0003-evaluation.json", "byte_count": 207958, "sha256": "84eb2ee7118b169f2684dda62835351b6a5dfb21b2ea13a2484420da49d969d1"},
    {"relative_path": "episodes/episode-0003-execution-operational.json", "byte_count": 221969, "sha256": "a98116ef10e754a7d3356ff74796fddcaace7f1c5f29a2ef9cd70e5dd9692edb"},
    {"relative_path": "episodes/episode-0003-planning-operational.json", "byte_count": 572095, "sha256": "3bc6456b52b4941fdcf4dc1661339a523e557264698847fe38b27cb9576d22b8"},
    {"relative_path": "model/evaluation-no-prior-control.json", "byte_count": 575317, "sha256": "292a12408fd96fe0441657505b5ab504dbfb3153384ba2bf334f4b4ec8478552"},
    {"relative_path": "model/operational-acquisition.json", "byte_count": 215272, "sha256": "338ff944b8b235c445f6cf56d853f4206fd82cac12a9db0b7afb2f540edf85bc"},
    {"relative_path": "model/operational-failure-frontier.json", "byte_count": 799895, "sha256": "34f2b77e1d86d9a40908d1e6797e7272a024015c0546be58e189d5dae434e3be"},
    {"relative_path": "model/operational-overlay.json", "byte_count": 211795, "sha256": "b45d2dda2c6b7cd71bf15099625304860490c7b00f5fb21b0fe4c634c31b8f1f"},
    {"relative_path": "model/operational-proof.json", "byte_count": 210868, "sha256": "30cab4ed4ae9e2daf6d79b761381be05ef7aa2731cc129fb9939733170a3741d"},
    {"relative_path": "model/operational-proposal.json", "byte_count": 225159, "sha256": "6905e16cb45ef5fd54649c8a572d1be5a652fa7ff8dbf8aedff93f4f02b2978b"},
    {"relative_path": "process-supervision.json", "byte_count": 209624, "sha256": "43da97b6c6b0fbac3253f827777998c0174e9e959ea6f29fb58d153a474c3574"},
)


@dataclass(frozen=True, slots=True)
class FrozenV36ResourceSuccessorFailureV180r10:
    canonical_bytes: bytes
    failure_id: str
    output_facts: tuple[dict[str, Any], ...]

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r10 retained failure is not a document")
        return document


def _output_facts(output_root: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "relative_path": path.relative_to(output_root).as_posix(),
            "byte_count": len(raw := path.read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(candidate for candidate in output_root.rglob("*") if candidate.is_file())
    )


def load_frozen_v36_resource_successor_failure_v180r10() -> FrozenV36ResourceSuccessorFailureV180r10:
    root = Path(__file__).resolve().parents[2]
    base = root / ".tmp" / "exact-freeze"
    failure_path = base / "v180r10_v36_resource_successor_failure.json"
    output_root = base / "v180r10_v36_resource_successor_output"
    raw = failure_path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise ValueError("V180r10 retained failure is not a document")
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    output_facts = _output_facts(output_root)
    if not (
        canonical_json_bytes(document) == raw
        and set(document) == {
            "schema", "v36_resource_successor_authorization_id", "failure_type",
            "failure_message", "output_root_created", "retained_output_file_count",
            "terminal_output_present", "verification_output_present",
            "same_authorization_rerun_forbidden", "success_claimed",
            "COUNTER_COMPLETENESS_GATE", "WORKLOAD_ECONOMICS_GATE",
            "official_execution_allowed", "failure_id",
        }
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id == domains.extension_content_id_v180r10(
            domains.CONSTRUCTION_K7_V36_RESOURCE_SUCCESSOR_FAILURE_V180R10_DOMAIN,
            payload,
        )
        and document["v36_resource_successor_authorization_id"] == authorization.EXPECTED_AUTHORIZATION_ID
        and document["failure_type"] == "ConstructionK7V36ProductionTerminalFinalizerV180r6Error"
        and document["failure_message"] == "V36 did not observe the registered local-recovery path"
        and document["output_root_created"] is True
        and document["retained_output_file_count"] == len(EXPECTED_OUTPUT_FACTS)
        and document["terminal_output_present"] is False
        and document["verification_output_present"] is False
        and document["same_authorization_rerun_forbidden"] is True
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
        and output_facts == EXPECTED_OUTPUT_FACTS
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r10 retained failure or complete output tree changed")
    return FrozenV36ResourceSuccessorFailureV180r10(raw, failure_id, output_facts)


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_FAILURE_ID",
    "EXPECTED_OUTPUT_FACTS",
    "load_frozen_v36_resource_successor_failure_v180r10",
)
