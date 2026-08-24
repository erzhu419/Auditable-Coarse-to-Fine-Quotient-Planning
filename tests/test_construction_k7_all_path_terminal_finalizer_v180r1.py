from __future__ import annotations

import ast
from copy import deepcopy
from functools import lru_cache
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_all_path_terminal_finalizer_v180r1 as producer
from acfqp import (
    construction_k7_all_path_terminal_finalizer_independent_verifier_v180r1
    as verifier,
)
from acfqp import (
    construction_k7_all_path_terminal_finalizer_fixture_freeze_v180r1
    as frozen,
)
from acfqp import construction_k7_domain_registry_extension_v180r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


@lru_cache(maxsize=1)
def _fixture_graph() -> tuple[dict[str, bytes], bytes, bytes]:
    bundles: dict[str, bytes] = {}
    for code in TerminalCode:
        fixture = producer.fixture_counter_values_v180r1(code)
        observation = producer.build_terminal_observation_v180r1(
            subject_id=f"fixture_{code.value.lower()}",
            terminal_code=code,
            counter_values=fixture.values,
            evidence_id=hashlib.sha256(code.value.encode()).hexdigest(),
        )
        bundles[code.value] = (
            producer.materialize_terminal_accounting_bundle_v180r1(observation)
        )
    campaign = producer.materialize_fixture_campaign_bundle_v180r1(bundles)
    verification = verifier.verify_fixture_campaign_independently_v180r1(campaign)
    return bundles, campaign, verification


def test_one_shared_v9_finalizer_covers_all_ten_terminal_codes() -> None:
    bundles, campaign_raw, verification_raw = _fixture_graph()
    assert set(bundles) == {code.value for code in TerminalCode}
    campaign = loads_canonical_json(campaign_raw)
    verification = loads_canonical_json(verification_raw)
    assert campaign["campaign_input"]["terminal_code_count"] == 10
    assert campaign["campaign_input"]["path_families"] == [
        "FAILURE",
        "FALLBACK",
        "OOD",
        "SUCCESS",
    ]
    assert campaign["output_bytes_fixed_point"] == len(campaign_raw)
    assert verification["all_terminal_counter_records_replayed"] is True
    assert verification["all_terminal_work_vectors_replayed"] is True
    assert verification["all_terminal_comparison_vectors_rederived"] is True
    assert verification["all_terminal_output_fixed_points_replayed"] is True
    assert verification["campaign_orchestration_work_vector_replayed"] is True


def test_fixture_evidence_does_not_unlock_fresh_or_official_gates() -> None:
    bundles, campaign_raw, verification_raw = _fixture_graph()
    for raw in (*bundles.values(), campaign_raw, verification_raw):
        document = loads_canonical_json(raw)
        assert document["development_fixture_only"] is True
        assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        assert document["official_scalar_cost"] is None
        assert document["official_N_break_even"] is None
        assert document["official_execution_allowed"] is False
    assert loads_canonical_json(campaign_raw)["fresh_v180_observed_occurrence_count"] == 0


def test_every_terminal_bundle_has_full_v9_rows_and_exact_output_fixed_point() -> None:
    bundles, _, _ = _fixture_graph()
    for code, raw in bundles.items():
        document = loads_canonical_json(raw)
        assert document["terminal_observation"]["terminal_code"] == code
        assert len(document["work_vector"]["records"]) == 269
        assert document["work_vector"]["records"] == sorted(
            document["work_vector"]["records"], key=lambda row: row["path"]
        )
        assert document["output_bytes_fixed_point"] == len(raw)
        output = next(
            row
            for row in document["work_vector"]["records"]
            if row["path"] == "io.output_bytes"
        )
        assert output["value"] == len(raw)


@pytest.mark.parametrize(
    ("path", "forged_value"),
    (
        (("COUNTER_COMPLETENESS_GATE",), "PASS"),
        (("fresh_v180_observed_occurrence_count",), 10),
        (("campaign_input", "terminal_rows", 0, "terminal_code"), "PROTOCOL_FAILURE"),
    ),
)
def test_resigned_campaign_claim_and_join_attacks_are_rejected(
    path: tuple[object, ...], forged_value: object
) -> None:
    _, campaign_raw, _ = _fixture_graph()
    forged = deepcopy(loads_canonical_json(campaign_raw))
    target = forged
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = forged_value
    payload = {
        key: value for key, value in forged.items() if key != "fixture_campaign_bundle_id"
    }
    forged["fixture_campaign_bundle_id"] = domains.extension_content_id_v180r1(
        domains.CONSTRUCTION_K7_CAMPAIGN_BUNDLE_V180R1_DOMAIN,
        payload,
    )
    with pytest.raises(
        verifier.ConstructionK7AllPathTerminalFinalizerIndependentVerifierV180r1Error
    ):
        verifier.verify_fixture_campaign_independently_v180r1(
            canonical_json_bytes(forged)
        )


def test_independent_verifier_does_not_import_the_producer() -> None:
    path = (
        Path(verifier.__file__).resolve()
    )
    tree = ast.parse(path.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("all_path_terminal_finalizer_v180r1" in name for name in imported)


def test_retained_fixture_graph_matches_exact_frozen_identities() -> None:
    graph = frozen.load_frozen_fixture_graph_v180r1()
    _, campaign, verification = _fixture_graph()
    assert graph.campaign_bytes == campaign
    assert graph.verification_bytes == verification
    assert graph.campaign_id == frozen.EXPECTED_CAMPAIGN_ID
    assert graph.verification_id == frozen.EXPECTED_VERIFICATION_ID
