from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
import acfqp.v075_frozen_source_proposal_archive_v1 as archive_v1
import acfqp.v075_source_offline_work_materializer_v1 as work_v1
import acfqp.v075_source_prior_adapter_v1 as v075
from tests.test_v075_source_offline_work_materializer_v1 import (
    exact_source_replay,
)
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-source-prior-adapter-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def source_authorities() -> tuple[
    archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_v1.V075FrozenSourceProposalArchiveVerificationV1,
]:
    source_archive = (
        archive_v1.compile_v075_frozen_source_proposal_archive_v1(
            REPOSITORY_ROOT
        )
    )
    verification = (
        archive_v1
        .verify_v075_frozen_source_proposal_archive_independently_v1(
            repository_root=REPOSITORY_ROOT,
            claimed=source_archive,
        )
    )
    return source_archive, verification


@pytest.fixture
def foreign_work(exact_source_replay) -> tuple[
    work_v1.V075SourceOfflineWorkMaterializationV1,
    work_v1.V075SourceOfflineWorkMaterializationVerificationV1,
]:
    materialization = (
        work_v1.materialize_v075_source_offline_work_v1(
            exact_source_replay
        )
    )
    verification = (
        work_v1.verify_v075_source_offline_work_independently_v1(
            replay=exact_source_replay,
            claimed=materialization,
        )
    )
    return materialization, verification


def _catalogue(
    source_authorities,
) -> v075.V075SourcePriorCatalogueV1:
    return v075.compile_v075_source_prior_catalogue_v1(
        *source_authorities
    )


def _forged_unbound_adapter(
    source_authorities,
) -> v075.V075SourcePriorAdapterV1:
    """Adversarial transport fixture; never a selector authority."""

    return v075.V075SourcePriorAdapterV1(
        v075._ISSUER,
        _catalogue(source_authorities),
        _id("schema-only-work"),
        _id("schema-only-work-verification"),
        _id("schema-only-counters"),
    )


def test_domains_are_new_unique_and_source_scoped() -> None:
    assert len(v075.DOMAIN_TAGS) == len(set(v075.DOMAIN_TAGS.values()))
    assert all(
        domain.startswith("acfqp:v075-source-prior")
        for domain in v075.DOMAIN_TAGS.values()
    )


def test_adapter_has_no_direct_target_observer_hidden_law_or_v072_import() -> None:
    tree = ast.parse(inspect.getsource(v075))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(
        fragment in name.lower()
        for name in imported
        for fragment in ("target", "observer", "hidden", "v072")
    )


def test_catalogue_compiles_exact_three_applied_source_consensuses(
    source_authorities,
) -> None:
    source_archive, archive_verification = source_authorities
    catalogue = _catalogue(source_authorities)

    assert catalogue.source_recipe_id == source_archive.source_recipe_id
    assert catalogue.source_archive_id == source_archive.archive_id
    assert (
        catalogue.source_archive_verification_id
        == archive_verification.verification_id
    )
    assert (
        catalogue.source_offline_work_reference_id
        == source_archive.offline_work.work_reference_id
    )
    assert tuple(item.feature_key for item in catalogue.entries) == (
        v075.REGISTERED_APPLIED_FEATURE_KEYS
    )
    assert tuple(item.consensus_id for item in catalogue.entries) == (
        "7dcd4446362466618ee5e063a47e650c6c9d02668e2ebe4bdb645ec5932f934e",
        "a5dba2f67f72c6d923c8e0fc48959bf3f5d8a51b1348d8e809d065a433ccdbc4",
        "afa322421e2956f33c6912182eb4124b800c0501e3ac93aa481bfb4435e2e846",
    )
    assert tuple(
        item.exact_mean_midrank for item in catalogue.entries
    ) == (Fraction(1, 6), Fraction(19, 36), Fraction(1))


def test_catalogue_is_not_selector_authority_until_work_is_bound(
    source_authorities,
) -> None:
    document = _catalogue(source_authorities).to_document()

    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["may_certify"] is False
    assert document["work_binding_required"] is True
    assert document["selector_use_authorized"] is False
    assert document["target_execution_allowed"] is False
    assert document["historical_recipe_reads"] == 0


def test_catalogue_strict_canonical_round_trip(
    source_authorities,
) -> None:
    catalogue = _catalogue(source_authorities)
    loaded = v075.load_v075_source_prior_catalogue_v1(
        catalogue.canonical_bytes,
        expected_catalogue_id=catalogue.catalogue_id,
        expected_source_archive_id=catalogue.source_archive_id,
        expected_source_archive_verification_id=(
            catalogue.source_archive_verification_id
        ),
    )
    assert loaded == catalogue


def test_applied_lookup_and_unknown_or_nonapplied_fail_closed(
    source_authorities,
) -> None:
    catalogue = _catalogue(source_authorities)

    for feature_key, expected in zip(
        v075.REGISTERED_APPLIED_FEATURE_KEYS,
        (Fraction(1, 6), Fraction(19, 36), Fraction(1)),
        strict=True,
    ):
        assert (
            catalogue.require_applied_feature(
                feature_key
            ).exact_mean_midrank
            == expected
        )
    with pytest.raises(
        v075.V075SourcePriorAdapterViolation,
        match="not APPLIED",
    ):
        catalogue.require_applied_feature(
            v075.REGISTERED_NONAPPLIED_FEATURE_KEYS[0]
        )
    with pytest.raises(
        v075.V075SourcePriorAdapterViolation,
        match="unknown",
    ):
        catalogue.require_applied_feature(_id("unknown-feature"))


def test_missing_applied_feature_fails_closed(
    source_authorities,
) -> None:
    catalogue = _catalogue(source_authorities)
    document = json.loads(catalogue.canonical_bytes)
    document["entries"].pop()
    document["entry_ids"].pop()

    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.load_v075_source_prior_catalogue_v1(
            canonical_json_bytes(document),
            expected_catalogue_id=catalogue.catalogue_id,
            expected_source_archive_id=catalogue.source_archive_id,
            expected_source_archive_verification_id=(
                catalogue.source_archive_verification_id
            ),
        )


def test_midrank_tamper_even_if_reconstructed_is_rejected(
    source_authorities,
) -> None:
    catalogue = _catalogue(source_authorities)
    entry = catalogue.entries[0]
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        replace(entry, exact_mean_midrank=Fraction(1, 5))

    document = json.loads(catalogue.canonical_bytes)
    document["entries"][0]["exact_mean_midrank"] = {
        "numerator": 1,
        "denominator": 5,
    }
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.load_v075_source_prior_catalogue_v1(
            canonical_json_bytes(document),
            expected_catalogue_id=catalogue.catalogue_id,
            expected_source_archive_id=catalogue.source_archive_id,
            expected_source_archive_verification_id=(
                catalogue.source_archive_verification_id
            ),
        )


def test_archive_or_archive_attestation_transplant_fails_closed(
    source_authorities,
) -> None:
    source_archive, verification = source_authorities
    changed_archive = replace(
        source_archive,
        source_recipe_bytes_sha256=_id("changed-recipe-bytes"),
    )
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.compile_v075_source_prior_catalogue_v1(
            changed_archive,
            verification,
        )

    changed_verification = replace(
        verification,
        archive_id=_id("foreign-archive"),
        recomputed_archive_id=_id("foreign-archive"),
    )
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.compile_v075_source_prior_catalogue_v1(
            source_archive,
            changed_verification,
        )


def test_coherently_resigned_archive_metadata_still_fails_registry(
    source_authorities,
) -> None:
    source_archive, _verification = source_authorities
    changed_archive = replace(
        source_archive,
        feature_schema_id=_id("foreign-feature-schema"),
    )
    changed_verification = (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1(
            changed_archive.source_recipe_id,
            changed_archive.archive_id,
            changed_archive.archive_id,
            hashlib.sha256(changed_archive.canonical_bytes).hexdigest(),
            changed_archive.offline_work.work_reference_id,
            tuple(
                item.summary_id
                for item in changed_archive.consensus_summaries
            ),
            tuple(
                item.lookup_id for item in changed_archive.applied_lookup
            ),
        )
    )
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.compile_v075_source_prior_catalogue_v1(
            changed_archive,
            changed_verification,
        )


def test_foreign_work_transplant_cannot_mint_adapter(
    source_authorities,
    foreign_work,
) -> None:
    with pytest.raises(
        v075.V075SourcePriorAdapterViolation,
        match="transplanted",
    ):
        v075.bind_v075_source_prior_adapter_v1(
            *source_authorities,
            *foreign_work,
        )


def test_work_attestation_tamper_fails_closed(
    source_authorities,
    foreign_work,
) -> None:
    materialization, verification = foreign_work
    changed = replace(
        verification,
        materialization_bytes_sha256=_id("wrong-work-bytes"),
    )
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.bind_v075_source_prior_adapter_v1(
            *source_authorities,
            materialization,
            changed,
        )


def test_binding_api_accepts_no_feature_map_target_or_counter_values() -> None:
    signature = inspect.signature(v075.bind_v075_source_prior_adapter_v1)
    assert tuple(signature.parameters) == (
        "source_archive",
        "archive_verification",
        "source_work",
        "work_verification",
    )
    assert not any(
        fragment in name
        for name in signature.parameters
        for fragment in ("target", "feature_map", "counter_values")
    )


def test_adapter_build_never_reads_recipe_or_reconstructs_archive(
    source_authorities,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("historical recipe/archive reconstruction called")

    monkeypatch.setattr(
        archive_v1,
        "compile_v075_frozen_source_proposal_archive_v1",
        forbidden,
    )
    monkeypatch.setattr(
        archive_v1,
        "verify_v075_frozen_source_proposal_archive_independently_v1",
        forbidden,
    )
    monkeypatch.setattr(
        archive_v1.v072_recipe,
        "load_source_reconstruction_recipe_v1",
        forbidden,
    )

    catalogue = v075.compile_v075_source_prior_catalogue_v1(
        *source_authorities
    )
    assert catalogue.to_document()["historical_recipe_reads"] == 0


def test_adapter_transport_contains_only_work_references_not_values_or_zero(
    source_authorities,
) -> None:
    # A forged object can still exercise the immutable schema shape, but the
    # public loader below must never promote it into selector authority.
    adapter = _forged_unbound_adapter(source_authorities)
    document = adapter.to_document()

    assert document["source_work_reference_only"] is True
    assert document["source_work_embedded"] is False
    assert document["source_work_zero_claimed"] is False
    assert document["source_work_charged_again"] is False
    assert "campaign_counters" not in document
    assert "offline_sample_draw_count" not in document
    assert "offline_random_word_call_count" not in document
    assert "offline_rejection_count" not in document


def test_forged_work_ids_cannot_be_loaded_as_selector_authority(
    source_authorities,
    foreign_work,
) -> None:
    adapter = _forged_unbound_adapter(source_authorities)
    source_archive, archive_verification = source_authorities
    source_work, work_verification = foreign_work

    with pytest.raises(
        v075.V075SourcePriorAdapterViolation,
        match="transplanted",
    ):
        v075.load_v075_source_prior_adapter_v1(
            adapter.canonical_bytes,
            source_archive=source_archive,
            archive_verification=archive_verification,
            source_work=source_work,
            work_verification=work_verification,
        )


def test_adapter_loader_accepts_authorities_not_caller_expected_ids() -> None:
    signature = inspect.signature(v075.load_v075_source_prior_adapter_v1)
    assert tuple(signature.parameters) == (
        "raw",
        "source_archive",
        "archive_verification",
        "source_work",
        "work_verification",
    )
    assert not any(
        name.startswith("expected_") for name in signature.parameters
    )


def test_exact_snapshot_requirement_and_production_blocker_are_frozen(
    source_authorities,
) -> None:
    status = v075.freeze_v075_source_prior_production_status_v1(
        *source_authorities
    )
    document = status.to_document()

    assert document["required_source_replay_commit"] == (
        "63cc0f5f78f64b7845319d1c1a5856212e3b8097"
    )
    assert document["required_source_replay_tree"] == (
        "8c88ef5e2747267a309834d155136c40ba926b61"
    )
    assert document["clean_detached_worktree_required"] is True
    assert (
        document["replay_and_materialization_same_process_required"]
        is True
    )
    assert document["current_checkout_replay_allowed"] is False
    assert document["replay_allowed_only_at_required_snapshot"] is True
    assert document["source_replay_snapshot_status"] == "NOT_RUN"
    assert document["source_replay_snapshot_attestation_id"] is None
    assert document["production_adapter_status"] == (
        v075.PRODUCTION_ADAPTER_STATUS
    )
    assert document["source_work_materialization_id"] is None
    assert document["source_work_verification_id"] is None
    assert document["adapter_id"] is None
    assert document["selector_use_authorized"] is False
    assert document["target_execution_allowed"] is False


def test_catalogue_snapshot_provenance_is_requirement_not_false_attestation(
    source_authorities,
) -> None:
    document = _catalogue(source_authorities).to_document()
    assert document["required_source_replay_commit"] == (
        v075.REQUIRED_SOURCE_REPLAY_COMMIT
    )
    assert document["required_source_replay_tree"] == (
        v075.REQUIRED_SOURCE_REPLAY_TREE
    )
    assert document["clean_detached_worktree_required"] is True
    assert (
        document["replay_and_materialization_same_process_required"]
        is True
    )
    assert "source_replay_snapshot_attestation_id" not in document


def test_noncanonical_catalogue_bytes_fail_closed(
    source_authorities,
) -> None:
    catalogue = _catalogue(source_authorities)
    with pytest.raises(v075.V075SourcePriorAdapterViolation):
        v075.load_v075_source_prior_catalogue_v1(
            catalogue.canonical_bytes + b"\n",
            expected_catalogue_id=catalogue.catalogue_id,
            expected_source_archive_id=catalogue.source_archive_id,
            expected_source_archive_verification_id=(
                catalogue.source_archive_verification_id
            ),
        )
