from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import pickle
import shutil

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    official_counter_registry_v1,
)
from acfqp.phase3e_ground_handoff_v1 import (
    GroundBindingAfterFailedAuditV1,
    Phase3EGroundHandoffV1Error,
    open_ground_binding_after_failed_audit_v1,
    require_ground_binding_after_failed_audit_v1,
)
from acfqp.phase3e_model_only_v1 import (
    Phase3EModelOnlyResultV1,
    run_phase3e_model_only_from_source_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    ModelOnlyRAPMSourceV1,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import TypedNotApplicable
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _model_only_case(
    *,
    query_key: str,
    regret_tolerance: Fraction = Fraction(1, 20),
) -> tuple[
    ModelOnlyRAPMSourceV1,
    Phase3EModelOnlyResultV1,
    SemanticVerificationResultV1,
]:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=query_key)
    result = run_phase3e_model_only_from_source_v1(
        source, regret_tolerance=regret_tolerance
    )
    binding = AttestationContextV1(
        result.route_context,
        TypedNotApplicable("abstract audit precedes route decision"),
        TypedNotApplicable("abstract audit precedes local transaction"),
        3,
        LaneEnum.OPERATIONAL,
    )
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(SemanticRole.ABSTRACT_AUDIT)
    work = CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.OPERATIONAL),
        1,
        recorder_id="abstract-audit-handoff-test-v1",
    )
    authority = verify_abstract_plan_audit_semantics_v1(
        result.audit,
        source=source,
        model_only_result=result,
        binding=binding,
        verification_work_record=work,
    )
    return source, result, authority


def test_failed_audit_is_the_unique_boundary_before_ground_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c
    import acfqp.phase3e_fallback_v1 as fallback
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    original_loader = frozen_phase3c.load_frozen_phase3c_world
    original_identity = fallback.safe_chain_fallback_context_identity_v1
    calls: list[str] = []

    def forbidden_planner(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("post-failure handoff repeated the portable planner")

    def spy_loader(*args: object, **kwargs: object) -> object:
        calls.append("ground_loader")
        return original_loader(*args, **kwargs)

    def spy_identity(*args: object, **kwargs: object) -> dict[str, str]:
        calls.append("ground_identity")
        return original_identity(*args, **kwargs)

    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden_planner)
    monkeypatch.setattr(
        model_only, "run_phase3e_model_only_from_source_v1", forbidden_planner
    )
    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", spy_loader)
    monkeypatch.setattr(
        fallback, "safe_chain_fallback_context_identity_v1", spy_identity
    )

    binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    assert calls == ["ground_loader", "ground_identity"]
    assert isinstance(binding, GroundBindingAfterFailedAuditV1)
    assert require_ground_binding_after_failed_audit_v1(binding) is binding
    assert binding.semantic_authority is authority
    assert binding.model_only_result_id == result.result_id
    assert binding.source_lease_id == result.source_lease.source_lease_id
    assert binding.selected_plan_id == result.selected_plan.selected_contingent_plan_id
    assert binding.sound_proof_id == result.sound_proof.proof_id
    assert binding.abstract_audit_id == result.audit.audit_id
    assert binding.route_decision_context_id == (
        result.route_context.route_decision_context_id
    )
    assert binding.structural_id == result.identities.structural_id
    assert binding.query_id == result.identities.query_id
    assert binding.build_epoch_id == result.identities.build_epoch_id
    assert binding.manifest_id == result.identities.manifest_id
    assert binding.portable_rapm_id == result.identities.portable_rapm_id
    assert binding.world.build_epoch["build_epoch_id"] == (
        result.source_lease.legacy_build_epoch_id
    )
    assert binding.metadata()["ground_binding_id"] == binding.ground_binding_id


def test_pass_result_and_pass_authority_are_rejected_before_ground_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c

    _source, result, authority = _model_only_case(query_key=ABSTRACT_QUERY_KEY)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("PASS opened the ground namespace")

    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="forbidden unless the model-only result is FAIL",
    ):
        open_ground_binding_after_failed_audit_v1(
            PHASE3C,
            model_only_result=result,
            abstract_audit_authority=authority,
        )


@pytest.mark.parametrize("raw_kind", ["audit", "hash", "attestation"])
def test_raw_or_hash_only_audit_claims_are_rejected_before_ground_loader(
    raw_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c

    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    raw_claim: object = {
        "audit": result.audit,
        "hash": result.audit.audit_id,
        "attestation": authority.attestation,
    }[raw_kind]

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("raw/hash-only audit claim opened ground")

    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="retained SemanticVerificationResultV1",
    ):
        open_ground_binding_after_failed_audit_v1(
            PHASE3C,
            model_only_result=result,
            abstract_audit_authority=raw_claim,  # type: ignore[arg-type]
        )


def test_foreign_failed_audit_context_is_rejected_before_ground_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c

    _source, result, _authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    _foreign_source, _foreign_result, foreign_authority = _model_only_case(
        query_key=LOCAL_QUERY_KEY,
        regret_tolerance=Fraction(1, 10),
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("foreign semantic context opened ground")

    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)
    with pytest.raises(Phase3EGroundHandoffV1Error, match="foreign route context"):
        open_ground_binding_after_failed_audit_v1(
            PHASE3C,
            model_only_result=result,
            abstract_audit_authority=foreign_authority,
        )


@pytest.mark.parametrize(
    "relative_path",
    ["build/portable_rapm.json", "build/epoch.json"],
)
def test_bundle_model_or_epoch_swap_fails_before_ground_loader(
    relative_path: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c

    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    swapped = tmp_path / "phase3c"
    shutil.copytree(PHASE3C, swapped)
    path = swapped / relative_path
    path.write_bytes(path.read_bytes() + b" ")

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("swapped model/epoch reached the ground loader")

    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="source/result replay failed before ground binding",
    ):
        open_ground_binding_after_failed_audit_v1(
            swapped,
            model_only_result=result,
            abstract_audit_authority=authority,
        )


def test_ground_identity_swap_is_rejected_after_authorized_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.frozen_phase3c as frozen_phase3c
    import acfqp.phase3e_fallback_v1 as fallback

    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    original_loader = frozen_phase3c.load_frozen_phase3c_world
    original_identity = fallback.safe_chain_fallback_context_identity_v1
    loader_calls = 0

    def spy_loader(*args: object, **kwargs: object) -> object:
        nonlocal loader_calls
        loader_calls += 1
        return original_loader(*args, **kwargs)

    def swapped_identity(world: object) -> dict[str, str]:
        identities = original_identity(world)
        return {**identities, "portable_rapm_id": "0" * 64}

    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", spy_loader)
    monkeypatch.setattr(
        fallback, "safe_chain_fallback_context_identity_v1", swapped_identity
    )
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="identity mismatch for portable_rapm_id",
    ):
        open_ground_binding_after_failed_audit_v1(
            PHASE3C,
            model_only_result=result,
            abstract_audit_authority=authority,
        )
    assert loader_calls == 1


def test_metadata_cannot_substitute_for_live_ground_capability() -> None:
    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=result,
        abstract_audit_authority=authority,
    )
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="authority-bearing live capability",
    ):
        require_ground_binding_after_failed_audit_v1(  # type: ignore[arg-type]
            binding.metadata()
        )


def test_ground_binding_cannot_be_copied_replaced_pickled_or_member_spliced() -> None:
    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    for copier, message in (
        (copy.copy, "cannot be copied"),
        (copy.deepcopy, "cannot be deep-copied"),
    ):
        with pytest.raises(Phase3EGroundHandoffV1Error, match=message):
            copier(binding)
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="cannot be serialized",
    ):
        pickle.dumps(binding)
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="copied or modified live authority",
    ):
        replace(binding)
    assert binding._instance_mint is not None
    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="copied or modified live authority",
    ):
        replace(
            binding,
            _mint=copy.copy(binding._mint),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "verification_work_record_id",
        "bound_ground_action_catalogue_id",
        "locality_metadata_id",
    ),
)
def test_dataclasses_replace_cannot_splice_ground_binding_identity(
    field_name: str,
) -> None:
    _source, result, authority = _model_only_case(query_key=LOCAL_QUERY_KEY)
    binding = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=result,
        abstract_audit_authority=authority,
    )

    with pytest.raises(
        Phase3EGroundHandoffV1Error,
        match="copied or modified live authority",
    ):
        replace(binding, **{field_name: binding.model_only_result_id})
