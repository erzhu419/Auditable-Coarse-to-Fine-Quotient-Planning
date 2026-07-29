from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.transfer_guided_acquisition_preregistration_v1 as v072
import acfqp.v075_fresh_campaign_authority_v1 as v075


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_all_new_authority_domains_are_unique_and_v075_only() -> None:
    assert len(v075.DOMAIN_TAGS) == len(set(v075.DOMAIN_TAGS.values()))
    assert all(
        domain.startswith("acfqp:v075-")
        for domain in v075.DOMAIN_TAGS.values()
    )


def test_historical_disposition_is_typed_and_frozen() -> None:
    registry = v075.freeze_historical_identity_disposition_registry_v1()
    assert (
        registry.historical_failure_record_ids
        == v075.HISTORICAL_FAILURE_RECORD_IDS
    )
    assert (
        registry.forbidden_v072_target_identity_ids
        == v075.FORBIDDEN_V072_TARGET_IDENTITY_IDS
    )
    assert set(registry.allowed_source_only_upstream_ids).isdisjoint(
        registry.forbidden_v072_target_identity_ids
    )
    assert set(registry.allowed_structural_topology_ids).isdisjoint(
        registry.forbidden_v072_target_identity_ids
    )
    document = registry.to_document()
    assert document["v072_target_evidence_reuse_allowed"] is False
    assert document["v072_attempt_resume_or_retry_allowed"] is False
    assert all(
        item["scientific_input_allowed"] is False
        for item in document["historical_failure_records"]
    )

    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(
            registry,
            historical_failure_record_ids=(
                registry.historical_failure_record_ids[1],
                registry.historical_failure_record_ids[0],
            ),
        )


def test_family_contains_three_same_structure_fresh_replicates() -> None:
    family = v075.freeze_v075_target_family_generation_v1()
    contexts = family.replicate_contexts
    old_contexts = v072.registered_heldout_public_contexts_v2()

    assert len(contexts) == 3
    assert tuple(context.replicate_ordinal for context in contexts) == (0, 1, 2)
    assert tuple(context.topology.topology_id for context in contexts) == tuple(
        context.topology.topology_id for context in old_contexts
    )
    assert set(context.context_id for context in contexts).isdisjoint(
        context.context_id for context in old_contexts
    )
    assert all(context.horizon == 2 for context in contexts)
    assert all(context.root_ranks == (1, 1, 2, 0, 0, 0, 0) for context in contexts)
    assert all(context.risk_tolerance == Fraction(1, 20) for context in contexts)
    assert all(
        context.normalized_regret_tolerance == Fraction(1, 20)
        for context in contexts
    )
    assert all(context.target_execution_allowed is False for context in contexts)
    assert family.historical_target_evidence_used is False
    assert family.target_tapes_opened is False
    assert family.target_observations_generated == 0
    assert family.target_execution_allowed is False
    assert (
        family.to_document()["fresh_identity_not_new_structural_generality"]
        is True
    )


def test_public_replicate_contexts_do_not_serialize_hidden_laws() -> None:
    family = v075.freeze_v075_target_family_generation_v1()
    for context in family.replicate_contexts:
        document = context.to_document()
        assert "rank_probabilities" not in document
        assert document["hidden_law_serialized"] is False
        assert document["target_execution_allowed"] is False


def test_fresh_environment_uses_new_exact_preregistered_laws() -> None:
    environment = v075.freeze_v075_environment_manifest_v1()
    old_environment = v072.frozen_heldout_environment_manifest_v1()

    assert tuple(law.rank_probabilities for law in environment.laws) == (
        (
            (1, Fraction(991, 1_000)),
            (2, Fraction(7, 1_000)),
            (3, Fraction(2, 1_000)),
        ),
        (
            (1, Fraction(197, 200)),
            (2, Fraction(3, 200)),
        ),
        (
            (1, Fraction(393, 400)),
            (2, Fraction(3, 200)),
            (3, Fraction(1, 400)),
        ),
    )
    assert all(
        sum((probability for _, probability in law.rank_probabilities), Fraction())
        == 1
        for law in environment.laws
    )
    assert set(law.law_id for law in environment.laws).isdisjoint(
        law.law_id for law in old_environment.laws
    )
    assert (
        environment.environment_manifest_id
        != old_environment.manifest_id
    )
    assert environment.target_tapes_opened is False
    assert environment.target_observations_generated == 0
    assert environment.target_execution_allowed is False


def test_preregistration_draft_freezes_five_arms_and_fifteen_occurrences() -> None:
    preregistration = v075.freeze_v075_preregistration_draft_v1()
    templates = preregistration.occurrence_templates
    document = preregistration.to_document()

    assert v075.ARM_ORDER == (
        "SOURCE_CONSENSUS_PRIOR",
        "NO_PRIOR",
        "WRONG_CONSENSUS_PRIOR",
        "OOD_ABSTENTION",
        "MATCHED_DIRECT_GROUND",
    )
    assert len(templates) == v075.EXPECTED_OCCURRENCE_COUNT == 15
    assert tuple(template.occurrence_ordinal for template in templates) == tuple(
        range(15)
    )
    assert tuple(template.arm for template in templates) == v075.ARM_ORDER * 3
    assert len({template.template_id for template in templates}) == 15
    assert document["order"] == "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER"
    assert document["campaign_early_stop_allowed"] is False
    assert document["replacement_allowed"] is False
    assert document["maximum_attempts_for_future_authority_chain"] == 1
    assert document["old_target_tape_or_evidence_reuse_allowed"] is False
    assert document["confirmatory_execution_manifest_id"] is None
    assert document["anchor_commit_id"] is None
    assert document["target_execution_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["sample_efficiency_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_all_fresh_target_authority_ids_are_disjoint_from_v072() -> None:
    registry = v075.freeze_historical_identity_disposition_registry_v1()
    family = v075.freeze_v075_target_family_generation_v1()
    environment = v075.freeze_v075_environment_manifest_v1()
    rule = v075.freeze_v075_tape_derivation_rule_v1()
    preregistration = v075.freeze_v075_preregistration_draft_v1()
    manifest = v075.freeze_v075_manifest_draft_v1()
    namespace = v075.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("future-v075-anchor"),
        final_preregistration_id=_id("future-v075-final-preregistration"),
        observer_profile_id=_id("future-v075-observer-profile"),
    )

    new_ids = {
        registry.registry_id,
        family.generation_seed_id,
        family.generation_id,
        *(context.context_id for context in family.replicate_contexts),
        environment.environment_manifest_id,
        *(law.law_id for law in environment.laws),
        rule.rule_id,
        preregistration.preregistration_draft_id,
        *(item.template_id for item in preregistration.occurrence_templates),
        manifest.manifest_draft_id,
        namespace.target_tape_namespace_id,
    }
    historical_target_ids = (
        set(registry.historical_failure_record_ids)
        | set(registry.forbidden_v072_target_identity_ids)
        | set(registry.allowed_source_only_upstream_ids)
    )
    assert new_ids.isdisjoint(historical_target_ids)
    assert len(new_ids) == 29


def test_manifest_draft_is_nonfinal_and_nonauthorizing() -> None:
    manifest = v075.freeze_v075_manifest_draft_v1()
    document = manifest.to_document()

    assert manifest.required_component_roles == (
        v075.REQUIRED_PRODUCTION_COMPONENT_ROLES
    )
    assert manifest.blockers == v075.MANIFEST_DRAFT_BLOCKERS
    assert document["component_registry_id"] is None
    assert document["production_source_proposal_archive_id"] is None
    assert document["test_command_manifest_id"] is None
    assert document["runtime_dependency_lock_id"] is None
    assert document["final_preregistration_id_embedded"] is False
    assert document["finalization_ready"] is False
    assert document["remote_main_anchor_id"] is None
    assert document["target_execution_allowed"] is False


def test_target_tape_namespace_is_anchor_derived_but_nonauthorizing() -> None:
    first = v075.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("future-anchor-a"),
        final_preregistration_id=_id("future-final-prereg-a"),
        observer_profile_id=_id("future-observer-profile"),
    )
    repeated = v075.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("future-anchor-a"),
        final_preregistration_id=_id("future-final-prereg-a"),
        observer_profile_id=_id("future-observer-profile"),
    )
    changed_anchor = v075.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("future-anchor-b"),
        final_preregistration_id=_id("future-final-prereg-a"),
        observer_profile_id=_id("future-observer-profile"),
    )
    changed_preregistration = (
        v075.derive_v075_target_tape_namespace_identity_v1(
            remote_main_anchor_id=_id("future-anchor-a"),
            final_preregistration_id=_id("future-final-prereg-b"),
            observer_profile_id=_id("future-observer-profile"),
        )
    )

    assert first == repeated
    assert (
        first.target_tape_namespace_id
        == repeated.target_tape_namespace_id
    )
    assert (
        first.target_tape_namespace_id
        != changed_anchor.target_tape_namespace_id
    )
    assert (
        first.target_tape_namespace_id
        != changed_preregistration.target_tape_namespace_id
    )
    assert first.remote_main_anchor_semantically_verified is False
    assert first.observer_open_authority is False
    assert first.target_execution_allowed is False


def test_worker_pid_and_schedule_do_not_enter_tape_identity() -> None:
    rule = v075.freeze_v075_tape_derivation_rule_v1().to_document()
    namespace = v075.derive_v075_target_tape_namespace_identity_v1(
        remote_main_anchor_id=_id("future-anchor"),
        final_preregistration_id=_id("future-final-prereg"),
        observer_profile_id=_id("future-observer"),
    ).to_document()
    signature = inspect.signature(
        v075.derive_v075_target_tape_namespace_identity_v1
    )

    assert tuple(signature.parameters) == (
        "remote_main_anchor_id",
        "final_preregistration_id",
        "observer_profile_id",
    )
    assert rule["worker_count_enters_namespace"] is False
    assert rule["worker_pid_enters_namespace"] is False
    assert rule["launch_order_enters_namespace"] is False
    assert rule["completion_order_enters_namespace"] is False
    assert rule["caller_nonce_allowed"] is False
    assert namespace["worker_count_used_as_namespace_input"] is False
    assert namespace["worker_pid_used_as_namespace_input"] is False
    assert namespace["launch_order_used_as_namespace_input"] is False
    assert namespace["completion_order_used_as_namespace_input"] is False
    assert namespace["caller_nonce_used"] is False


@pytest.mark.parametrize(
    "old_identity",
    (
        "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26",
        "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474",
        "a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a",
        "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f",
        "16b383ff8fd9ce3ec52737c9e68c079f2e908be4f9abd07ac4c4b41c16a9c7be",
    ),
)
def test_old_identity_cannot_seed_a_fresh_target_namespace(
    old_identity: str,
) -> None:
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        v075.derive_v075_target_tape_namespace_identity_v1(
            remote_main_anchor_id=old_identity,
            final_preregistration_id=_id("future-final-prereg"),
            observer_profile_id=_id("future-observer"),
        )


def test_old_identity_injection_fails_in_preregistration_and_manifest() -> None:
    preregistration = v075.freeze_v075_preregistration_draft_v1()
    manifest = v075.freeze_v075_manifest_draft_v1()
    old_environment_id = (
        v072.frozen_heldout_environment_manifest_v1().manifest_id
    )

    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(
            preregistration,
            environment_manifest_id=old_environment_id,
        )
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(
            manifest,
            historical_disposition_registry_id=old_environment_id,
        )


def test_recursive_historical_target_material_rejection() -> None:
    old_anchor = (
        "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474"
    )
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        v075.assert_no_v072_target_identity_material_v1(
            {"nested": [{"artifact_id": old_anchor}]}
        )
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        v075.assert_no_v072_target_identity_material_v1(
            {"schema": "acfqp.v072_target_result.v1"}
        )
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        v075.assert_no_v072_target_identity_material_v1(
            {"v072_target_cache": []}
        )

    source_only = v075.ALLOWED_SOURCE_ONLY_UPSTREAM_IDS[0]
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        v075.assert_no_v072_target_identity_material_v1(
            {"upstream_archive_id": source_only}
        )
    v075.assert_no_v072_target_identity_material_v1(
        {"upstream_archive_id": source_only},
        allow_source_only_upstream_ids=True,
    )


def test_registered_objects_reject_semantic_tampering() -> None:
    family = v075.freeze_v075_target_family_generation_v1()
    context = family.replicate_contexts[0]
    environment = v075.freeze_v075_environment_manifest_v1()
    law = environment.laws[0]
    rule = v075.freeze_v075_tape_derivation_rule_v1()
    manifest = v075.freeze_v075_manifest_draft_v1()

    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(family, target_tapes_opened=True)
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(context, risk_tolerance=Fraction(1, 10))
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(law, rank_probabilities=((1, Fraction(1)),))
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(rule, worker_pid_enters_namespace=True)
    with pytest.raises(
        v075.V075FreshCampaignAuthorityInvariantViolation
    ):
        replace(
            manifest,
            blockers=manifest.blockers[:-1],
        )


def test_frozen_documents_are_deterministic_and_contain_no_target_access() -> None:
    first = (
        v075.freeze_v075_target_family_generation_v1().to_document(),
        v075.freeze_v075_environment_manifest_v1().to_document(),
        v075.freeze_v075_preregistration_draft_v1().to_document(),
        v075.freeze_v075_manifest_draft_v1().to_document(),
    )
    second = (
        v075.freeze_v075_target_family_generation_v1().to_document(),
        v075.freeze_v075_environment_manifest_v1().to_document(),
        v075.freeze_v075_preregistration_draft_v1().to_document(),
        v075.freeze_v075_manifest_draft_v1().to_document(),
    )
    assert first == second
    for document in first:
        v075.assert_no_v072_target_identity_material_v1(document)
        encoded = repr(document)
        assert "'target_execution_allowed': True" not in encoded
        assert "'target_tapes_opened': True" not in encoded
