from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as source_independent_v2,
)
from acfqp import v072_verified_source_archive_component_v1 as source_component
from acfqp import (
    v072_portable_feature_consensus_authority_v1
    as consensus_authority,
)
from acfqp import public_novel_child_cardinality_authority_v2 as child_v2
from acfqp import (
    public_novel_child_cardinality_independent_verifier_v2
    as child_independent_v2,
)
from acfqp import (
    v072_public_catalogue_novel_child_component_v1
    as child_component,
)
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)
from tests.test_public_novel_child_cardinality_authority_v2 import _valid


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _source_component(
    fixture,
) -> source_component.V072VerifiedSourceArchiveComponentV1:
    source_campaign, source_verification, source_archive = fixture
    assert source_archive.source_campaign_id == source_campaign.campaign_id
    production = archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2(
        source_archive.archive_id,
        source_archive.archive_id,
        source_campaign.campaign_id,
        source_verification.verification_id,
        len(source_archive.adjacent_pairs),
        len(source_archive.trials),
        len(source_archive.consensus),
    )
    digest = hashlib.sha256(
        source_component.ARCHIVE_DOCUMENT_DIGEST_TAG
        + canonical_json_bytes(source_archive.to_document())
    ).hexdigest()
    independent = (
        source_independent_v2
        .IndependentSourceAcquisitionArchiveVerificationV2(
            source_archive.archive_id,
            source_archive.archive_id,
            digest,
            source_campaign.campaign_id,
            source_verification.verification_id,
            len(source_archive.adjacent_pairs),
            len(source_archive.trials),
            len(source_archive.consensus),
        )
    )
    return source_component.bind_v072_verified_source_archive_component_v1(
        archive=source_archive,
        production_verification=production,
        independent_attestation=independent,
    )


def test_source_component_strictly_binds_three_exact_artifacts(
    miniature_source_archive,
) -> None:
    component = _source_component(miniature_source_archive)
    document = component.to_document()
    assert document["archive_id"] == component.archive.archive_id
    assert document["production_verification_id"] == (
        component.production_verification.verification_id
    )
    assert document[
        "independent_archive_transform_attestation_id"
    ] == component.independent_attestation.verification_id
    assert document["independent_archive_transform_verified"] is True
    assert document["independent_source_campaign_verifier_claimed"] is False
    assert document["source_campaign_input_accepted"] is False
    assert document["target_observation_input_accepted"] is False
    assert document["environment_law_queries"] == 0


def test_source_component_rejects_stale_identity_or_document_digest(
    miniature_source_archive,
) -> None:
    component = _source_component(miniature_source_archive)
    stale_production = replace(
        component.production_verification,
        source_campaign_id=_id("stale-source-campaign"),
    )
    with pytest.raises(
        source_component
        .V072VerifiedSourceArchiveComponentInvariantViolation,
    ):
        source_component.bind_v072_verified_source_archive_component_v1(
            archive=component.archive,
            production_verification=stale_production,
            independent_attestation=component.independent_attestation,
        )

    stale_independent = replace(
        component.independent_attestation,
        archive_document_digest=_id("stale-archive-document"),
    )
    with pytest.raises(
        source_component
        .V072VerifiedSourceArchiveComponentInvariantViolation,
    ):
        source_component.bind_v072_verified_source_archive_component_v1(
            archive=component.archive,
            production_verification=component.production_verification,
            independent_attestation=stale_independent,
        )


def test_source_binding_and_consensus_never_rerun_upstream_verifiers(
    miniature_source_archive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    component = _source_component(miniature_source_archive)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("upstream archive builder/verifier was called")

    monkeypatch.setattr(
        archive_v2,
        "freeze_verified_source_acquisition_archive_v2",
        forbidden,
    )
    monkeypatch.setattr(
        archive_v2,
        "verify_verified_source_acquisition_archive_v2",
        forbidden,
    )
    monkeypatch.setattr(
        archive_v2,
        "_derive_nonrectangular_consensus",
        forbidden,
    )
    monkeypatch.setattr(
        source_independent_v2,
        "verify_source_acquisition_archive_independently_v2",
        forbidden,
    )
    rebound = (
        source_component.bind_v072_verified_source_archive_component_v1(
            archive=component.archive,
            production_verification=component.production_verification,
            independent_attestation=component.independent_attestation,
        )
    )
    replayed = (
        consensus_authority
        .replay_portable_feature_consensus_authority_v1(rebound)
    )
    assert replayed.context_feature_aggregates == (
        component.archive.context_feature_aggregates
    )
    assert replayed.consensus == component.archive.consensus
    assert replayed.to_document()["caller_supplied_gain"] is False
    assert replayed.to_document()["caller_supplied_rank"] is False


def test_consensus_public_constructor_has_no_rank_or_gain_input(
    miniature_source_archive,
) -> None:
    component = _source_component(miniature_source_archive)
    signature = inspect.signature(
        consensus_authority
        .replay_portable_feature_consensus_authority_v1
    )
    assert tuple(signature.parameters) == ("source_archive_component",)
    constructor_signature = inspect.signature(
        consensus_authority.V072PortableFeatureConsensusAuthorityV1
    )
    assert tuple(constructor_signature.parameters) == (
        "source_archive_component",
    )
    replayed = (
        consensus_authority
        .replay_portable_feature_consensus_authority_v1(component)
    )
    unknown_feature = _id("unknown-portable-feature")
    assert replayed.multiplier_for(unknown_feature) == (
        archive_v2.NEUTRAL_PRIOR_MULTIPLIER
    )
    assert replayed.disposition_for(unknown_feature) is None


def _verified_child_pair():
    context, parent, closure, gain, claimed = _valid(
        label="v072-manifest-novel-child-component"
    )
    attestation = (
        child_independent_v2
        .verify_public_novel_child_cardinality_authority_v2(
            claimed=claimed,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=gain,
        )
    )
    return claimed, attestation


def test_public_catalogue_component_binds_exact_independent_counts() -> None:
    claimed, attestation = _verified_child_pair()
    component = (
        child_component
        .bind_v072_public_catalogue_novel_child_component_v1(
            cardinality_authority=claimed,
            independent_attestation=attestation,
        )
    )
    document = component.to_document()
    assert document["new_child_row_count"] == len(
        claimed.rows_to_acquire
    )
    assert document["exact_round_draw_upper"] == (
        claimed.exact_round_draw_upper
    )
    assert document["full_public_catalogue_row_list_bound"] is True
    assert document["independently_replayed"] is True
    assert document["observer_input_accepted"] is False
    assert document["environment_law_input_accepted"] is False
    assert document["outcome_input_accepted"] is False


def test_public_catalogue_component_does_not_replay_or_open_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claimed, attestation = _verified_child_pair()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("upstream cardinality authority was called")

    monkeypatch.setattr(
        child_v2,
        "derive_public_novel_child_cardinality_evidence_v2",
        forbidden,
    )
    monkeypatch.setattr(
        child_v2,
        "authorize_public_novel_child_rows_v2",
        forbidden,
    )
    monkeypatch.setattr(
        child_independent_v2,
        "verify_public_novel_child_cardinality_authority_v2",
        forbidden,
    )
    component = (
        child_component
        .bind_v072_public_catalogue_novel_child_component_v1(
            cardinality_authority=claimed,
            independent_attestation=attestation,
        )
    )
    assert component.rows_to_acquire == claimed.rows_to_acquire

    signature = inspect.signature(
        child_component
        .bind_v072_public_catalogue_novel_child_component_v1
    )
    assert tuple(signature.parameters) == (
        "cardinality_authority",
        "independent_attestation",
    )


def test_public_catalogue_component_rejects_mismatched_attestation() -> None:
    claimed, attestation = _verified_child_pair()
    stale = replace(
        attestation,
        exact_round_draw_upper=attestation.exact_round_draw_upper + 1,
    )
    with pytest.raises(
        child_component
        .V072PublicCatalogueNovelChildComponentInvariantViolation,
    ):
        (
            child_component
            .bind_v072_public_catalogue_novel_child_component_v1(
                cardinality_authority=claimed,
                independent_attestation=stale,
            )
        )

    foreign = replace(
        attestation,
        parent_artifact_id=_id("foreign-parent-artifact"),
    )
    with pytest.raises(
        child_component
        .V072PublicCatalogueNovelChildComponentInvariantViolation,
    ):
        (
            child_component
            .bind_v072_public_catalogue_novel_child_component_v1(
                cardinality_authority=claimed,
                independent_attestation=foreign,
            )
        )
