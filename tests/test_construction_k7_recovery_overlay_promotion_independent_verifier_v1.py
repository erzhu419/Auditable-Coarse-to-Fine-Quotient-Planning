from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_recovery_overlay_promotion_independent_verifier_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def test_domain_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 1
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "verify_recovery_overlay_promotion_bytes_v1",
    }


def test_verifier_import_surface_excludes_all_relevant_producers() -> None:
    source_path = Path(subject.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    forbidden = {
        "construction_k7_recovery_overlay_promotion_v1",
        "construction_k7_recovery_eligible_world_model_loop_v1",
        "construction_k7_recovery_eligible_checkpoint_fixture_v1",
    }
    assert forbidden.isdisjoint(imported)


@pytest.fixture(scope="module")
def retained_bytes():
    retained = os.environ.get("ACFQP_RETAINED_RECOVERY_OVERLAY_PROMOTION")
    if not retained:
        pytest.skip("retained recovery-overlay promotion is unavailable")
    root = Path(retained)
    rows = {
        "checkpoint": (root / "RECOVERY_ELIGIBLE_CHECKPOINT.json").read_bytes(),
        "transaction": (root / "GROUND_TRANSACTION.json").read_bytes(),
        "loop": (root / "WORLD_MODEL_LOOP.json").read_bytes(),
        "promotion": (root / "PROMOTION_RESULT.json").read_bytes(),
    }
    return rows


@pytest.fixture(scope="module")
def verified(retained_bytes):
    return subject.verify_recovery_overlay_promotion_bytes_v1(
        checkpoint_bytes=retained_bytes["checkpoint"],
        ground_transaction_bytes=retained_bytes["transaction"],
        world_model_loop_bytes=retained_bytes["loop"],
        promotion_result_bytes=retained_bytes["promotion"],
    )


def test_retained_promotion_is_reconstructed_without_producer(verified) -> None:
    assert verified["valid"] is True
    assert verified["source_h2_proof_independently_recomputed"] is True
    assert verified["successor_h2_proof_independently_recomputed"] is True
    assert verified["promoted_epoch_identity_independently_recomputed"] is True
    assert verified["fresh_query_identity_independently_recomputed"] is True
    assert verified["cached_failure_consumption_independently_recomputed"] is True
    assert verified["new_local_ground_draw_count_verified"] == 0
    assert verified["local_recovery_reopened"] is False
    assert (
        verified["verified_next_route"]
        == "QUERY_IDENTITY_BOUND_DIRECT_GROUND_FALLBACK"
    )
    assert verified["promotion_producer_imported"] is False
    assert verified["recovery_loop_producer_imported"] is False
    assert verified["abstract_plan_certificate_verified"] is False
    assert verified["official_execution_allowed"] is False


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (("promoted_epoch", "promoted_numerical_model_id"), "a" * 64),
        (("promoted_epoch", "promoted_numerical_proof_id"), "b" * 64),
        (("promoted_consumption", "new_local_ground_draw_count"), 1),
        (("promoted_consumption", "local_allowed_after_result"), True),
        (("abstract_plan_certificate_issued",), True),
        (("official_execution_allowed",), True),
    ),
)
def test_fully_resigned_promotion_changes_are_rejected(
    retained_bytes,
    path,
    replacement,
) -> None:
    document = json.loads(retained_bytes["promotion"])
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(
        subject.ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error
    ):
        subject.verify_recovery_overlay_promotion_bytes_v1(
            checkpoint_bytes=retained_bytes["checkpoint"],
            ground_transaction_bytes=retained_bytes["transaction"],
            world_model_loop_bytes=retained_bytes["loop"],
            promotion_result_bytes=canonical_json_bytes(document),
        )


def test_unknown_field_and_noncanonical_bytes_are_rejected(retained_bytes) -> None:
    document = json.loads(retained_bytes["promotion"])
    document["forged"] = True
    with pytest.raises(
        subject.ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error
    ):
        subject.verify_recovery_overlay_promotion_bytes_v1(
            checkpoint_bytes=retained_bytes["checkpoint"],
            ground_transaction_bytes=retained_bytes["transaction"],
            world_model_loop_bytes=retained_bytes["loop"],
            promotion_result_bytes=canonical_json_bytes(document),
        )
    with pytest.raises(
        subject.ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error
    ):
        subject.verify_recovery_overlay_promotion_bytes_v1(
            checkpoint_bytes=retained_bytes["checkpoint"],
            ground_transaction_bytes=retained_bytes["transaction"],
            world_model_loop_bytes=retained_bytes["loop"],
            promotion_result_bytes=retained_bytes["promotion"] + b"\n",
        )
