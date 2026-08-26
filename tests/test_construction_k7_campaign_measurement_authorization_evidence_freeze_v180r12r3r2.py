from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import pickle
import subprocess

import pytest

from acfqp import (
    construction_k7_campaign_measurement_authorization_evidence_freeze_v180r12r3r2
    as evidence,
)
from acfqp import (
    construction_k7_campaign_measurement_execution_authorization_v180r12r3r2
    as authorization,
)
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r3r2 as protocol


def _wrapper_raw() -> bytes:
    return Path(evidence.__file__).read_bytes()


def _c_pre_wrapper_raw() -> bytes:
    return evidence.normalize_own_source_v180r12r3r2(_wrapper_raw())


def _replace_literals(raw: bytes, *, include_evidence: bool = True) -> bytes:
    result = raw
    evidence_names = {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        "EXPECTED_CANONICAL_BYTE_COUNT",
        "EXPECTED_CANONICAL_SHA256",
    }
    for name, (start, end, _replacement) in sorted(
        evidence._literal_spans(raw).items(),  # noqa: SLF001
        key=lambda item: item[1][0],
        reverse=True,
    ):
        if not include_evidence and name in evidence_names:
            continue
        replacement = (
            b'"1111111111111111111111111111111111111111111111111111111111111111"'
            if name in evidence._STRING_REDACTED_CONSTANTS  # noqa: SLF001
            else b"123456"
        )
        result = result[:start] + replacement + result[end:]
    return result


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        (evidence.GIT_EXECUTABLE, "-C", str(repository), *arguments),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=evidence._git_environment(),  # noqa: SLF001
    )
    return completed.stdout.strip()


def _initialize_repository(repository: Path) -> None:
    repository.mkdir(parents=True)
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "V180r12r3r2 Test")
    _git(repository, "config", "user.email", "v180r12r3r2@example.invalid")


def _populate_source_boundary(repository: Path) -> None:
    for index, relative_path in enumerate(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS):
        path = repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            _c_pre_wrapper_raw()
            if relative_path == evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
            else f"frozen source {index}\n".encode("ascii")
        )


def _source_facts() -> tuple[dict[str, object], ...]:
    rows = []
    for index, relative_path in enumerate(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS):
        raw = (
            _c_pre_wrapper_raw()
            if relative_path == evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
            else f"frozen source {index}\n".encode("ascii")
        )
        rows.append(evidence._fact_from_raw(relative_path, raw))  # noqa: SLF001
    return tuple(rows)


def _boundary_record(source_facts: tuple[dict[str, object], ...]) -> dict[str, object]:
    by_path = {row["relative_path"]: row for row in source_facts}
    return {
        "source_boundary_commit": "1" * 40,
        "source_boundary_tree": "2" * 40,
        "source_boundary_empty_bridge_commit": "3" * 40,
        "source_boundary_empty_bridge_tree": "2" * 40,
        "source_boundary_source_fact_count": len(source_facts),
        "source_boundary_source_total_byte_count": sum(
            int(row["byte_count"]) for row in source_facts
        ),
        "source_boundary_source_facts_sha256": hashlib.sha256(
            evidence.canonical_json_bytes(list(source_facts))
        ).hexdigest(),
        "source_boundary_authorization_source_fact": by_path[
            evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
        ],
        "source_boundary_wrapper_normalized_source_fact": by_path[
            evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
        ],
        "source_boundary_git_process_count": 6,
        "source_boundary_is_external_not_self_derived": True,
        "source_boundary_commit_is_strict_ancestor": True,
        "source_boundary_empty_bridge_is_immediate_child": True,
        "source_boundary_empty_bridge_preserved_entire_tree": True,
        "source_boundary_wrapper_only_allowlisted_literal_commit_required": True,
        "source_boundary_candidate_allowed_only_at_empty_bridge_head": True,
        "source_boundary_runtime_requires_committed_wrapper_literals": True,
        "source_boundary_candidate_and_runtime_payload_identity_equal": True,
        "source_boundary_post_literal_bound_source_touch_forbidden": True,
        "source_boundary_ordinary_sources_equal_current_bytes": True,
        "source_boundary_wrapper_twelve_sentinels_verified": True,
    }


def _install_frozen_protocol_authorization_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    values: dict[str, object] = {
        name: (101 if name == "EXPECTED_CANONICAL_BYTE_COUNT" else "d" * 64)
        for name in protocol.PROTOCOL_FINAL_ANCHOR_NAMES
    }
    values["EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"] = "e" * 64
    for name, value in values.items():
        monkeypatch.setattr(protocol, name, value)
    monkeypatch.setattr(
        protocol,
        "require_frozen_protocol_final_anchor_set_v180r12r3r2",
        lambda: dict(values),
    )
    monkeypatch.setattr(
        authorization, "EXPECTED_PROTOCOL_ID", values["EXPECTED_PROTOCOL_ID"]
    )
    monkeypatch.setattr(
        authorization,
        "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
        values["EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"],
    )
    return values


def test_outcome_free_wrapper_has_exact_phase_aware_twelve_literal_topology() -> None:
    assert evidence.POST_PREREG_REDACTED_CONSTANTS == (
        authorization.AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS
    )
    assert len(evidence.POST_PREREG_REDACTED_CONSTANTS) == 12
    values = evidence._literal_values(_wrapper_raw())  # noqa: SLF001
    final_phase = evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID != evidence.ZERO_ID
    if final_phase:
        assert all(
            value != evidence.ZERO_ID
            for name, value in values.items()
            if name in evidence._STRING_REDACTED_CONSTANTS  # noqa: SLF001
        )
        assert all(
            type(value) is int and value > 0
            for name, value in values.items()
            if name in evidence._INTEGER_REDACTED_CONSTANTS  # noqa: SLF001
        )
    else:
        assert evidence._all_sentinels(values)  # noqa: SLF001
    assert authorization.EXPECTED_AUTHORIZATION_ID == evidence.ZERO_ID
    assert authorization.EXPECTED_SOURCE_CLOSURE_ID == evidence.ZERO_ID
    assert evidence.SOURCE_FACT_EXCLUSIONS == ()
    assert evidence.SOURCE_BOUNDARY_REQUIRED_PATHS == tuple(
        sorted(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)
    )
    assert len(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS) == 21
    assert len(set(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)) == 21
    assert protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in (
        evidence.SOURCE_BOUNDARY_REQUIRED_PATHS
    )
    assert protocol.V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH in (
        evidence.SOURCE_BOUNDARY_REQUIRED_PATHS
    )
    assert evidence._AUTHORIZATION_RELATIVE_PATH in (  # noqa: SLF001
        evidence.SOURCE_BOUNDARY_REQUIRED_PATHS
    )
    assert evidence._EVIDENCE_RELATIVE_PATH in (  # noqa: SLF001
        evidence.SOURCE_BOUNDARY_REQUIRED_PATHS
    )


def test_public_build_requires_explicit_external_boundary_and_candidate_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = inspect.signature(
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2
    )
    assert signature.parameters["source_boundary_commit"].default is inspect.Parameter.empty
    assert signature.parameters["candidate_only"].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="explicit bool"):
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
            "0" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
            candidate_only=None,  # type: ignore[arg-type]
        )
    monkeypatch.setattr(
        protocol,
        "require_frozen_protocol_final_anchor_set_v180r12r3r2",
        lambda: (_ for _ in ()).throw(
            protocol.CampaignMeasurementProtocolV180R12R3R2Error(
                "test draft protocol anchors"
            )
        ),
    )
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="protocol final anchor set is not frozen",
    ):
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
            "0" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
            candidate_only=True,
        )
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="protocol final anchor set is not frozen",
    ):
        evidence.freeze_campaign_measurement_authorization_evidence_v180r12r3r2(
            "0" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
        )


def test_protocol_and_authorization_anchor_gate_precedes_evidence_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replayed = False

    def replay(*_args, **_kwargs):
        nonlocal replayed
        replayed = True
        raise AssertionError("external evidence replay must not start")

    monkeypatch.setattr(evidence, "_replay_external_source_boundary", replay)
    monkeypatch.setattr(
        protocol,
        "require_frozen_protocol_final_anchor_set_v180r12r3r2",
        lambda: (_ for _ in ()).throw(
            protocol.CampaignMeasurementProtocolV180R12R3R2Error(
                "test draft protocol anchors"
            )
        ),
    )
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="protocol final anchor set is not frozen",
    ):
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
            "1" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
            candidate_only=True,
        )
    assert replayed is False


@pytest.mark.parametrize(
    "authorization_anchor",
    (
        "EXPECTED_PROTOCOL_ID",
        "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
    ),
)
def test_authorization_anchor_mismatch_precedes_evidence_replay(
    monkeypatch: pytest.MonkeyPatch,
    authorization_anchor: str,
) -> None:
    replayed = False

    def replay(*_args, **_kwargs):
        nonlocal replayed
        replayed = True
        raise AssertionError("external evidence replay must not start")

    monkeypatch.setattr(evidence, "_replay_external_source_boundary", replay)
    anchors = _install_frozen_protocol_authorization_anchors(monkeypatch)
    monkeypatch.setattr(
        authorization,
        authorization_anchor,
        "f" * 64,
    )
    assert getattr(authorization, authorization_anchor) != anchors[
        authorization_anchor
    ]
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="not frozen or equal",
    ):
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
            "1" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
            candidate_only=True,
        )
    assert replayed is False


def test_normalizer_changes_only_allowlisted_literal_values() -> None:
    boundary = _c_pre_wrapper_raw()
    current = _wrapper_raw()
    changed = _replace_literals(boundary)
    assert evidence.normalize_own_source_v180r12r3r2(current) == boundary
    assert evidence.normalize_own_source_v180r12r3r2(boundary) == boundary
    assert evidence.normalize_own_source_v180r12r3r2(changed) == boundary
    changed_logic = boundary.replace(
        b"External, non-bootstrapping evidence",
        b"External non-bootstrapping evidence",
        1,
    )
    assert changed_logic != boundary
    assert evidence.normalize_own_source_v180r12r3r2(changed_logic) != boundary


def test_normalizer_rejects_expression_duplicate_and_adjacent_literal() -> None:
    raw = _wrapper_raw()
    spans = evidence._literal_spans(raw)  # noqa: SLF001
    start, end, _replacement = spans["EXPECTED_AUTHORIZATION_ID"]
    expression = raw[:start] + b'"0" * 64' + raw[end:]
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="string anchor is not one literal",
    ):
        evidence.normalize_own_source_v180r12r3r2(expression)
    duplicate = raw + b'\nEXPECTED_AUTHORIZATION_ID = "' + b"2" * 64 + b'"\n'
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="duplicated",
    ):
        evidence.normalize_own_source_v180r12r3r2(duplicate)
    adjacent = raw[:start] + b'"' + b"0" * 32 + b'" "' + b"0" * 32 + b'"' + raw[end:]
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="exactly one lexical literal token",
    ):
        evidence.normalize_own_source_v180r12r3r2(adjacent)


def test_external_boundary_blob_replay_blocks_coordinated_source_resign() -> None:
    boundary: dict[str, bytes] = {}
    for index, path in enumerate(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS):
        boundary[path] = (
            _c_pre_wrapper_raw()
            if path == evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
            else f"source {index}\n".encode("ascii")
        )
    current = {
        **boundary,
        evidence._EVIDENCE_RELATIVE_PATH: _replace_literals(  # noqa: SLF001
            boundary[evidence._EVIDENCE_RELATIVE_PATH]  # noqa: SLF001
        ),
    }
    facts = evidence._verify_boundary_blobs(boundary, current)  # noqa: SLF001
    assert len(facts) == len(evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)
    resigned = {
        **current,
        evidence._AUTHORIZATION_RELATIVE_PATH: b"coordinated resign\n",  # noqa: SLF001
    }
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="ordinary source differs from the external C_pre bytes",
    ):
        evidence._verify_boundary_blobs(boundary, resigned)  # noqa: SLF001
    attacked_wrapper = current[evidence._EVIDENCE_RELATIVE_PATH].replace(  # noqa: SLF001
        b"External, non-bootstrapping evidence",
        b"External non-bootstrapping evidence",
        1,
    )
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="outside twelve allowlisted literals",
    ):
        evidence._verify_boundary_blobs(  # noqa: SLF001
            boundary,
            {**current, evidence._EVIDENCE_RELATIVE_PATH: attacked_wrapper},  # noqa: SLF001
        )


def test_real_git_accepts_only_cpre_empty_bridge_wrapper_literal_sequence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "legal-boundary"
    _initialize_repository(repository)
    _populate_source_boundary(repository)
    _git(repository, "add", "--", *evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)
    _git(repository, "commit", "-m", "external C_pre")
    c_pre = _git(repository, "rev-parse", "HEAD^{commit}")
    tree = _git(repository, "rev-parse", "HEAD^{tree}")
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="root, commit, tree, or HEAD changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            repository,
            candidate_only=True,
        )
    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")
    bridge = _git(repository, "rev-parse", "HEAD^{commit}")
    assert _git(repository, "rev-parse", "HEAD^{tree}") == tree
    wrapper = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    wrapper.write_bytes(_replace_literals(wrapper.read_bytes()))
    replayed_tree, replayed_bridge, boundary, committed = (
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            repository,
            candidate_only=True,
        )
    )
    assert replayed_tree == tree
    assert replayed_bridge == bridge
    assert committed == boundary[evidence._EVIDENCE_RELATIVE_PATH]  # noqa: SLF001
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="runtime freeze requires the wrapper-only literal successor",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            repository,
            candidate_only=False,
        )
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "freeze twelve wrapper literals")
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="candidate build is allowed only at the empty bridge HEAD",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            repository,
            candidate_only=True,
        )
    _, frozen_bridge, _, committed = evidence._git_source_boundary_blobs(  # noqa: SLF001
        c_pre,
        evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
        repository,
        candidate_only=False,
    )
    assert frozen_bridge == bridge
    assert committed == wrapper.read_bytes()


def test_real_git_rejects_nonempty_bridge_and_multi_file_literal_commit(
    tmp_path: Path,
) -> None:
    nonempty = tmp_path / "nonempty"
    _initialize_repository(nonempty)
    _populate_source_boundary(nonempty)
    _git(nonempty, "add", "--", *evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)
    _git(nonempty, "commit", "-m", "C_pre")
    c_pre = _git(nonempty, "rev-parse", "HEAD^{commit}")
    ordinary = nonempty / evidence.EXECUTION_CHAIN_RELATIVE_PATHS[0]
    ordinary.write_bytes(b"changed bridge\n")
    _git(nonempty, "add", "--", evidence.EXECUTION_CHAIN_RELATIVE_PATHS[0])
    _git(nonempty, "commit", "-m", "nonempty bridge")
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="empty bridge commit or tree changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            nonempty,
            candidate_only=True,
        )

    multi = tmp_path / "multi"
    _initialize_repository(multi)
    _populate_source_boundary(multi)
    _git(multi, "add", "--", *evidence.SOURCE_BOUNDARY_REQUIRED_PATHS)
    _git(multi, "commit", "-m", "C_pre")
    c_pre = _git(multi, "rev-parse", "HEAD^{commit}")
    _git(multi, "commit", "--allow-empty", "-m", "empty bridge")
    wrapper = multi / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    wrapper.write_bytes(_replace_literals(wrapper.read_bytes()))
    ordinary = multi / evidence.EXECUTION_CHAIN_RELATIVE_PATHS[0]
    ordinary.write_bytes(b"changed literal commit\n")
    _git(
        multi,
        "add",
        "--",
        evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
        evidence.EXECUTION_CHAIN_RELATIVE_PATHS[0],
    )
    _git(multi, "commit", "-m", "illegal multi-file literal commit")
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="must modify only the regular evidence wrapper",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            c_pre,
            evidence.SOURCE_BOUNDARY_REQUIRED_PATHS,
            multi,
            candidate_only=False,
        )


def test_candidate_and_runtime_payloads_match_under_external_nonbootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchors = _install_frozen_protocol_authorization_anchors(monkeypatch)
    source_facts = _source_facts()
    source_boundary = _boundary_record(source_facts)
    closure = authorization.source_closure_candidate_v180r12r3r2(source_facts)
    authorization_raw = evidence.canonical_json_bytes({"fixture": "authorization"})
    authorization_id = "a" * 64
    authorization_source_fact = source_boundary[
        "source_boundary_authorization_source_fact"
    ]
    document = {
        "campaign_measurement_protocol_id": anchors["EXPECTED_PROTOCOL_ID"],
        "campaign_measurement_execution_slot_id": anchors[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ],
        "source_closure_candidate": closure,
        "source_closure_contract": protocol.source_closure_contract_v180r12r3r2(),
        "source_closure_facts_supplied": True,
        "source_closure_identity_frozen": False,
        "source_closure_placeholder_only": True,
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "identity_literals_frozen": False,
        "execution_authorization_effective": False,
        "zero_sentinel_draft_is_executable_authorization": False,
        "execution_forbidden_until_all_protocol_authorization_source_closure_prelaunch_rule_and_evidence_identities_are_frozen": True,
        "authorization_evidence_freeze_required_before_execution": True,
        "source_bound_prelaunch_required_before_real_outcome_execution": True,
        "campaign_measurement_authorization_issued": False,
        "campaign_measurement_execution_started": False,
        "campaign_measurement_execution_count": 0,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
        "prelaunch_contract": protocol.prelaunch_contract_v180r12r3r2(),
        "failed_dispatch_repair_lineage": (
            protocol.failed_dispatch_repair_lineage_contract_v180r12r3r2()
        ),
        "failed_external_replay_repair_lineage": (
            protocol.failed_external_replay_repair_lineage_contract_v180r12r3r2()
        ),
        "failed_v180r12r3_identity_rerun_forbidden": True,
        "failed_v180r12r3r1_identity_rerun_forbidden": True,
        "fresh_v180r12r3r2_physical_paths_and_identities_required": True,
        "repair_scope": (
            "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
        ),
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
        "source_bound_runner_execution_envelope_contract": (
            protocol.source_bound_runner_execution_envelope_contract_v180r12r3r2()
        ),
        "cgroup_parent_fact": {"fixture": "cgroup"},
        "runtime_capability_fact": {"fixture": "runtime"},
    }

    class FrozenAuthorization:
        canonical_bytes = authorization_raw
        execution_authorization_id = authorization_id

        @staticmethod
        def to_document() -> dict[str, object]:
            return document

    observed: dict[str, object] = {}

    def replay_boundary(commit: str, *, candidate_only: bool):
        observed["commit"] = commit
        observed["candidate_only"] = candidate_only
        return source_boundary, source_facts

    def freeze_authorization(**kwargs):
        observed["authorization_kwargs"] = kwargs
        return FrozenAuthorization()

    monkeypatch.setattr(evidence, "_replay_external_source_boundary", replay_boundary)
    monkeypatch.setattr(
        evidence.authorization,
        "freeze_campaign_measurement_execution_authorization_v180r12r3r2",
        freeze_authorization,
    )
    monkeypatch.setattr(evidence, "EXPECTED_AUTHORIZATION_ID", authorization_id)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        len(authorization_raw),
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        hashlib.sha256(authorization_raw).hexdigest(),
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
        authorization_source_fact["byte_count"],
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        authorization_source_fact["sha256"],
    )
    monkeypatch.setattr(evidence, "EXPECTED_SOURCE_CLOSURE_ID", closure["source_closure_id"])
    monkeypatch.setattr(
        evidence,
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
        closure["source_closure_byte_count"],
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_SOURCE_CLOSURE_SHA256",
        closure["source_closure_sha256"],
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
        closure["source_fact_count"],
    )
    candidate = evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
        "1" * 40,
        cgroup_parent_fact={"fixture": "cgroup"},
        runtime_capability_fact={"fixture": "runtime"},
        candidate_only=True,
    )
    assert candidate["execution_authorization_id"] == authorization_id
    assert candidate["authorization_candidate_identity_bound_only_by_external_evidence"] is True
    assert candidate["authorization_self_bootstrap_forbidden"] is True
    assert candidate["authorization_source_excluded_from_self_derived_fixed_point"] is True
    assert candidate["authorization_source_included_only_as_external_c_pre_fact"] is True
    assert candidate["authorization_evidence_makes_execution_effective"] is False
    assert candidate["failed_dispatch_repair_lineage"] == (
        protocol.failed_dispatch_repair_lineage_contract_v180r12r3r2()
    )
    assert candidate["failed_external_replay_repair_lineage"] == (
        protocol.failed_external_replay_repair_lineage_contract_v180r12r3r2()
    )
    assert candidate["source_bound_runner_execution_envelope_contract"] == (
        protocol.source_bound_runner_execution_envelope_contract_v180r12r3r2()
    )
    assert candidate["failed_v180r12r3_identity_rerun_forbidden"] is True
    assert candidate["failed_v180r12r3r1_identity_rerun_forbidden"] is True
    assert candidate["fresh_v180r12r3r2_physical_paths_and_identities_required"]
    assert candidate["repair_scope"] == (
        "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
    )
    assert candidate["v180r12r3r2_outcome_bytes_accessed"] is False
    assert candidate["campaign_measurement_execution_count"] == 0
    assert candidate["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert candidate["official_execution_allowed"] is False
    assert candidate["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert observed["authorization_kwargs"] == {
        "cgroup_parent_fact": {"fixture": "cgroup"},
        "runtime_capability_fact": {"fixture": "runtime"},
        "source_facts": source_facts,
    }

    candidate_raw = evidence.canonical_json_bytes(candidate)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        candidate["authorization_evidence_id"],
    )
    monkeypatch.setattr(evidence, "EXPECTED_CANONICAL_BYTE_COUNT", len(candidate_raw))
    monkeypatch.setattr(
        evidence,
        "EXPECTED_CANONICAL_SHA256",
        hashlib.sha256(candidate_raw).hexdigest(),
    )
    frozen = evidence.freeze_campaign_measurement_authorization_evidence_v180r12r3r2(
        "1" * 40,
        cgroup_parent_fact={"fixture": "cgroup"},
        runtime_capability_fact={"fixture": "runtime"},
    )
    assert observed["candidate_only"] is False
    assert frozen.canonical_bytes == candidate_raw
    assert frozen.to_document() == candidate


@pytest.mark.parametrize(
    "field",
    (
        "source_closure_id",
        "source_closure_byte_count",
        "source_closure_sha256",
        "source_fact_count",
    ),
)
def test_build_rejects_source_closure_anchor_drift(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    anchors = _install_frozen_protocol_authorization_anchors(monkeypatch)
    source_facts = _source_facts()
    boundary = _boundary_record(source_facts)
    closure = authorization.source_closure_candidate_v180r12r3r2(source_facts)
    authorization_raw = b"{}"
    source_fact = boundary["source_boundary_authorization_source_fact"]
    document = {
        "campaign_measurement_protocol_id": anchors["EXPECTED_PROTOCOL_ID"],
        "campaign_measurement_execution_slot_id": anchors[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ],
        "source_closure_candidate": {**closure, field: 1 if "count" in field else "f" * 64},
        "source_closure_contract": protocol.source_closure_contract_v180r12r3r2(),
        "source_closure_facts_supplied": True,
        "source_closure_identity_frozen": False,
        "source_closure_placeholder_only": True,
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "identity_literals_frozen": False,
        "execution_authorization_effective": False,
        "zero_sentinel_draft_is_executable_authorization": False,
        "execution_forbidden_until_all_protocol_authorization_source_closure_prelaunch_rule_and_evidence_identities_are_frozen": True,
        "authorization_evidence_freeze_required_before_execution": True,
        "source_bound_prelaunch_required_before_real_outcome_execution": True,
        "campaign_measurement_authorization_issued": False,
        "campaign_measurement_execution_started": False,
        "campaign_measurement_execution_count": 0,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
        "prelaunch_contract": {},
        "cgroup_parent_fact": {},
        "runtime_capability_fact": {},
    }

    class Frozen:
        execution_authorization_id = "a" * 64
        canonical_bytes = authorization_raw

        @staticmethod
        def to_document():
            return document

    monkeypatch.setattr(
        evidence,
        "_replay_external_source_boundary",
        lambda _commit, *, candidate_only: (boundary, source_facts),
    )
    monkeypatch.setattr(
        evidence.authorization,
        "freeze_campaign_measurement_execution_authorization_v180r12r3r2",
        lambda **_kwargs: Frozen(),
    )
    for name, value in (
        ("EXPECTED_AUTHORIZATION_ID", "a" * 64),
        ("EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT", len(authorization_raw)),
        ("EXPECTED_AUTHORIZATION_CANONICAL_SHA256", hashlib.sha256(authorization_raw).hexdigest()),
        ("EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT", source_fact["byte_count"]),
        ("EXPECTED_AUTHORIZATION_SOURCE_SHA256", source_fact["sha256"]),
        ("EXPECTED_SOURCE_CLOSURE_ID", closure["source_closure_id"]),
        ("EXPECTED_SOURCE_CLOSURE_BYTE_COUNT", closure["source_closure_byte_count"]),
        ("EXPECTED_SOURCE_CLOSURE_SHA256", closure["source_closure_sha256"]),
        ("EXPECTED_SOURCE_CLOSURE_FILE_COUNT", closure["source_fact_count"]),
    ):
        monkeypatch.setattr(evidence, name, value)
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="authorization candidate or external source anchor changed",
    ):
        evidence.build_campaign_measurement_authorization_evidence_v180r12r3r2(
            "1" * 40,
            cgroup_parent_fact={},
            runtime_capability_fact={},
            candidate_only=True,
        )


def test_evidence_value_object_rejects_forgery_and_pickle() -> None:
    payload = {"schema": "fixture"}
    identity = authorization.domains.extension_content_id_v180r12r3r2(
        authorization.domains.CONSTRUCTION_K7_AUTHORIZATION_EVIDENCE_V180R12R3R2_DOMAIN,
        payload,
    )
    raw = evidence.canonical_json_bytes({**payload, "authorization_evidence_id": identity})
    with pytest.raises(
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2Error,
        match="foreign or noncanonical",
    ):
        evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2(
            object(), raw, identity
        )
    legitimate = evidence.CampaignMeasurementAuthorizationEvidenceV180R12R3R2(
        evidence._ISSUER, raw, identity  # noqa: SLF001
    )
    with pytest.raises(TypeError, match="not picklable"):
        pickle.dumps(legitimate)
