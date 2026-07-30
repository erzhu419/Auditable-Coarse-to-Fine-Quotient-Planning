from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_five_arm_acquisition_authority_v2 as authority
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as namespace_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-five-arm-acquisition-v2-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _occurrence(
    namespace,
    *,
    context_ordinal: int,
    arm: worker.V075WorkerArmV1,
):
    context = namespace.family.replicate_contexts[context_ordinal]
    source = (
        occurrence_plan.load_tracked_v075_source_prior_transport_v1(
            REPOSITORY_ROOT
        )
        if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        else None
    )
    arm_ordinal = authority.ARM_ORDER.index(arm)
    return (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=(
                context_ordinal * len(authority.ARM_ORDER) + arm_ordinal
            ),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=source,
        )
    )


def _own_artifacts(value: Any):
    if isinstance(value, dict):
        schema = value.get("schema")
        if (
            isinstance(schema, str)
            and schema.startswith("acfqp.v075_five_arm_")
        ):
            yield value
        for child in value.values():
            yield from _own_artifacts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _own_artifacts(child)


@pytest.fixture(scope="module")
def static_graph():
    _generated, _salt, namespace, _authorization, _signer = (
        namespace_fixture._fixture("five-arm-acquisition-v2")
    )
    occurrences = {
        arm: _occurrence(namespace, context_ordinal=0, arm=arm)
        for arm in authority.ARM_ORDER
    }
    schedules = {
        arm: authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=occurrence,
        )
        for arm, occurrence in occurrences.items()
    }
    return namespace, occurrences, schedules


def test_profile_is_v2_namespace_bound_and_five_arms_do_not_collapse(
    static_graph,
):
    namespace, _occurrences, schedules = static_graph
    profile = schedules[authority.ARM_ORDER[0]].profile
    assert profile.namespace.target_tape_namespace_id == (
        namespace.target_tape_namespace_id
    )
    assert profile.to_document()["workload_id"] == namespace.workload.workload_id
    assert profile.to_document()["threshold_profile_id"] == (
        namespace.workload.threshold_profile.threshold_profile_id
    )
    assert profile.to_document()["cap_profile_id"] == (
        namespace.workload.cap_profile.cap_profile_id
    )
    assert tuple(item.arm for item in profile.registrations) == (
        authority.ARM_ORDER
    )
    assert len({item.registration_id for item in profile.registrations}) == 5
    v1_ids = {
        item.registration_id
        for item in worker.freeze_v075_worker_registry_draft_v1().registrations
    }
    assert not {
        item.registration_id for item in profile.registrations
    } & v1_ids
    document = profile.to_document()
    assert document["support_selection_rule"] == (
        "ALL_DISTINCT_SIGNED_DISCOVERY_SUPPORT"
    )
    assert document["maximum_adaptive_rounds"] == 2
    assert document["direct_validation_checkpoints"] == [
        2_048,
        4_096,
        8_192,
        16_384,
    ]
    assert [item["context_id"] for item in document["context_bindings"]] == [
        item.context_id for item in namespace.family.replicate_contexts
    ]
    assert len(profile.occurrence_slots) == 15
    assert [item.occurrence_ordinal for item in profile.occurrence_slots] == (
        list(range(15))
    )
    assert all(
        item["complete_root_action_count"] == 2
        for item in document["context_bindings"]
    )

    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            profile,
            registrations=(
                profile.registrations[0],
                profile.registrations[0],
                *profile.registrations[2:],
            ),
        )


def test_proposal_views_are_arm_distinct_source_exclusive_and_exact(
    static_graph,
):
    _namespace, _occurrences, schedules = static_graph
    source = schedules[
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    ].proposal_view
    no_prior = schedules[
        worker.V075WorkerArmV1.NO_PRIOR
    ].proposal_view
    wrong = schedules[
        worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR
    ].proposal_view
    ood = schedules[
        worker.V075WorkerArmV1.OOD_ABSTENTION
    ].proposal_view
    direct = schedules[
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ].proposal_view

    assert source is not None
    assert no_prior is not None
    assert wrong is not None
    assert ood is not None
    assert direct is None
    assert source.feature_midranks == tuple(
        sorted(authority.REGISTERED_FORWARD_MIDRANKS)
    )
    assert source.source_transport_id is not None
    assert source.source_adapter_id is not None
    assert source.source_verification_id is not None
    assert no_prior.feature_midranks == ()
    assert all(
        value is None
        for value in (
            no_prior.source_transport_id,
            no_prior.source_adapter_id,
            no_prior.source_verification_id,
            no_prior.source_catalogue_id,
        )
    )
    assert wrong.feature_midranks == (
        authority.REGISTERED_WRONG_REVERSED_MIDRANKS
    )
    assert dict(wrong.feature_midranks) == {
        key: 1 - value
        for key, value in authority.REGISTERED_FORWARD_MIDRANKS
    }
    assert wrong.fixed_control_id == authority.WRONG_FIXED_CONTROL_ID
    assert wrong.source_transport_id is None
    assert ood.feature_midranks == ()
    assert ood.applicable_feature_schema_id == (
        authority.OOD_INCOMPATIBLE_FEATURE_SCHEMA_ID
    )
    assert ood.applicable_feature_schema_id != (
        authority.SOURCE_FEATURE_SCHEMA_ID
    )
    assert len(
        {
            item.proposal_view_id
            for item in (source, no_prior, wrong, ood)
        }
    ) == 4


def test_wrong_no_prior_ood_and_direct_never_read_source_transport(
    static_graph,
    monkeypatch,
):
    namespace, occurrences, _schedules = static_graph

    def forbidden(_root):
        raise AssertionError("non-SOURCE arm tried to read source transport")

    monkeypatch.setattr(
        occurrence_plan,
        "load_tracked_v075_source_prior_transport_v1",
        forbidden,
    )
    for arm in (
        worker.V075WorkerArmV1.NO_PRIOR,
        worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
        worker.V075WorkerArmV1.OOD_ABSTENTION,
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
    ):
        schedule = (
            authority
            .freeze_v075_occurrence_initial_acquisition_schedule_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=namespace,
                occurrence=occurrences[arm],
            )
        )
        assert schedule.occurrence.arm is arm

    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=occurrences[
                worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ],
        )


def test_adaptive_and_direct_initial_schedules_freeze_complete_dependencies(
    static_graph,
):
    _namespace, _occurrences, schedules = static_graph
    for arm in authority.ADAPTIVE_ARM_ORDER:
        schedule = schedules[arm]
        assert len(schedule.intents) == 6
        assert [item.kind for item in schedule.intents] == [
            authority.V075InitialIntentKindV2.ROOT_DISCOVERY,
            authority.V075InitialIntentKindV2.ROOT_DISCOVERY,
            authority.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE,
            authority.V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE,
            authority.V075InitialIntentKindV2.ROOT_VALIDATION,
            authority.V075InitialIntentKindV2.ROOT_VALIDATION,
        ]
        discovery = schedule.intents[:2]
        promotion = schedule.intents[2:4]
        validation = schedule.intents[4:]
        assert [item.accepted_draw_count for item in discovery] == [64, 64]
        assert [item.accepted_draw_cap for item in discovery] == [64, 64]
        assert [item.accepted_draw_count for item in promotion] == [0, 0]
        assert [item.dependency_intent_ids for item in promotion] == [
            (discovery[0].intent_id,),
            (discovery[1].intent_id,),
        ]
        assert [item.accepted_draw_count for item in validation] == [
            2_048,
            2_048,
        ]
        assert [item.accepted_draw_cap for item in validation] == [
            6_144,
            6_144,
        ]
        assert [item.dependency_intent_ids for item in validation] == [
            (promotion[0].intent_id,),
            (promotion[1].intent_id,),
        ]
        assert schedule.initial_committed_draws == 4_224
        assert schedule.sound_route_draw_upper == 165_184

    direct = schedules[worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND]
    assert direct.proposal_view is None
    assert len(direct.intents) == 4
    assert all(
        item.kind
        is not authority.V075InitialIntentKindV2.ROOT_VALIDATION
        for item in direct.intents
    )
    assert direct.initial_committed_draws == 128
    assert direct.sound_route_draw_upper == 345_408
    document = direct.to_document()
    assert document["direct_child_catalogues_present"] is False
    assert document["direct_child_rows_present"] is False
    assert document["direct_child_expansion_rule"] == (
        authority.DIRECT_CHILD_EXPANSION_RULE
    )
    assert document["direct_checkpoint_rule"] == (
        authority.DIRECT_CHECKPOINT_RULE
    )


def test_every_v2_static_artifact_has_zero_pretarget_access(static_graph):
    _namespace, occurrences, schedules = static_graph
    for arm, schedule in schedules.items():
        occurrence_bytes = canonical_json_bytes(
            occurrences[arm].to_document()
        )
        replayed, verification = (
            authority
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=schedule.profile.namespace,
                expected_slot=schedule.profile.occurrence_slot_for(
                    context_id=occurrences[arm].context_id,
                    arm=arm,
                ),
                occurrence_identity_bytes=occurrence_bytes,
                raw=schedule.canonical_bytes,
            )
        )
        assert replayed.schedule_id == schedule.schedule_id
        artifacts = tuple(
            _own_artifacts(
                {
                    "schedule": schedule.to_document(),
                    "verification": verification.to_document(),
                }
            )
        )
        assert artifacts
        for artifact in artifacts:
            assert artifact["observer_calls"] == 0
            assert artifact["kernel_calls"] == 0
            assert artifact["target_access_count"] == 0
            assert artifact["target_accessed"] is False
            assert artifact["official_execution_allowed"] is False
            assert artifact["scientific_endpoint_credit_allowed"] is False
            assert artifact["production_authorizing"] is False


def _mutated_schedule_bytes(schedule, mutation: str) -> bytes:
    document = loads_canonical_json(schedule.canonical_bytes)
    assert isinstance(document, dict)
    if mutation == "row_omission":
        document["intents"].pop(0)
    elif mutation == "row_reorder":
        document["intents"][0], document["intents"][1] = (
            document["intents"][1],
            document["intents"][0],
        )
    elif mutation == "count":
        document["intents"][0]["accepted_draw_count"] = 63
    elif mutation == "cap":
        document["intents"][-1]["accepted_draw_cap"] = 6_145
    elif mutation == "unknown":
        document["attacker_unknown_field"] = True
    else:  # pragma: no cover
        raise AssertionError(mutation)
    return canonical_json_bytes(document)


@pytest.mark.parametrize(
    "mutation",
    ("row_omission", "row_reorder", "count", "cap", "unknown"),
)
def test_canonical_verifier_rejects_row_order_count_cap_and_unknown_attacks(
    static_graph,
    mutation,
):
    namespace, occurrences, schedules = static_graph
    arm = worker.V075WorkerArmV1.NO_PRIOR
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        (
            authority
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=namespace,
                expected_slot=schedules[arm].profile.occurrence_slot_for(
                    context_id=occurrences[arm].context_id,
                    arm=arm,
                ),
                occurrence_identity_bytes=canonical_json_bytes(
                    occurrences[arm].to_document()
                ),
                raw=_mutated_schedule_bytes(schedules[arm], mutation),
            )
        )


def test_source_fake_missing_and_nonsource_injection_are_rejected(
    static_graph,
    tmp_path,
):
    namespace, occurrences, _schedules = static_graph
    source = occurrences[
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    ]
    fake_source = replace(source, source_transport_id=_id("fake-source"))
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=fake_source,
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=tmp_path,
            namespace=namespace,
            occurrence=source,
        )

    no_prior = occurrences[worker.V075WorkerArmV1.NO_PRIOR]
    with pytest.raises(
        identity_backend.V075BatchNativeBackendInvariantViolation
    ):
        replace(
            no_prior,
            source_transport_id=source.source_transport_id,
        )


def test_ood_schema_and_direct_proposal_attacks_are_rejected(static_graph):
    _namespace, _occurrences, schedules = static_graph
    ood = schedules[
        worker.V075WorkerArmV1.OOD_ABSTENTION
    ].proposal_view
    no_prior = schedules[
        worker.V075WorkerArmV1.NO_PRIOR
    ].proposal_view
    assert ood is not None
    assert no_prior is not None
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            ood,
            applicable_feature_schema_id=authority.SOURCE_FEATURE_SCHEMA_ID,
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            no_prior,
            arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        )


def test_namespace_and_occurrence_transplants_are_rejected(static_graph):
    namespace, occurrences, schedules = static_graph
    arm = worker.V075WorkerArmV1.NO_PRIOR
    other_occurrence = _occurrence(
        namespace,
        context_ordinal=1,
        arm=arm,
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        (
            authority
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=namespace,
                expected_slot=schedules[arm].profile.occurrence_slot_for(
                    context_id=occurrences[arm].context_id,
                    arm=arm,
                ),
                occurrence_identity_bytes=canonical_json_bytes(
                    other_occurrence.to_document()
                ),
                raw=schedules[arm].canonical_bytes,
            )
        )

    _g, _s, other_namespace, _a, _signer = (
        namespace_fixture._fixture("five-arm-acquisition-v2-transplant")
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        (
            authority
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=other_namespace,
                expected_slot=schedules[arm].profile.occurrence_slot_for(
                    context_id=occurrences[arm].context_id,
                    arm=arm,
                ),
                occurrence_identity_bytes=canonical_json_bytes(
                    occurrences[arm].to_document()
                ),
                raw=schedules[arm].canonical_bytes,
            )
        )


def test_object_new_forged_occurrence_and_schedule_are_rejected(
    static_graph,
):
    namespace, occurrences, _schedules = static_graph
    forged_occurrence = object.__new__(
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=forged_occurrence,
        )

    forged_schedule = object.__new__(
        authority.V075InitialAcquisitionScheduleV2
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.replay_v075_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=forged_schedule,
        )


def test_profile_byte_verifier_is_exact_and_rejects_unknown_fields(
    static_graph,
):
    namespace, _occurrences, schedules = static_graph
    profile = schedules[authority.ARM_ORDER[0]].profile
    assert (
        authority.verify_v075_five_arm_acquisition_profile_bytes_v2(
            namespace=namespace,
            raw=profile.canonical_bytes,
        ).profile_id
        == profile.profile_id
    )
    document = loads_canonical_json(profile.canonical_bytes)
    document["unknown"] = 1
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.verify_v075_five_arm_acquisition_profile_bytes_v2(
            namespace=namespace,
            raw=canonical_json_bytes(document),
        )


def test_typed_intent_and_schedule_reject_cross_context_root_transplants(
    static_graph,
):
    namespace, _occurrences, schedules = static_graph
    arm = worker.V075WorkerArmV1.NO_PRIOR
    other_occurrence = _occurrence(
        namespace,
        context_ordinal=1,
        arm=arm,
    )
    other_schedule = (
        authority.freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=other_occurrence,
        )
    )
    original = schedules[arm]
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            original.intents[0],
            row_binding=other_schedule.intents[0].row_binding,
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            original.intents[0],
            occurrence=other_occurrence,
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            original,
            intents=(
                other_schedule.intents[0],
                *original.intents[1:],
            ),
        )

    direct = schedules[worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND]
    wrong_ordinal = replace(
        direct.occurrence,
        occurrence_ordinal=direct.occurrence.occurrence_ordinal + 100,
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation,
        match="context-major",
    ):
        replace(
            direct.intents[0],
            occurrence=wrong_ordinal,
            occurrence_id=wrong_ordinal.occurrence_id,
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation,
        match="context-major",
    ):
        replace(direct, occurrence=wrong_ordinal)

    wrong_threshold = replace(
        direct.occurrence,
        threshold_profile_id=_id("foreign-threshold"),
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation,
        match="threshold/cap",
    ):
        replace(direct, occurrence=wrong_threshold)


def test_source_proposal_intrinsically_binds_typed_tracked_provenance(
    static_graph,
):
    _namespace, _occurrences, schedules = static_graph
    proposal = schedules[
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    ].proposal_view
    assert proposal is not None
    provenance = proposal.source_provenance
    assert provenance is not None
    assert provenance.to_document()["complete_tracked_authority_replayed"]
    assert provenance.source_transport_id == proposal.source_transport_id
    assert provenance.source_adapter_id == proposal.source_adapter_id
    assert provenance.source_verification_id == (
        proposal.source_verification_id
    )
    assert {
        "source_transport_id",
        "source_adapter_id",
        "source_verification_id",
        "source_catalogue_id",
    }.isdisjoint(proposal.__dataclass_fields__)
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            provenance,
            source_catalogue_id=_id("fake-source-catalogue"),
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(proposal, source_provenance=None)

    verification = loads_canonical_json(
        provenance.transport.verification_bytes
    )
    verification.pop("verification_id")
    verification["attacker_marker"] = "self-consistent-but-untracked"
    forged_verification_id = hashlib.sha256(
        worker.SOURCE_PRIOR_VERIFICATION_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(verification)
    ).hexdigest()
    forged_transport = worker.V075SourcePriorTransportV1(
        provenance.transport.adapter_bytes,
        canonical_json_bytes(
            {
                **verification,
                "verification_id": forged_verification_id,
            }
        ),
        provenance.transport.adapter_id,
        forged_verification_id,
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation,
        match="preregistered source archive",
    ):
        replace(provenance, transport=forged_transport)


def test_adaptive_intents_bind_future_proposals_without_claiming_execution(
    static_graph,
):
    _namespace, _occurrences, schedules = static_graph
    proposal_ids = set()
    for arm in authority.ADAPTIVE_ARM_ORDER:
        schedule = schedules[arm]
        assert schedule.proposal_view is not None
        proposal_ids.add(schedule.proposal_view.proposal_view_id)
        expected_rule = authority.PROPOSAL_USE_RULES[arm]
        assert schedule.proposal_use_rule == expected_rule
        assert schedule.to_document()["proposal_ranking_executed"] is False
        assert (
            schedule.to_document()[
                "future_adaptive_round_must_consume_proposal"
            ]
            is True
        )
        assert all(
            item.proposal_view is schedule.proposal_view
            and item.to_document()["proposal_view_id"]
            == schedule.proposal_view.proposal_view_id
            and item.proposal_use_rule == expected_rule
            and item.to_document()["proposal_input_binding_mandatory"] is True
            and item.to_document()["proposal_ranking_executed"] is False
            for item in schedule.intents
        )
        with pytest.raises(
            authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
        ):
            replace(schedule.intents[0], proposal_view=None)
        with pytest.raises(
            authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
        ):
            replace(
                schedule.intents[0],
                proposal_use_rule=(
                    authority.PROPOSAL_USE_RULES[
                        worker.V075WorkerArmV1.NO_PRIOR
                    ]
                    + "_ATTACK"
                ),
            )
        with pytest.raises(
            authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
        ):
            replace(
                schedule,
                proposal_use_rule=expected_rule + "_IGNORED",
            )
    assert len(proposal_ids) == 4

    source = schedules[
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    ]
    no_prior = schedules[worker.V075WorkerArmV1.NO_PRIOR]
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(source.intents[0], proposal_view=no_prior.proposal_view)

    ood = schedules[worker.V075WorkerArmV1.OOD_ABSTENTION]
    assert ood.proposal_view is not None
    assert ood.proposal_view.to_document()["explicit_abstention"] is True
    assert ood.to_document()["ood_explicit_abstention_required"] is True
    assert all(
        item.to_document()["ood_explicit_abstention_required"] is True
        for item in ood.intents
    )


def test_proposal_and_verification_typed_witnesses_reject_replace_and_object_new(
    static_graph,
):
    namespace, occurrences, schedules = static_graph
    arm = worker.V075WorkerArmV1.NO_PRIOR
    schedule = schedules[arm]
    proposal = schedule.proposal_view
    assert proposal is not None

    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            proposal,
            target_tape_namespace_id=_id("proposal-foreign-namespace"),
        )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            proposal,
            occurrence_id=_id("proposal-foreign-occurrence"),
        )

    forged = object.__new__(authority.V075ProposalViewV2)
    for name in (
        "_issuer",
        "profile",
        "occurrence",
        "target_tape_namespace_id",
        "occurrence_id",
        "arm",
        "disposition",
        "applicable_feature_schema_id",
        "feature_midranks",
        "source_provenance",
        "fixed_control_id",
        "_proposal_view_id",
    ):
        object.__setattr__(forged, name, getattr(proposal, name))
    object.__setattr__(
        forged,
        "disposition",
        authority.V075ProposalDispositionV2.WRONG_FIXED_REVERSED_MIDRANK,
    )
    object.__setattr__(
        forged,
        "feature_midranks",
        authority.REGISTERED_WRONG_REVERSED_MIDRANKS,
    )
    object.__setattr__(
        forged,
        "fixed_control_id",
        authority.WRONG_FIXED_CONTROL_ID,
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(schedule, proposal_view=forged)

    slot = schedule.profile.occurrence_slot_for(
        context_id=occurrences[arm].context_id,
        arm=arm,
    )
    _replayed, verification = (
        authority
        .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            expected_slot=slot,
            occurrence_identity_bytes=canonical_json_bytes(
                occurrences[arm].to_document()
            ),
            raw=schedule.canonical_bytes,
        )
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        replace(
            verification,
            schedule_bytes_sha256=_id("forged-schedule-digest"),
        )
    assert (
        authority.verify_v075_initial_acquisition_verification_bytes_v2(
            schedule=schedule,
            expected_slot=slot,
            raw=verification.canonical_bytes,
        ).verification_id
        == verification.verification_id
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        authority.verify_v075_initial_acquisition_verification_bytes_v2(
            schedule=schedule,
            expected_slot=slot,
            raw=verification.canonical_bytes + b" ",
        )


def test_initial_commitment_and_sound_route_upper_are_distinct_exact_formulas(
    static_graph,
):
    _namespace, _occurrences, schedules = static_graph
    profile_document = schedules[authority.ARM_ORDER[0]].profile.to_document()
    assert profile_document["new_child_discovery_draws_per_row"] == 64
    assert profile_document["new_child_validation_draws_per_row"] == 8_192
    assert profile_document["maximum_new_child_action_rows"] == 19
    assert profile_document["maximum_dynamic_child_base_draws"] == 156_864
    assert profile_document["maximum_dynamic_promotion_draws"] == 4_096
    assert profile_document["maximum_selected_rows_per_adaptive_round"] == 1
    assert profile_document["adaptive_round_selection_rule"] == (
        authority.ADAPTIVE_ROUND_SELECTION_RULE
    )
    assert (
        profile_document["maximum_incremental_draws_per_adaptive_arm"]
        == 160_960
        == 19 * (64 + 8_192) + 2 * 2_048
    )
    assert profile_document["direct_validation_checkpoints"] == [
        2_048,
        4_096,
        8_192,
        16_384,
    ]
    assert profile_document["direct_maximum_validation_checkpoint"] == 16_384

    for arm in authority.ADAPTIVE_ARM_ORDER:
        document = schedules[arm].to_document()
        assert document["initial_root_discovery_draws"] == 2 * 64 == 128
        assert document["initial_root_validation_draws"] == 2 * 2_048 == 4_096
        assert document["initial_committed_draws"] == 4_224
        assert document["maximum_dynamic_child_discovery_draws"] == 1_216
        assert document["maximum_dynamic_child_validation_draws"] == 155_648
        assert document["maximum_dynamic_promotion_draws"] == 4_096
        assert document["sound_route_draw_upper"] == (
            4_224 + 160_960
        ) == 165_184
        assert document["initial_committed_draws_are_not_route_upper"] is True

    direct = schedules[worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND]
    document = direct.to_document()
    assert document["initial_committed_draws"] == 2 * 64 == 128
    assert document["maximum_dynamic_child_discovery_draws"] == 19 * 64
    assert document["direct_maximum_validation_rows"] == 2 + 19 == 21
    assert document["direct_maximum_validation_draws"] == 21 * 16_384
    assert document["sound_route_draw_upper"] == (
        128 + 19 * 64 + 21 * 16_384
    ) == 345_408


def test_forged_arm_is_rejected_before_source_loader_access(
    static_graph,
    monkeypatch,
):
    namespace, occurrences, schedules = static_graph
    arm = worker.V075WorkerArmV1.NO_PRIOR
    document = loads_canonical_json(
        canonical_json_bytes(occurrences[arm].to_document())
    )
    document["arm"] = (
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR.value
    )
    calls = []

    def source_spy(_root):
        calls.append("source-read")
        raise AssertionError("forged arm triggered tracked SOURCE access")

    monkeypatch.setattr(
        occurrence_plan,
        "load_tracked_v075_source_prior_transport_v1",
        source_spy,
    )
    with pytest.raises(
        authority.V075FiveArmAcquisitionAuthorityV2InvariantViolation
    ):
        (
            authority
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                namespace=namespace,
                expected_slot=schedules[arm].profile.occurrence_slot_for(
                    context_id=occurrences[arm].context_id,
                    arm=arm,
                ),
                occurrence_identity_bytes=canonical_json_bytes(document),
                raw=schedules[arm].canonical_bytes,
            )
        )
    assert calls == []
