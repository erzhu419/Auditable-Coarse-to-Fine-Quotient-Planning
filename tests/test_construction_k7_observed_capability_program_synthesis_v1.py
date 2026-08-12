from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v3 as synthesis_v3
from acfqp import construction_k7_observed_capability_program_synthesis_v1 as subject
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _occurrence(label: str) -> str:
    return hashlib.sha256(f"observed-program:{label}".encode()).hexdigest()


@pytest.fixture(scope="module")
def decisions():
    return {
        key: subject.propose_observed_capability_program_v1(
            observer.public_context_by_key_v1(key)
        )
        for key in (
            "opaque_graph_w5_v0",
            "opaque_graph_k6_v0",
            "opaque_graph_k6_minus_edge_v0",
        )
    }


def test_domains_grammar_and_public_surface_are_frozen() -> None:
    grammar = subject.freeze_observed_capability_program_grammar_v1()
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert synthesis_v3.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert grammar.primitives == subject.FEATURES
    assert grammar.operators == ("EQUALS", "AND")
    document = grammar.to_document()
    assert document["literal_values_must_come_from_positive_observations"] is True
    assert document["automatic_primitive_or_operator_invention_claimed"] is False
    assert set(subject.__all__) == {
        "CONSTRUCTOR_EXAMPLES",
        "ConstructionK7ObservedCapabilityProgramSynthesisV1Error",
        "EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR",
        "FEATURES",
        "LOCAL_DOMAINS",
        "ObservedCapabilityProgramCandidateV1",
        "ObservedCapabilityProgramCorpusV1",
        "ObservedCapabilityProgramDecisionV1",
        "ObservedCapabilityProgramGrammarV1",
        "ObservedCapabilityProgramProposalV1",
        "freeze_observed_capability_program_corpus_v1",
        "freeze_observed_capability_program_grammar_v1",
        "propose_observed_capability_program_v1",
        "synthesize_observed_capability_program_v1",
        "verify_observed_capability_program_v1",
    }


def test_complete_subset_search_synthesizes_values_from_observations(decisions) -> None:
    w5 = decisions["opaque_graph_w5_v0"]
    k6 = decisions["opaque_graph_k6_v0"]
    for decision, constructor in (
        (w5, "W5_CHECKPOINT_OVERLAY_V1"),
        (k6, "K6_CHECKPOINT_OVERLAY_V1"),
    ):
        proposal = next(
            row for row in decision.proposals if row.constructor_key == constructor
        )
        assert len(proposal.candidates) == subject.EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR
        assert sum(row.accepted for row in proposal.candidates) == 1
        assert tuple(name for name, _value in proposal.selected_atoms) == subject.FEATURES
        assert dict(proposal.selected_atoms) == dict(
            (name, getattr(decision.signature, name)) for name in subject.FEATURES
        )
        document = proposal.to_document()
        assert document["literal_values_observation_derived"] is True
        assert document["fixed_human_signature_value_table_used"] is False


def test_program_evaluation_never_reads_context_key(decisions) -> None:
    w5 = decisions["opaque_graph_w5_v0"]
    assert w5.selected_constructor_key == "W5_CHECKPOINT_OVERLAY_V1"
    source = inspect.getsource(subject._program_matches)  # noqa: SLF001
    assert "context_key" not in source
    document = w5.to_document()
    assert document["context_key_used_as_program_input"] is False
    assert document["fixed_human_signature_value_table_authoritative"] is False


def test_nearby_structure_is_no_program_and_no_ground_authority(decisions) -> None:
    decision = decisions["opaque_graph_k6_minus_edge_v0"]
    subject.verify_observed_capability_program_v1(
        observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0"),
        decision,
    )
    assert decision.outcome == "NO_SOUND_PROGRAM"
    assert decision.selected_constructor_key is None
    document = decision.to_document()
    assert document["nearby_program_transfer_allowed"] is False
    assert document["ground_access_authorized_here"] is False
    assert document["broad_graph_generalization_claimed"] is False


def test_single_feature_controls_force_every_atom(decisions) -> None:
    for decision in decisions.values():
        for proposal in decision.proposals:
            selected = next(
                row for row in proposal.candidates if row.candidate_id == proposal.selected_candidate_id
            )
            controls = [
                row for row in selected.evaluation_rows if row[0].startswith("SINGLE_FEATURE_COUNTERFACTUAL:")
            ]
            assert len(controls) == len(subject.FEATURES)
            assert all(expected is False and observed is False for _key, expected, observed in controls)
            assert all(
                not row.accepted
                for row in proposal.candidates
                if len(row.atoms) < len(subject.FEATURES)
            )


def test_candidate_or_corpus_tamper_is_rejected(decisions) -> None:
    decision = decisions["opaque_graph_w5_v0"]
    proposal = decision.proposals[0]
    candidate = proposal.candidates[-1]
    with pytest.raises(subject.ConstructionK7ObservedCapabilityProgramSynthesisV1Error):
        object.__setattr__(candidate, "accepted", False)
        subject.verify_observed_capability_program_v1(
            observer.public_context_by_key_v1("opaque_graph_w5_v0"), decision
        )
    object.__setattr__(candidate, "accepted", True)
    subject.verify_observed_capability_program_v1(
        observer.public_context_by_key_v1("opaque_graph_w5_v0"), decision
    )


def test_v3_uses_program_authority_and_preserves_claim_boundary() -> None:
    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    result = synthesis_v3.run_observation_driven_world_model_synthesis_v3(
        catalogue,
        context,
        logical_occurrence_id=_occurrence("w5"),
        occurrence_ordinal=1,
        selected_reuse_result_bytes=None,
    )
    synthesis_v3.verify_observation_driven_world_model_synthesis_v3(context, result)
    document = result.to_document()
    assert document["constructor_selection_authority"] == (
        "OBSERVATION_DERIVED_PROGRAM_PROPOSAL_V1"
    )
    assert document["literal_values_observation_derived"] is True
    assert document["fixed_human_signature_value_table_authoritative"] is False
    assert document["human_registered_primitive_and_operator_vocabulary"] is True
    assert document["automatic_primitive_or_operator_invention_claimed"] is False
    assert result.executor_result.executor_result.promotion is not None

    reuse_document = result.executor_result.executor_result.reuse_result_document
    assert reuse_document is not None
    reuse_bytes = canonical_json_bytes(reuse_document)
    entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1("W5", reuse_bytes)
    reused = synthesis_v3.run_observation_driven_world_model_synthesis_v3(
        catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1((entry,)),
        context,
        logical_occurrence_id=_occurrence("w5-reuse"),
        occurrence_ordinal=2,
        selected_reuse_result_bytes=reuse_bytes,
    )
    assert reused.to_document()["exact_catalogue_hit_bypasses_constructor"] is True

