from __future__ import annotations

from fractions import Fraction
import ast
import hashlib
import inspect

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
from acfqp import v075_public_campaign_authority_v1 as authority
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_learned_support_quotient_planners_v1 as support_fixture


def _source_transport(
    *,
    source_archive_id: str = proposal.SOURCE_ARCHIVE_ID,
    feature_schema_id: str = proposal.SOURCE_FEATURE_SCHEMA_ID,
) -> worker.V075SourcePriorTransportV1:
    entries = [
        {
            "applied_ordinal": ordinal,
            "feature_key": feature_key,
            "exact_mean_midrank": {
                "numerator": midrank.numerator,
                "denominator": midrank.denominator,
            },
            "disposition": "APPLIED",
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
        }
        for ordinal, (feature_key, midrank) in enumerate(
            proposal.REGISTERED_APPLIED_SOURCE_MIDRANKS
        )
    ]
    catalogue = {
        "schema": "acfqp.v075_source_prior_catalogue.v1",
        "catalogue_id": hashlib.sha256(
            canonical_json_bytes(
                {
                    "feature_schema_id": feature_schema_id,
                    "entries": entries,
                }
            )
        ).hexdigest(),
        "source_feature_schema_id": feature_schema_id,
        "registered_applied_feature_keys": list(
            proposal.REGISTERED_APPLIED_SOURCE_KEYS
        ),
        "entries": entries,
    }
    adapter_payload = {
        "schema": "acfqp.v075_source_prior_adapter.v1",
        "schema_version": "1.0.0",
        "profile_key": worker.SOURCE_PRIOR_PROFILE_KEY,
        "source_archive_id": source_archive_id,
        "source_archive_verification_id": (
            proposal.SOURCE_ARCHIVE_VERIFICATION_ID
        ),
        "registered_applied_feature_keys": list(
            proposal.REGISTERED_APPLIED_SOURCE_KEYS
        ),
        "source_only": True,
        "proposal_only": True,
        "may_certify": False,
        "source_work_reference_only": True,
        "source_work_embedded": False,
    }
    adapter_id = hashlib.sha256(
        worker.SOURCE_PRIOR_ADAPTER_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(adapter_payload)
    ).hexdigest()
    adapter = {
        **adapter_payload,
        "catalogue": catalogue,
        "adapter_id": adapter_id,
    }
    adapter_bytes = canonical_json_bytes(adapter)
    verification_payload = {
        "schema": "acfqp.v075_source_prior_adapter_verification.v1",
        "schema_version": "1.0.0",
        "profile_key": worker.SOURCE_PRIOR_PROFILE_KEY,
        "adapter_id": adapter_id,
        "recomputed_adapter_id": adapter_id,
        "catalogue_id": catalogue["catalogue_id"],
        "adapter_bytes_sha256": hashlib.sha256(adapter_bytes).hexdigest(),
        "valid": True,
    }
    verification_id = hashlib.sha256(
        worker.SOURCE_PRIOR_VERIFICATION_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(verification_payload)
    ).hexdigest()
    verification = {
        **verification_payload,
        "verification_id": verification_id,
    }
    return worker.V075SourcePriorTransportV1(
        adapter_bytes,
        canonical_json_bytes(verification),
        adapter_id,
        verification_id,
    )


def test_exact_source_feature_schema_and_three_registered_keys() -> None:
    features = (
        proposal.V075PortableAcquisitionCoreFeatureReplayV2(
            "CONTINUATION",
            "CONTINUATION_CONCRETIZER_COMPONENT",
            "2",
            "2",
            ("SUCCESS_TERMINAL",),
        ),
        proposal.V075PortableAcquisitionCoreFeatureReplayV2(
            "CONTINUATION",
            "CONTINUATION_CONCRETIZER_COMPONENT",
            "2",
            "2",
            ("FAILURE", "SUCCESS_TERMINAL"),
        ),
        proposal.V075PortableAcquisitionCoreFeatureReplayV2(
            "ROOT",
            "ROOT_CONCRETIZER_COMPONENT",
            "2",
            "2",
            ("ACTIVE_STATE",),
        ),
    )
    assert proposal.SOURCE_FEATURE_SCHEMA_ID == (
        "6c5867ab74182b98faf776ec6a544799c745b5bf6c7cd9943733da5fe96951de"
    )
    assert tuple(item.feature_key for item in features) == (
        proposal.REGISTERED_APPLIED_SOURCE_KEYS
    )
    forbidden = {
        "context_id",
        "state_id",
        "row_id",
        "vertex_count",
        "success_count",
        "draw_count",
        "probability",
    }
    for item in features:
        document = item.to_document()
        assert forbidden.isdisjoint(document)
        assert document["ids_stripped"] is True
        assert document["exact_probabilities_absent"] is True
        assert document["exact_counts_absent"] is True


def test_source_wrong_no_prior_and_ood_have_frozen_semantics() -> None:
    source = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        source_transport=_source_transport(),
    )
    wrong = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
    )
    no_prior = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    ood = proposal.freeze_v075_source_proposal_view_v1(
        arm=worker.V075WorkerArmV1.OOD_ABSTENTION,
    )
    for feature_key, q in proposal.REGISTERED_APPLIED_SOURCE_MIDRANKS:
        assert proposal._prior_fields(
            source_view=source,
            feature_key=feature_key,
        ) == (
            proposal.V075PriorDispositionV1.SOURCE_APPLIED,
            q,
            q,
            Fraction(1, 2) + Fraction(3, 2) * q,
        )
        assert proposal._prior_fields(
            source_view=wrong,
            feature_key=feature_key,
        ) == (
            proposal.V075PriorDispositionV1.WRONG_REVERSED_APPLIED,
            q,
            1 - q,
            Fraction(1, 2) + Fraction(3, 2) * (1 - q),
        )
    unmatched = hashlib.sha256(b"unmatched-portable-feature").hexdigest()
    assert proposal._prior_fields(
        source_view=source,
        feature_key=unmatched,
    )[2:] == (Fraction(1), Fraction(1))
    assert proposal._prior_fields(
        source_view=no_prior,
        feature_key=proposal.REGISTERED_APPLIED_SOURCE_KEYS[0],
    )[2:] == (Fraction(1), Fraction(1))
    assert proposal._prior_fields(
        source_view=ood,
        feature_key=proposal.REGISTERED_APPLIED_SOURCE_KEYS[0],
    )[2:] == (Fraction(1), Fraction(1))


def test_source_archive_and_feature_schema_transplants_are_rejected() -> None:
    with pytest.raises(
        proposal.V075AdaptiveAcquisitionInvariantViolation,
        match="transplanted or changed feature schema",
    ):
        proposal.freeze_v075_source_proposal_view_v1(
            arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_transport=_source_transport(
                source_archive_id=hashlib.sha256(
                    b"transplanted-source-archive"
                ).hexdigest(),
            ),
        )
    with pytest.raises(
        proposal.V075AdaptiveAcquisitionInvariantViolation,
        match="transplanted or changed feature schema",
    ):
        proposal.freeze_v075_source_proposal_view_v1(
            arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_transport=_source_transport(
                feature_schema_id=hashlib.sha256(
                    b"wrong-feature-schema"
                ).hexdigest(),
            ),
        )


def test_initial_root_schedule_is_complete_and_cold_draws_are_fixed() -> None:
    caps = worker.V075WorkerCapProfileV1()
    for context in (
        authority.freeze_v075_public_family_generation_v1()
        .replicate_contexts
    ):
        schedule = proposal.freeze_v075_initial_root_acquisition_schedule_v1(
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
        )
        assert len(schedule.intents) == 4
        assert schedule.online_draw_upper == 2 * (
            caps.initial_discovery_draws_per_row
            + caps.initial_validation_draws_per_row
        )
        assert {
            item.accepted_draw_cap
            for item in schedule.intents
            if item.kind is proposal.V075InitialIntentKindV1.ROOT_VALIDATION
        } == {proposal.INITIAL_VALIDATION_ACCEPTED_DRAW_CAP}


def test_target_interval_changes_cannot_change_portable_feature() -> None:
    zero = support_fixture._graph(child_other_probability=Fraction(0))
    nonzero = support_fixture._graph(
        child_other_probability=Fraction(1, 10)
    )
    zero_plan = support_fixture.planners.plan_v075_exact_h2_abstract_v1(zero)
    nonzero_plan = support_fixture.planners.plan_v075_exact_h2_abstract_v1(
        nonzero
    )

    def continuation_feature(graph_value, plan_value):
        assert plan_value.policy is not None
        decision = next(
            item
            for item in plan_value.policy.decisions
            if item.remaining_horizon == 1
        )
        choice = decision.state_choices[0]
        node = next(
            item
            for item in graph_value.nodes
            if item.state_id == choice.state_id
        )
        row = next(
            item for item in node.rows if item.row_id in choice.row_ids
        )
        return proposal.replay_v075_target_portable_feature_v2(
            node=node,
            row=row,
            choice=choice,
        )

    assert continuation_feature(zero, zero_plan) == continuation_feature(
        nonzero,
        nonzero_plan,
    )


def test_proposal_authority_has_no_direct_target_or_private_access() -> None:
    tree = ast.parse(inspect.getsource(proposal))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        token in name
        for name in imported
        for token in (
            "private_observer",
            "private_environment",
            "kernel",
            "exact_lift",
        )
    )
