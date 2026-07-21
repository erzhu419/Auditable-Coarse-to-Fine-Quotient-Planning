from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import acfqp.feature_synthesis as synthesis_module
from acfqp.abstraction.partition import Partition
from acfqp.artifacts import object_id
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains.matching_buffer import (
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.domains.semantic import LMBSemanticAdapter
from acfqp.feature_synthesis import (
    CanonicalPredicateTreeV1,
    FeatureRAPMSynthesisStatus,
    FeatureRealizationCertificateV1,
    FeatureRegistryV1,
    FeatureSynthesisInvariantViolation,
    LMB_FEATURE_IMPLEMENTATION_SHA256_V1,
    SynthesisCandidateTraceV1,
    SynthesisSpecV1,
    lmb_feature_registry_v1,
    lmb_synthesis_spec_v1,
    replace_candidate_trace_for_attack,
    synthesize_lmb_feature_rapm_negative_control_v1,
    synthesize_lmb_feature_rapm_v1,
    verify_lmb_feature_rapm_negative_control_v1,
    verify_lmb_feature_rapm_synthesis_v1,
)
from acfqp.portable import (
    PortableRAPM,
    dump_model,
    dump_query,
    load_model,
    load_query,
)
from acfqp.portable_planner import load_result, solve_portable_pareto


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def lmb_training_contract():
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    declared_support = (
        (11, (1, 2)),
        (13, (2, 1)),
        (19, (1, 2)),
        (21, (2, 1)),
        (25, (1, 2)),
        (35, (2, 1)),
        (41, (2, 1)),
        (49, (2, 1)),
        (7, (2, 1)),
    )
    initial_distribution = tuple(
        (
            Fraction(1, len(declared_support)),
            LMBState(mask, buffer, LMBStatus.ACTIVE),
        )
        for mask, buffer in declared_support
    )
    # Query material is used only here to freeze SuiteBuildCoverage.  The
    # synthesizer below receives only that immutable coverage certificate.
    coverage_query = QuerySpec(
        initial_distribution,
        horizon=3,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(1)),
        ),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(4),
        normalizer_proof_id="lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    )
    coverage = SuiteBuildCoverage.from_queries(kernel, (coverage_query,))
    return kernel, coverage, coverage_query


@pytest.fixture(scope="module")
def synthesized_lmb(lmb_training_contract):
    kernel, coverage, _ = lmb_training_contract
    return synthesize_lmb_feature_rapm_v1(kernel, coverage)


def test_synthesis_has_query_free_public_boundary(lmb_training_contract) -> None:
    kernel, coverage, query = lmb_training_contract
    signature = inspect.signature(synthesize_lmb_feature_rapm_v1)
    assert tuple(signature.parameters) == ("kernel", "coverage")
    forbidden_parameter_fragments = (
        "query",
        "j0",
        "q_value",
        "value",
        "policy",
        "heldout",
    )
    assert all(
        fragment not in parameter.lower()
        for parameter in signature.parameters
        for fragment in forbidden_parameter_fragments
    )

    source = inspect.getsource(synthesis_module)
    imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        module == "acfqp.core"
        or module.startswith("acfqp.planning")
        or module.startswith("acfqp.abstraction.oracle")
        or module == "acfqp.phase3a"
        for module in imports
    )
    with pytest.raises(FeatureSynthesisInvariantViolation, match="SuiteBuildCoverage"):
        synthesize_lmb_feature_rapm_v1(kernel, query)  # type: ignore[arg-type]

    spec = lmb_synthesis_spec_v1(kernel, coverage, lmb_feature_registry_v1())
    assert set(spec.forbidden_information_channels) == {
        "QuerySpec",
        "J0",
        "Q_values",
        "value_function",
        "policy",
        "heldout_data",
    }


def test_production_profile_cannot_encode_query_bits_in_a_registry_subset(
    lmb_training_contract,
) -> None:
    kernel, coverage, _query = lmb_training_contract
    exact_registry = lmb_feature_registry_v1(("action_count",))
    failed_registry = lmb_feature_registry_v1(("match_debt_min",))

    for registry in (exact_registry, failed_registry):
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            synthesize_lmb_feature_rapm_v1(  # type: ignore[call-arg]
                kernel,
                coverage,
                registry=registry,
            )

    with pytest.raises(
        FeatureSynthesisInvariantViolation,
        match="negative-control profile cannot publish an exact realization",
    ):
        synthesize_lmb_feature_rapm_negative_control_v1(
            kernel,
            coverage,
            registry=exact_registry,
        )
    forged_exact_control = synthesis_module._synthesize_lmb_feature_rapm_profile_v1(
        kernel,
        coverage,
        registry=exact_registry,
        spec=lmb_synthesis_spec_v1(
            kernel,
            coverage,
            exact_registry,
            profile_kind=synthesis_module.RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1,
        ),
    )
    assert forged_exact_control.certificate is not None
    assert verify_lmb_feature_rapm_negative_control_v1(
        kernel, coverage, forged_exact_control
    ) == ("NEGATIVE_CONTROL_PROFILE_MISMATCH",)
    assert verify_lmb_feature_rapm_synthesis_v1(
        kernel, coverage, forged_exact_control
    ) != ()
    failed_control = synthesize_lmb_feature_rapm_negative_control_v1(
        kernel,
        coverage,
        registry=failed_registry,
    )
    assert failed_control.status is FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION
    assert failed_control.synthesis_spec.profile_kind == (
        synthesis_module.RESTRICTED_NEGATIVE_CONTROL_PROFILE_V1
    )
    assert verify_lmb_feature_rapm_negative_control_v1(
        kernel, coverage, failed_control
    ) == ()


def test_feature_implementation_digest_is_frozen_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert synthesis_module._lmb_feature_implementation_sha256() == (
        LMB_FEATURE_IMPLEMENTATION_SHA256_V1
    )
    monkeypatch.setattr(
        synthesis_module,
        "_lmb_feature_implementation_sha256",
        lambda: "0" * 64,
    )
    with pytest.raises(
        FeatureSynthesisInvariantViolation,
        match="frozen V1 code authority",
    ):
        lmb_feature_registry_v1()


def test_lmb_synthesis_exact_golden_and_canonical_two_split_tree(
    synthesized_lmb,
) -> None:
    result = synthesized_lmb
    assert result.status is FeatureRAPMSynthesisStatus.EXACT_FEATURE_REALIZATION
    certificate = result.certificate
    tree = result.predicate_tree
    assert certificate is not None
    assert tree is not None
    assert result.feature_registry == lmb_feature_registry_v1()
    assert result.synthesis_spec.profile_kind == (
        synthesis_module.CANONICAL_PRODUCTION_PROFILE_V1
    )

    assert certificate.selected_features == ("action_count",)
    assert certificate.selected_thresholds == (Fraction(3, 2), Fraction(5, 2))
    assert (
        certificate.ground_state_count,
        certificate.active_ground_state_count,
        certificate.quotient_cell_count,
        certificate.active_quotient_cell_count,
    ) == (25, 18, 5, 3)
    assert result.realized_partition.signature() == (
        result.behavioral_target.partition.signature()
    )
    assert certificate.target_partition_id == certificate.realized_partition_id
    assert certificate.envelope_is_singleton

    assert tuple(atom.feature_name for atom in tree.generated_atoms) == (
        "action_count",
        "action_count",
    )
    assert tuple(atom.threshold for atom in tree.generated_atoms) == (
        Fraction(3, 2),
        Fraction(5, 2),
    )
    assert len(tree.split_nodes) == 2
    first, second = tree.split_nodes
    assert first.parent_member_count == 18
    assert (first.true_member_count, first.false_member_count) == (5, 13)
    assert second.parent_cell_id == first.false_child_cell_id
    assert (second.true_member_count, second.false_member_count) == (4, 9)

    assert len(result.candidate_trace.candidates) == 2**11
    selected = next(
        candidate
        for candidate in result.candidate_trace.candidates
        if candidate.candidate_id == result.candidate_trace.selected_candidate_id
    )
    assert selected.selected_features == ("action_count",)
    assert selected.applied_split_count == 2
    assert selected.exact_target_match
    assert result.synthesis_spec.selection_rule == (
        "minimum_feature_count_then_minimum_split_count_then_lexicographic_"
        "feature_names_then_partition_id_v1"
    )
    assert selected == min(
        (
            candidate
            for candidate in result.candidate_trace.candidates
            if candidate.exact_target_match
        ),
        key=lambda candidate: (
            len(candidate.selected_features),
            candidate.applied_split_count,
            candidate.selected_features,
            candidate.final_partition_id,
        ),
    )


def test_all_typed_artifacts_and_portable_model_round_trip(
    synthesized_lmb,
    tmp_path,
) -> None:
    result = synthesized_lmb
    transport = lambda document: json.loads(
        json.dumps(document, ensure_ascii=False, sort_keys=True)
    )
    registry = FeatureRegistryV1.from_document(
        transport(result.feature_registry.to_document())
    )
    spec = SynthesisSpecV1.from_document(transport(result.synthesis_spec.to_document()))
    trace = SynthesisCandidateTraceV1.from_document(
        transport(result.candidate_trace.to_document())
    )
    tree = CanonicalPredicateTreeV1.from_document(
        transport(result.predicate_tree.to_document())
    )
    certificate = FeatureRealizationCertificateV1.from_document(
        transport(result.certificate.to_document())
    )
    assert registry == result.feature_registry
    assert spec == result.synthesis_spec
    assert trace == result.candidate_trace
    assert tree == result.predicate_tree
    assert certificate == result.certificate

    assert all(
        len(identifier) == 64 and identifier == identifier.lower()
        for identifier in (
            registry.feature_registry_id,
            spec.synthesis_spec_id,
            trace.candidate_trace_id,
            tree.predicate_tree_id,
            certificate.feature_realization_certificate_id,
        )
    )
    portable = PortableRAPM.from_dict(result.portable_build.model.to_dict())
    assert portable.model_id == result.portable_build.model.model_id
    path = tmp_path / "feature-realized-rapm.json"
    dump_model(portable, path)
    assert load_model(path).to_dict() == portable.to_dict()


@pytest.mark.parametrize("artifact", ("trace", "tree", "certificate"))
def test_transport_parser_rejects_string_for_json_list(
    synthesized_lmb,
    artifact: str,
) -> None:
    if artifact == "trace":
        document = synthesized_lmb.candidate_trace.to_document()
        assert document["candidates"][0]["selected_features"] == []
        document["candidates"][0]["selected_features"] = ""
        parser = SynthesisCandidateTraceV1.from_document
    elif artifact == "tree":
        document = synthesized_lmb.predicate_tree.to_document()
        document["selected_features"] = "action_count"
        parser = CanonicalPredicateTreeV1.from_document
    else:
        document = synthesized_lmb.certificate.to_document()
        document["selected_features"] = "action_count"
        parser = FeatureRealizationCertificateV1.from_document
    with pytest.raises(FeatureSynthesisInvariantViolation, match="JSON list"):
        parser(document)


def test_one_synthesized_rapm_serves_two_queries_in_fresh_processes(
    lmb_training_contract,
    synthesized_lmb,
    tmp_path,
) -> None:
    _, coverage, coverage_query = lmb_training_contract
    alternate = QuerySpec(
        ((Fraction(1), coverage.declared_support_states[0]),),
        horizon=2,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(0)),
        ),
        goal="default",
        delta=Fraction(1, 10),
        normalizer=Fraction(2),
        normalizer_proof_id="lmb.match_only.matches_le_n_over_3.v1",
    )
    built = synthesized_lmb.portable_build
    model_path = tmp_path / "synthesized-rapm.json"
    dump_model(built.model, model_path)
    query_ids: list[str] = []
    for index, query in enumerate((coverage_query, alternate), start=1):
        portable_query = built.query_from_spec(query)
        query_ids.append(portable_query.query_id)
        query_path = tmp_path / f"query-{index}.json"
        result_path = tmp_path / f"result-{index}.json"
        dump_query(portable_query, query_path)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "acfqp.portable_planner",
                "--model",
                str(model_path),
                "--query",
                str(query_path),
                "--output",
                str(result_path),
            ],
            cwd=tmp_path,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        loaded_model = load_model(model_path)
        loaded_query = load_query(query_path, loaded_model)
        loaded_result = load_result(
            result_path, model=loaded_model, query=loaded_query
        )
        assert loaded_result == solve_portable_pareto(built.model, portable_query)
    assert len(set(query_ids)) == 2


def test_synthesis_is_deterministic_under_registry_input_reordering(
    lmb_training_contract,
    synthesized_lmb,
) -> None:
    kernel, coverage, _ = lmb_training_contract
    reversed_input = tuple(reversed(synthesized_lmb.feature_registry.feature_names))
    registry = lmb_feature_registry_v1(reversed_input)
    assert registry == synthesized_lmb.feature_registry
    repeated = synthesize_lmb_feature_rapm_v1(kernel, coverage)
    assert repeated.feature_registry.feature_registry_id == (
        synthesized_lmb.feature_registry.feature_registry_id
    )
    assert repeated.synthesis_spec.synthesis_spec_id == (
        synthesized_lmb.synthesis_spec.synthesis_spec_id
    )
    assert repeated.candidate_trace.candidate_trace_id == (
        synthesized_lmb.candidate_trace.candidate_trace_id
    )
    assert repeated.predicate_tree.predicate_tree_id == (
        synthesized_lmb.predicate_tree.predicate_tree_id
    )
    assert repeated.certificate.feature_realization_certificate_id == (
        synthesized_lmb.certificate.feature_realization_certificate_id
    )
    assert repeated.portable_build.model.to_dict() == (
        synthesized_lmb.portable_build.model.to_dict()
    )


def test_content_address_and_independent_rebuild_reject_attacks(
    lmb_training_contract,
    synthesized_lmb,
) -> None:
    kernel, coverage, _ = lmb_training_contract

    registry_document = synthesized_lmb.feature_registry.to_document()
    registry_document["definitions"][0]["semantics"] = "attacker substituted meaning"
    with pytest.raises(
        FeatureSynthesisInvariantViolation, match="canonical V1 authority|ID mismatch"
    ):
        FeatureRegistryV1.from_document(registry_document)

    certificate_document = synthesized_lmb.certificate.to_document()
    certificate_document["active_ground_state_count"] += 1
    with pytest.raises(FeatureSynthesisInvariantViolation, match="ID mismatch"):
        FeatureRealizationCertificateV1.from_document(certificate_document)

    tree_document = synthesized_lmb.predicate_tree.to_document()
    tree_document["generated_atoms"][0]["threshold"] = {
        "numerator": 7,
        "denominator": 4,
    }
    with pytest.raises(FeatureSynthesisInvariantViolation, match="ID mismatch"):
        CanonicalPredicateTreeV1.from_document(tree_document)

    # This forgery is internally content-addressed: a nonselected candidate is
    # deleted and the trace ID changes coherently.  Only independent rebuilding
    # of the registered enumeration detects the semantically incomplete trace.
    trace = synthesized_lmb.candidate_trace
    forged_trace = replace(trace, candidates=trace.candidates[1:])
    assert forged_trace.candidate_trace_id != trace.candidate_trace_id
    forged_result = replace_candidate_trace_for_attack(
        synthesized_lmb, forged_trace
    )
    failures = verify_lmb_feature_rapm_synthesis_v1(
        kernel, coverage, forged_result
    )
    assert "CANDIDATE_TRACE_MISMATCH" in failures

    forged_nominal = replace(
        synthesized_lmb.quotient_models.nominal,
        horizon=synthesized_lmb.quotient_models.nominal.horizon + 1,
    )
    forged_models = replace(
        synthesized_lmb.quotient_models,
        nominal=forged_nominal,
    )
    one_cell = Partition.single_cell(coverage.covered_states, "forged-root")
    forged_adapter = replace(
        synthesized_lmb.behavioral_target.semantic_adapter,
        assignments=synthesized_lmb.behavioral_target.semantic_adapter.assignments[:-1],
    )
    forged_target = replace(
        synthesized_lmb.behavioral_target,
        partition=one_cell,
        refinement_trace=synthesized_lmb.behavioral_target.refinement_trace[:-1],
        semantic_adapter=forged_adapter,
        quotient_models=forged_models,
    )
    forged_portable_registry = replace(
        synthesized_lmb.portable_build.registry,
        state_records=tuple(
            reversed(synthesized_lmb.portable_build.registry.state_records)
        ),
    )
    forged_runtime_result = replace(
        synthesized_lmb,
        behavioral_target=forged_target,
        realized_partition=one_cell,
        quotient_models=forged_models,
        portable_build=replace(
            synthesized_lmb.portable_build,
            registry=forged_portable_registry,
        ),
    )
    runtime_failures = set(
        verify_lmb_feature_rapm_synthesis_v1(
            kernel, coverage, forged_runtime_result
        )
    )
    assert {
        "BEHAVIORAL_TARGET_PARTITION_MISMATCH",
        "BEHAVIORAL_TARGET_TRACE_MISMATCH",
        "BEHAVIORAL_TARGET_ADAPTER_MISMATCH",
        "BEHAVIORAL_TARGET_MODEL_MISMATCH",
        "REALIZED_PARTITION_MISMATCH",
        "QUOTIENT_MODELS_MISMATCH",
        "PORTABLE_REGISTRY_MISMATCH",
    } <= runtime_failures


def test_runtime_proxy_members_cannot_obtain_a_verifier_pass(
    lmb_training_contract,
    synthesized_lmb,
) -> None:
    kernel, coverage, query = lmb_training_contract

    public_member_attacks = (
        {"status": "EXACT_FEATURE_REALIZATION"},
        {"feature_registry": object()},
        {"synthesis_spec": object()},
        {"behavioral_target": object()},
        {
            "behavioral_target": replace(
                synthesized_lmb.behavioral_target,
                partition=object(),
            )
        },
        {"candidate_trace": object()},
        {"predicate_tree": object()},
        {"realized_partition": object()},
        {"quotient_models": object()},
        {
            "quotient_models": replace(
                synthesized_lmb.quotient_models,
                nominal=object(),
            )
        },
        {"unresolved_witnesses": (object(),)},
    )
    for attack in public_member_attacks:
        with pytest.raises(
            FeatureSynthesisInvariantViolation,
            match="substituted runtime type|exact|unresolved_witnesses",
        ):
            replace(synthesized_lmb, **attack)

    class LyingCertificate:
        official_execution_allowed = True
        claim_scope = "attacker-controlled runtime claim"

        def to_document(self):
            return synthesized_lmb.certificate.to_document()

    class LyingModel:
        attacker_payload = "runtime model substituted"

        def to_dict(self):
            return synthesized_lmb.portable_build.model.to_dict()

    class LyingBuild:
        model = LyingModel()
        registry = synthesized_lmb.portable_build.registry

        def query_from_spec(self, _query):
            return "ATTACKER_CONTROLLED_QUERY"

    with pytest.raises(
        FeatureSynthesisInvariantViolation,
        match="certificate has a substituted runtime type",
    ):
        replace(synthesized_lmb, certificate=LyingCertificate())
    with pytest.raises(
        FeatureSynthesisInvariantViolation,
        match="portable_build has a substituted runtime type",
    ):
        replace(synthesized_lmb, portable_build=LyingBuild())

    forged_certificate = replace(synthesized_lmb)
    object.__setattr__(forged_certificate, "certificate", LyingCertificate())
    assert verify_lmb_feature_rapm_synthesis_v1(
        kernel, coverage, forged_certificate
    ) == ("RUNTIME_TYPE_MISMATCH",)
    assert forged_certificate.certificate.official_execution_allowed is True

    forged_build = replace(synthesized_lmb)
    object.__setattr__(forged_build, "portable_build", LyingBuild())
    assert verify_lmb_feature_rapm_synthesis_v1(
        kernel, coverage, forged_build
    ) == ("RUNTIME_TYPE_MISMATCH",)
    assert forged_build.portable_build.query_from_spec(query) == (
        "ATTACKER_CONTROLLED_QUERY"
    )


def test_coherently_resigned_contract_substitutions_are_rejected(
    synthesized_lmb,
) -> None:
    def resign(document, identifier, domain):
        payload = dict(document)
        payload.pop(identifier)
        document[identifier] = synthesis_module._content_id(domain, payload)

    registry_document = synthesized_lmb.feature_registry.to_document()
    registry_document["definitions"][0]["semantics"] = "coherently resigned lie"
    resign(
        registry_document,
        "feature_registry_id",
        synthesis_module.FEATURE_REGISTRY_DOMAIN,
    )
    with pytest.raises(
        FeatureSynthesisInvariantViolation, match="canonical V1 authority"
    ):
        FeatureRegistryV1.from_document(registry_document)

    spec_document = synthesized_lmb.synthesis_spec.to_document()
    spec_document["forbidden_information_channels"].remove("QuerySpec")
    spec_document["selection_rule"] = "attacker_preferred_candidate_v1"
    resign(
        spec_document,
        "synthesis_spec_id",
        synthesis_module.SYNTHESIS_SPEC_DOMAIN,
    )
    with pytest.raises(
        FeatureSynthesisInvariantViolation,
        match="forbidden information channels|selection rule",
    ):
        SynthesisSpecV1.from_document(spec_document)

    for field, forged_value, message in (
        ("workload_economics_gate", "WORKLOAD_ECONOMICS_GATE_RUN", "NOT_RUN"),
        ("counter_completeness_gate", "COUNTER_COMPLETENESS_GATE_RUN", "NOT_RUN"),
        ("claim_scope", "unbounded official strategic-world-model claim", "claim scope"),
    ):
        certificate_document = synthesized_lmb.certificate.to_document()
        certificate_document[field] = forged_value
        resign(
            certificate_document,
            "feature_realization_certificate_id",
            synthesis_module.REALIZATION_CERTIFICATE_DOMAIN,
        )
        with pytest.raises(FeatureSynthesisInvariantViolation, match=message):
            FeatureRealizationCertificateV1.from_document(certificate_document)


def test_negative_grammar_returns_typed_unseparated_witness(
    lmb_training_contract,
) -> None:
    kernel, coverage, _ = lmb_training_contract
    registry = lmb_feature_registry_v1(("match_debt_min",))
    result = synthesize_lmb_feature_rapm_negative_control_v1(
        kernel,
        coverage,
        registry=registry,
    )
    assert result.status is FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION
    assert result.candidate_trace.status is (
        FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION
    )
    assert len(result.candidate_trace.candidates) == 2
    assert result.certificate is None
    assert result.predicate_tree is None
    assert result.realized_partition is None
    assert result.quotient_models is None
    assert result.portable_build is None
    assert len(result.unresolved_witnesses) == 1

    witness = result.unresolved_witnesses[0]
    assert witness.witness_kind == "TARGET_SEPARATED_FEATURE_ALIASED"
    assert witness.left_target_cell_id != witness.right_target_cell_id
    assert witness.left_candidate_cell_id == witness.right_candidate_cell_id
    by_id = {object_id(state, "state"): state for state in coverage.covered_states}
    left = by_id[witness.left_state_id]
    right = by_id[witness.right_state_id]
    assert result.behavioral_target.partition.cell_of(left) != (
        result.behavioral_target.partition.cell_of(right)
    )
    adapter = LMBSemanticAdapter()
    left_features = dict(adapter.features(kernel, left))
    right_features = dict(adapter.features(kernel, right))
    assert left_features["match_debt_min"] == right_features["match_debt_min"]
    assert verify_lmb_feature_rapm_negative_control_v1(kernel, coverage, result) == ()


def test_incomparable_feature_partition_returns_typed_oversplit_witness() -> None:
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    coverage_query = QuerySpec(
        kernel.initial_distribution(),
        horizon=3,
        reward_weights=(
            ("match", Fraction(1)),
            ("terminal_clear", Fraction(1)),
        ),
        goal="default",
        delta=Fraction(1, 10),
        normalizer=Fraction(4),
        normalizer_proof_id="lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
    )
    coverage = SuiteBuildCoverage.from_queries(kernel, (coverage_query,))
    assert len(coverage.covered_states) == 36
    registry = lmb_feature_registry_v1(("action_count",))
    result = synthesize_lmb_feature_rapm_negative_control_v1(
        kernel,
        coverage,
        registry=registry,
    )
    assert result.status is FeatureRAPMSynthesisStatus.NO_EXACT_FEATURE_REALIZATION
    witness = result.unresolved_witnesses[0]
    assert witness.witness_kind == "TARGET_MERGED_FEATURE_SEPARATED"
    assert witness.left_target_cell_id == witness.right_target_cell_id
    assert witness.left_candidate_cell_id != witness.right_candidate_cell_id

    by_id = {object_id(state, "state"): state for state in coverage.covered_states}
    left = by_id[witness.left_state_id]
    right = by_id[witness.right_state_id]
    assert result.behavioral_target.partition.cell_of(left) == (
        result.behavioral_target.partition.cell_of(right)
    )
    adapter = LMBSemanticAdapter()
    assert dict(adapter.features(kernel, left))["action_count"] != (
        dict(adapter.features(kernel, right))["action_count"]
    )
    assert {
        item.witness_kind for item in result.candidate_trace.witnesses
    } == {
        "TARGET_SEPARATED_FEATURE_ALIASED",
        "TARGET_MERGED_FEATURE_SEPARATED",
    }
    assert verify_lmb_feature_rapm_negative_control_v1(kernel, coverage, result) == ()


def test_feature_certificate_keeps_all_phase3e_gates_locked(synthesized_lmb) -> None:
    certificate = synthesized_lmb.certificate
    assert certificate.official_execution_allowed is False
    assert certificate.official_scalar_cost is None
    assert certificate.official_N_break_even is None
    assert certificate.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert certificate.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert "no query/value/policy/heldout claim" in certificate.claim_scope
