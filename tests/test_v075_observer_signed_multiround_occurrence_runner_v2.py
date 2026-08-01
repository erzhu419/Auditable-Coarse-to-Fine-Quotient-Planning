from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import construction_operational_context_v3 as operational_context
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


REPOSITORY_ROOT = (
    "/home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning"
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-observer-signed-multiround-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _exact_schedule(namespace, *, context_index: int):
    arm = worker.V075WorkerArmV1.NO_PRIOR
    context = namespace.family.replicate_contexts[context_index]
    occurrence = (
        backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=(
                context_index * len(acquisition.ARM_ORDER)
                + acquisition.ARM_ORDER.index(arm)
            ),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    schedule = acquisition.freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        occurrence=occurrence,
    )
    slot = schedule.profile.occurrence_slot_for(
        context_id=context.context_id,
        arm=arm,
    )
    replayed, verification = (
        acquisition.verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            expected_slot=slot,
            occurrence_identity_bytes=canonical_json_bytes(
                occurrence.to_document()
            ),
            raw=schedule.canonical_bytes,
        )
    )
    assert replayed.schedule_id == schedule.schedule_id
    return schedule, verification


@pytest.fixture(scope="module")
def capped_closed_result():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture(  # noqa: SLF001
            "observer-signed-multiround-capped"
        )
    )
    # K7 has a complete dynamic child closure larger than the registered
    # 19-row cap.  It exercises a fully closed result without running the
    # intentionally expensive W7 all-18 acquisition.
    schedule, verification = _exact_schedule(namespace, context_index=0)
    roots = {}
    result = (
        runner.run_v075_construction_observer_signed_multiround_occurrence_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=verification,
            authority=authorization,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("capped-session"),
            evidence_sink=lambda values: roots.update(values),
        )
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
        "schedule": schedule,
        "verification": verification,
        "result": result,
        "roots": roots,
    }


def test_exact_root_schedule_closes_and_matches_full_recompile(
    capped_closed_result,
) -> None:
    result = capped_closed_result["result"]
    document = result.to_document()
    assert result.status is (
        runner.V075ObserverSignedMultiroundTerminalStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert document["child_closure_status"] == (
        "CHILD_ACTION_ROW_CAP_EXCEEDED"
    )
    assert len(document["child_closure_verification_id"]) == 64
    assert document["child_execution_ledger_id"] is None
    assert document["child_execution_verification_id"] is None
    assert document["child_replanning_barrier_id"] is None
    assert document["child_replanning_barrier_verification_id"] is None
    assert document["promotion_decision_ids"] == []
    assert document["promotion_decision_verification_ids"] == []
    assert document["promotion_replanning_barrier_ids"] == []
    assert document["promotion_replanning_barrier_verification_ids"] == []
    assert document["closed_lineage_recompiled"] is True
    assert document["partial_child_closure_permitted"] is False
    assert (
        document["raw_post_child_epoch_consumable_without_barrier"] is False
    )
    assert document["fresh_heldout_accessed"] is False
    assert document["official_execution_allowed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert result.canonical_bytes == canonical_json_bytes(document)


def test_owned_no_full_replay_context_skips_portable_epoch_rebuild(
    capped_closed_result,
    monkeypatch,
) -> None:
    values = capped_closed_result
    roots = values["roots"]

    with pytest.raises(
        runner.dynamic.V075LiveDynamicAcquisitionV2InvariantViolation,
        match="scoped no-full-replay context",
    ):
        (
            runner.dynamic
            .freeze_and_attest_v075_live_dynamic_child_closure_owned_v3(
                source_epoch=roots["root_model_epoch"],
                namespace=values["namespace"],
            )
        )

    def forbidden_replay(_epoch):
        raise AssertionError("owned operational child audit must not replay")

    monkeypatch.setattr(runner.dynamic, "_replay_epoch", forbidden_replay)
    monkeypatch.setattr(
        runner.live_model,
        "replay_v075_live_incremental_model_epoch_v2",
        forbidden_replay,
    )
    with operational_context._activate_owned_no_full_replay_v3():  # noqa: SLF001
        child_closure, child_verification = (
            runner.dynamic
            .freeze_and_attest_v075_live_dynamic_child_closure_owned_v3(
                source_epoch=roots["root_model_epoch"],
                namespace=values["namespace"],
            )
        )
        result = runner._closed_result(  # noqa: SLF001
            repository_root=REPOSITORY_ROOT,
            namespace=values["namespace"],
            status=(
                runner.V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ),
            schedule=values["schedule"],
            verification=values["verification"],
            root_execution=roots["root_execution"],
            root_epoch=roots["root_model_epoch"],
            child_closure=child_closure,
            child_closure_verification=child_verification,
            child_ledger=None,
            child_ledger_verification=None,
            child_barrier=None,
            child_barrier_verification=None,
            promotion_decisions=(),
            promotion_decision_verifications=(),
            promotion_barriers=(),
            promotion_barrier_verifications=(),
            final_epoch=roots["final_model_epoch"],
            reconciliation=roots["closed_reconciliation"],
        )
    assert result.status is (
        runner.V075ObserverSignedMultiroundTerminalStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED
    )
    assert operational_context.operational_no_full_replay_enabled_v3() is False


def test_schedule_verification_transplant_fails_before_observer_open(
    capped_closed_result,
    monkeypatch,
) -> None:
    values = capped_closed_result
    schedule = values["schedule"]
    foreign_schedule, foreign_verification = _exact_schedule(
        values["namespace"],
        context_index=1,
    )
    assert foreign_schedule.schedule_id != schedule.schedule_id
    opened = False

    def forbidden_open(**_kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("observer must remain unopened")

    monkeypatch.setattr(
        runner.control,
        "open_v075_construction_controlled_private_observer_v2",
        forbidden_open,
    )
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="initial schedule or verification exact replay failed",
    ):
        runner.run_v075_construction_observer_signed_multiround_occurrence_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=values["namespace"],
            schedule=schedule,
            schedule_verification=foreign_verification,
            authority=values["authorization"],
            private_salt=values["salt"],
            private_environment=(
                values["generated"].secret_laws_for_commitment()
            ),
            observer_signer=values["signer"],
            session_external_id=_id("must-not-open"),
        )
    assert opened is False


def test_support_promotion_templates_cannot_be_omitted_swapped_or_transplanted(
    capped_closed_result,
    monkeypatch,
) -> None:
    values = capped_closed_result
    schedule = values["schedule"]
    original_intents = schedule.intents
    promotion_indices = tuple(
        index
        for index, item in enumerate(original_intents)
        if item.kind
        is acquisition.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
    )
    assert len(promotion_indices) >= 2
    foreign_schedule, _ = _exact_schedule(
        values["namespace"],
        context_index=1,
    )
    foreign_promotion = next(
        item
        for item in foreign_schedule.intents
        if item.kind
        is acquisition.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
    )
    omitted = tuple(
        item
        for index, item in enumerate(original_intents)
        if index != promotion_indices[0]
    )
    swapped_items = list(original_intents)
    first, second = promotion_indices[:2]
    swapped_items[first], swapped_items[second] = (
        swapped_items[second],
        swapped_items[first],
    )
    transplanted_items = list(original_intents)
    transplanted_items[first] = foreign_promotion
    attacks = (
        omitted,
        tuple(swapped_items),
        tuple(transplanted_items),
    )
    observer_opened = False

    def forbidden_open(**_kwargs):
        nonlocal observer_opened
        observer_opened = True
        raise AssertionError("observer must remain unopened")

    monkeypatch.setattr(
        runner.control,
        "open_v075_construction_controlled_private_observer_v2",
        forbidden_open,
    )

    class ForbiddenExecutionController:
        occurrence_identity = schedule.occurrence
        controlled_appends = ()
        support_freezes = ()
        execution_started = False

        def prepare_batch_intent_v2(self, **_kwargs):
            self.execution_started = True
            raise AssertionError("execution must not begin")

    for attack_index, forged_intents in enumerate(attacks):
        object.__setattr__(schedule, "intents", forged_intents)
        try:
            with pytest.raises(
                runner.V075ObserverSignedMultiroundV2InvariantViolation,
                match="initial schedule or verification exact replay failed",
            ):
                runner.run_v075_construction_observer_signed_multiround_occurrence_v2(
                    repository_root=REPOSITORY_ROOT,
                    namespace=values["namespace"],
                    schedule=schedule,
                    schedule_verification=values["verification"],
                    authority=values["authorization"],
                    private_salt=values["salt"],
                    private_environment=(
                        values["generated"].secret_laws_for_commitment()
                    ),
                    observer_signer=values["signer"],
                    session_external_id=_id(
                        f"template-attack-{attack_index}"
                    ),
                )
            controller = ForbiddenExecutionController()
            with pytest.raises(
                runner.V075ObserverSignedMultiroundV2InvariantViolation,
                match="initial root execution boundary",
            ):
                runner._execute_initial_root_schedule(  # noqa: SLF001
                    controller=controller,
                    namespace=values["namespace"],
                    schedule=schedule,
                    verification=values["verification"],
                )
            assert controller.execution_started is False
        finally:
            object.__setattr__(schedule, "intents", original_intents)
    assert observer_opened is False


def test_root_execution_hash_binds_template_to_same_row_freeze() -> None:
    artifact = runner.V075ObserverSignedRootExecutionV2(
        _issuer=runner._ROOT_EXECUTION_ISSUER,  # noqa: SLF001
        schedule_id=_id("root-schedule"),
        schedule_verification_id=_id("root-schedule-verification"),
        occurrence_id=_id("root-occurrence"),
        resulting_head_id=_id("root-head"),
        open_prefix_verification_id=_id("root-prefix"),
        discovery_intent_ids=(_id("d0"), _id("d1")),
        discovery_receipt_ids=(_id("dr0"), _id("dr1")),
        support_promotion_template_ids=(_id("p0"), _id("p1")),
        support_freeze_ids=(_id("f0"), _id("f1")),
        support_promotion_freeze_bindings=(
            (_id("p0"), _id("f0")),
            (_id("p1"), _id("f1")),
        ),
        validation_intent_ids=(_id("v0"), _id("v1")),
        validation_receipt_ids=(_id("vr0"), _id("vr1")),
        root_row_binding_ids=(_id("r0"), _id("r1")),
    )
    assert artifact.to_document()["support_promotion_freeze_bindings"] == [
        {
            "support_promotion_template_id": _id("p0"),
            "support_freeze_id": _id("f0"),
        },
        {
            "support_promotion_template_id": _id("p1"),
            "support_freeze_id": _id("f1"),
        },
    ]
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="partial, duplicated, or caller-minted",
    ):
        replace(
            artifact,
            _issuer=runner._ROOT_EXECUTION_ISSUER,  # noqa: SLF001
            support_promotion_freeze_bindings=(
                (_id("p0"), _id("f1")),
                (_id("p1"), _id("f0")),
            ),
        )


def test_result_and_production_boundaries_reject_forgery(
    capped_closed_result,
) -> None:
    result = capped_closed_result["result"]
    with pytest.raises(
        runner.V075ObserverSignedMultiroundV2InvariantViolation,
        match="malformed or caller-minted",
    ):
        replace(
            result,
            _issuer=object(),
            status=(
                runner.V075ObserverSignedMultiroundTerminalStatusV2
                .CANDIDATE_EARLY_STOP
            ),
        )
    with pytest.raises(
        runner.V075ObserverSignedMultiroundProductionV2NotReady
    ):
        runner.open_v075_production_observer_signed_multiround_occurrence_v2()
