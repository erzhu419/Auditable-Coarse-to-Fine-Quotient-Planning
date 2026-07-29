from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_public_source_work_authority_v1 as authority
from acfqp import v075_source_offline_work_materializer_v1 as source_work
from tests.test_v075_source_offline_work_materializer_v1 import (
    exact_source_replay,
)
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _rehash(
    value: dict,
    *,
    role: str,
    id_field: str,
) -> bytes:
    payload = dict(value)
    payload.pop(id_field, None)
    value = {
        **payload,
        id_field: hashlib.sha256(
            authority.DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    return canonical_json_bytes(value)


def _artifacts(exact_source_replay):
    materialization = source_work.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    verification = (
        source_work.verify_v075_source_offline_work_independently_v1(
            replay=exact_source_replay,
            claimed=materialization,
        )
    )
    status = {
        "schema": "acfqp.v075_source_replay_materialization_status.v1",
        "schema_version": "1.0.0",
        "profile_key": authority.CONTROLLER_PROFILE_KEY,
        "snapshot_preflight_id": _id("snapshot-preflight"),
        "controller_code_manifest_id": _id("controller-code"),
        "source_only_bypass_evidence_id": _id("source-only-bypass"),
        "source_only_readiness_id": _id("source-only-readiness"),
        "same_process_protocol_id": _id("same-process-protocol"),
        "source_graph_verification_id": _id("source-graph-verification"),
        "blocker": None,
        "source_only_snapshot_eligible": True,
        "current_code_production_ready": True,
        "production_replay_status": "COMPLETED",
        "production_materialization_status": "COMPLETED",
        "source_replay_id": None,
        "source_replay_object_persisted": False,
        "source_replay_object_consumed_same_process": True,
        "source_work_materialization_id": materialization.materialization_id,
        "source_work_verification_id": verification.verification_id,
        "source_child_launched": False,
        "sample_draws_started": True,
        "materialization_artifact_written": True,
        "verification_artifact_written": True,
        "counter_document_accepted": False,
        "pickle_transport_accepted": False,
        "caller_supplied_expected_ids_accepted": False,
        "current_tree_recomputation_used_as_source_replay": False,
        "generic_recipe_freeze_helper_called": False,
        "confirmatory_manifest_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "target_access": False,
        "hidden_law_access": False,
    }
    return (
        materialization.canonical_bytes,
        canonical_json_bytes(verification.to_document()),
        _rehash(status, role="controller_status", id_field="status_id"),
    )


def test_public_artifacts_mint_one_law_free_bundle(
    exact_source_replay,
) -> None:
    materialization, verification, status = _artifacts(exact_source_replay)
    value = authority.verify_v075_public_source_work_artifacts_v1(
        materialization_raw=materialization,
        verification_raw=verification,
        controller_status_raw=status,
    )
    document = value.to_document()
    assert document["source_replay_completed"] is True
    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["may_certify"] is False
    assert document["target_access"] is False
    assert document["hidden_law_access"] is False
    assert value.offline_draw_count > 0


def test_caller_cannot_mint_public_bundle() -> None:
    with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
        authority.V075VerifiedPublicSourceWorkBundleV1(
            object(),
            *(_id(f"role-{index}") for index in range(9)),
            1,
            1,
            0,
        )


def test_materialization_counter_tamper_is_rejected(
    exact_source_replay,
) -> None:
    materialization, verification, status = _artifacts(exact_source_replay)
    document = loads_canonical_json(materialization)
    document["offline_sample_draw_count"] += 1
    with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
        authority.verify_v075_public_source_work_artifacts_v1(
            materialization_raw=canonical_json_bytes(document),
            verification_raw=verification,
            controller_status_raw=status,
        )


def test_semantically_false_verification_is_rejected_even_when_rehashed(
    exact_source_replay,
) -> None:
    materialization, verification, status = _artifacts(exact_source_replay)
    document = loads_canonical_json(verification)
    document["valid"] = False
    attacked = _rehash(
        document,
        role="verification",
        id_field="verification_id",
    )
    with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
        authority.verify_v075_public_source_work_artifacts_v1(
            materialization_raw=materialization,
            verification_raw=attacked,
            controller_status_raw=status,
        )


def test_target_or_hidden_law_access_status_is_rejected_even_when_rehashed(
    exact_source_replay,
) -> None:
    materialization, verification, status = _artifacts(exact_source_replay)
    for field_name in ("target_access", "hidden_law_access"):
        document = loads_canonical_json(status)
        document[field_name] = True
        attacked = _rehash(
            document,
            role="controller_status",
            id_field="status_id",
        )
        with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
            authority.verify_v075_public_source_work_artifacts_v1(
                materialization_raw=materialization,
                verification_raw=verification,
                controller_status_raw=attacked,
            )


def test_stale_status_reference_and_noncanonical_json_are_rejected(
    exact_source_replay,
) -> None:
    materialization, verification, status = _artifacts(exact_source_replay)
    document = loads_canonical_json(status)
    document["source_work_materialization_id"] = _id("stale-materialization")
    stale = _rehash(
        document,
        role="controller_status",
        id_field="status_id",
    )
    with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
        authority.verify_v075_public_source_work_artifacts_v1(
            materialization_raw=materialization,
            verification_raw=verification,
            controller_status_raw=stale,
        )
    noncanonical = json.dumps(
        loads_canonical_json(materialization),
        indent=2,
    ).encode("utf-8")
    with pytest.raises(authority.V075PublicSourceWorkAuthorityViolation):
        authority.verify_v075_public_source_work_artifacts_v1(
            materialization_raw=noncanonical,
            verification_raw=verification,
            controller_status_raw=status,
        )


def test_production_reconciliation_import_closure_has_no_v072_source_graph(
) -> None:
    root = Path(__file__).resolve().parents[1]
    script = (
        "import sys;"
        f"sys.path.insert(0,{str(root / 'src')!r});"
        "import acfqp.v075_campaign_reconciliation_v1;"
        "bad=[name for name in sys.modules "
        "if name.startswith('acfqp.v072') "
        "or name=='acfqp.observation_support_campaign_v1'];"
        "print('\\n'.join(sorted(bad)));"
        "raise SystemExit(bool(bad))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == ""
