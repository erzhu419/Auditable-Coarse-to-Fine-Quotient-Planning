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

import acfqp.direct_feature_synthesis as direct_module
from acfqp.abstraction.partition import Partition
from acfqp.artifacts import object_id
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.direct_feature_synthesis import (
    DirectActionFeatureRegistryV1,
    DirectHomomorphismCandidateTraceV1,
    DirectHomomorphismCertificateV1,
    DirectHomomorphismSynthesisResultV1,
    DirectHomomorphismSynthesisSpecV1,
    DirectPredicateTreeV1,
    DirectStateFeatureRegistryV1,
    DirectSynthesisInvariantViolation,
    DirectSynthesisStatus,
    run_direct_lmb_negative_control_v1,
    synthesize_direct_lmb_homomorphism_v1,
    verify_direct_lmb_homomorphism_v1,
    verify_direct_lmb_negative_control_v1,
)
from acfqp.domains.matching_buffer import (
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.portable import dump_model, dump_query, load_model, load_query
from acfqp.portable_planner import load_result, solve_portable_pareto


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def direct_training_contract():
    kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    support = (
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
    rho = tuple(
        (
            Fraction(1, len(support)),
            LMBState(mask, buffer, LMBStatus.ACTIVE),
        )
        for mask, buffer in support
    )
    query = QuerySpec(
        rho,
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
    coverage = SuiteBuildCoverage.from_queries(kernel, (query,))
    assert len(coverage.covered_states) == 25
    return kernel, coverage, query


@pytest.fixture(scope="module")
def direct_result(direct_training_contract):
    kernel, coverage, _ = direct_training_contract
    return synthesize_direct_lmb_homomorphism_v1(kernel, coverage)


def test_production_api_and_import_graph_have_no_target_or_query_channel(
    direct_training_contract,
) -> None:
    kernel, _, query = direct_training_contract
    signature = inspect.signature(synthesize_direct_lmb_homomorphism_v1)
    assert tuple(signature.parameters) == ("kernel", "coverage")
    with pytest.raises(DirectSynthesisInvariantViolation, match="SuiteBuildCoverage"):
        synthesize_direct_lmb_homomorphism_v1(kernel, query)  # type: ignore[arg-type]

    imports = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(direct_module)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.feature_synthesis" not in imports
    assert "acfqp.abstraction.behavioral" not in imports
    assert "acfqp.core" not in imports
    assert not any(module.startswith("acfqp.planning") for module in imports)


def test_direct_homomorphism_golden_and_selection_rule(direct_result) -> None:
    result = direct_result
    certificate = result.certificate
    assert result.status is DirectSynthesisStatus.EXACT_DIRECT_HOMOMORPHISM
    assert len(result.trace.candidates) == 4096
    assert result.trace.required_candidate_count == 4096
    assert certificate.selected_state_features == ("action_count",)
    assert certificate.selected_action_features == ("completes_match",)
    assert certificate.state_thresholds == (Fraction(3, 2), Fraction(5, 2))
    assert (
        certificate.ground_state_count,
        certificate.active_ground_state_count,
        certificate.quotient_cell_count,
        certificate.active_quotient_cell_count,
        certificate.abstract_entry_count,
    ) == (25, 18, 5, 3, 4)
    assert certificate.action_alias_checked_before_mixture is True
    assert certificate.execution_profile == "production_full_grammar_v1"
    assert certificate.claim_kind == "DIRECT_EXACT_HOMOMORPHISM_INSIDE_FIXED_GRAMMAR"
    assert len(result.quotient_models.envelope.entries) == 4
    assert all(
        len(
            {
                (
                    realization.reward_features,
                    realization.failure_probability,
                    realization.termination_probability,
                    realization.successor_probabilities,
                )
                for realization in entry.realizations
            }
        )
        == 1
        for entry in result.quotient_models.envelope.entries
    )
    selected = next(
        item for item in result.trace.candidates
        if item.candidate_id == result.trace.selected_candidate_id
    )
    assert selected == min(
        (item for item in result.trace.candidates if item.exact_homomorphism),
        key=lambda item: (
            len(item.selected_state_features),
            len(item.selected_action_features),
            item.split_count,
            item.selected_state_features,
            item.selected_action_features,
            item.partition_id,
        ),
    )
    assert result.spec.selection_rule == direct_module.SELECTION_RULE


def _canonical_model(model) -> tuple:
    partition = model.envelope.partition
    block = {
        cell: tuple(sorted(object_id(state, "state") for state in partition.members(cell)))
        for cell in partition.cell_ids
    }
    records = []
    for entry in model.envelope.entries:
        signatures = {
            (
                realization.reward_features,
                realization.failure_probability,
                realization.termination_probability,
                tuple(sorted((block[cell], probability) for cell, probability in realization.successor_probabilities)),
            )
            for realization in entry.realizations
        }
        assert len(signatures) == 1
        records.append((block[entry.cell], next(iter(signatures))))
    return tuple(sorted(records, key=repr))


def test_evaluation_only_behavioral_oracle_matches_partition_and_model(
    direct_training_contract,
    direct_result,
) -> None:
    # Imported only after direct construction has completed; it is evaluation,
    # not a construction input or certificate authority.
    from acfqp.abstraction.behavioral import build_exact_behavioral_quotient

    kernel, coverage, _ = direct_training_contract
    target = build_exact_behavioral_quotient(kernel, coverage.covered_states)
    assert direct_result.partition.signature() == target.partition.signature()
    assert _canonical_model(direct_result.quotient_models) == _canonical_model(
        target.quotient_models
    )


def test_typed_artifact_transport_and_rebuild_determinism(
    direct_training_contract,
    direct_result,
) -> None:
    transport = lambda document: json.loads(json.dumps(document, sort_keys=True))
    assert DirectStateFeatureRegistryV1.from_document(
        transport(direct_result.state_registry.to_document())
    ) == direct_result.state_registry
    assert DirectActionFeatureRegistryV1.from_document(
        transport(direct_result.action_registry.to_document())
    ) == direct_result.action_registry
    assert DirectHomomorphismSynthesisSpecV1.from_document(
        transport(direct_result.spec.to_document())
    ) == direct_result.spec
    assert DirectHomomorphismCandidateTraceV1.from_document(
        transport(direct_result.trace.to_document())
    ) == direct_result.trace
    assert DirectPredicateTreeV1.from_document(
        transport(direct_result.predicate_tree.to_document())
    ) == direct_result.predicate_tree
    assert DirectHomomorphismCertificateV1.from_document(
        transport(direct_result.certificate.to_document())
    ) == direct_result.certificate

    kernel, coverage, _ = direct_training_contract
    assert verify_direct_lmb_homomorphism_v1(kernel, coverage, direct_result) == ()


def test_one_direct_model_serves_two_queries_in_fresh_processes(
    direct_training_contract,
    direct_result,
    tmp_path,
) -> None:
    _, coverage, first_query = direct_training_contract
    second_query = QuerySpec(
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
    built = direct_result.portable_build
    model_path = tmp_path / "direct-model.json"
    dump_model(built.model, model_path)
    query_ids = []
    for index, query in enumerate((first_query, second_query), 1):
        portable_query = built.query_from_spec(query)
        query_ids.append(portable_query.query_id)
        query_path = tmp_path / f"query-{index}.json"
        output_path = tmp_path / f"result-{index}.json"
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
                str(output_path),
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        model = load_model(model_path)
        loaded_query = load_query(query_path, model)
        assert load_result(output_path, model=model, query=loaded_query) == (
            solve_portable_pareto(built.model, portable_query)
        )
    assert len(set(query_ids)) == 2


def test_restricted_negative_and_cap_outcomes_cannot_claim_production(
    direct_training_contract,
    direct_result,
) -> None:
    kernel, coverage, _ = direct_training_contract
    negative = run_direct_lmb_negative_control_v1(
        kernel,
        coverage,
        state_feature_names=("match_debt_min",),
        action_feature_names=("completes_match",),
    )
    assert negative.status is DirectSynthesisStatus.NO_EXACT_DIRECT_HOMOMORPHISM
    assert len(negative.trace.candidates) == 4
    assert negative.certificate is None and negative.portable_build is None
    assert {item.witness_kind for item in negative.trace.witnesses} >= {
        "WITHIN_STATE_ACTION_ALIAS",
        "CROSS_STATE_LABEL_DYNAMICS_MISMATCH",
    }
    assert verify_direct_lmb_negative_control_v1(kernel, coverage, negative) == ()

    cap = run_direct_lmb_negative_control_v1(
        kernel,
        coverage,
        state_feature_names=("match_debt_min",),
        action_feature_names=("completes_match",),
        candidate_cap=1,
    )
    assert cap.status is DirectSynthesisStatus.CANDIDATE_CAP_EXHAUSTED
    assert cap.trace.required_candidate_count == 4
    assert cap.trace.evaluated_candidate_count == 0
    assert cap.trace.witnesses[0].witness_kind == "CANDIDATE_CAP_INSUFFICIENT"

    restricted_exact = run_direct_lmb_negative_control_v1(
        kernel,
        coverage,
        state_feature_names=("action_count",),
        action_feature_names=("completes_match",),
    )
    assert restricted_exact.status is DirectSynthesisStatus.RESTRICTED_CONTROL_EXACT_FOUND
    assert restricted_exact.certificate is None and restricted_exact.portable_build is None
    with pytest.raises(DirectSynthesisInvariantViolation, match="restricted-control"):
        verify_direct_lmb_homomorphism_v1(kernel, coverage, restricted_exact)
    with pytest.raises(DirectSynthesisInvariantViolation, match="production provenance"):
        verify_direct_lmb_negative_control_v1(kernel, coverage, direct_result)


def test_coherent_resign_transport_nested_proxy_and_source_attacks(
    direct_training_contract,
    direct_result,
    monkeypatch,
) -> None:
    def resign(document, identifier, domain):
        payload = dict(document)
        payload.pop(identifier)
        document[identifier] = direct_module._content_id(domain, payload)

    state_document = direct_result.state_registry.to_document()
    state_document["definitions"] = ""
    resign(state_document, "registry_id", direct_module.STATE_REGISTRY_DOMAIN)
    with pytest.raises(DirectSynthesisInvariantViolation, match="must be a list"):
        DirectStateFeatureRegistryV1.from_document(state_document)

    spec_document = direct_result.spec.to_document()
    spec_document["selection_rule"] = "attacker_rule"
    spec_document["forbidden_information_channels"].remove("QuerySpec")
    resign(spec_document, "spec_id", direct_module.DIRECT_SPEC_DOMAIN)
    with pytest.raises(DirectSynthesisInvariantViolation, match="substitution"):
        DirectHomomorphismSynthesisSpecV1.from_document(spec_document)

    certificate_document = direct_result.certificate.to_document()
    certificate_document["workload_economics_gate"] = "WORKLOAD_ECONOMICS_GATE_RUN"
    certificate_document["claim_scope"] = "feature invention at scale"
    resign(certificate_document, "certificate_id", direct_module.CERTIFICATE_DOMAIN)
    with pytest.raises(DirectSynthesisInvariantViolation, match="claim|Gate"):
        DirectHomomorphismCertificateV1.from_document(certificate_document)

    class DuckModel:
        def to_dict(self):
            return direct_result.portable_build.model.to_dict()

    with pytest.raises(DirectSynthesisInvariantViolation, match="type substitution"):
        replace(
            direct_result,
            portable_build=replace(direct_result.portable_build, model=DuckModel()),
        )

    nominal_entry = direct_result.quotient_models.nominal.entries[0]
    malformed_model = replace(
        nominal_entry.model,
        reward_features=(("match", 1),),
    )
    malformed_nominal = replace(
        direct_result.quotient_models.nominal,
        entries=(replace(nominal_entry, model=malformed_model),)
        + direct_result.quotient_models.nominal.entries[1:],
    )
    with pytest.raises(
        DirectSynthesisInvariantViolation,
        match="nominal model vector type substitution",
    ):
        replace(
            direct_result,
            quotient_models=replace(
                direct_result.quotient_models,
                nominal=malformed_nominal,
            ),
        )

    forged_trace = replace(
        direct_result.trace,
        required_candidate_count=4095,
        evaluated_candidate_count=4095,
        candidates=direct_result.trace.candidates[1:],
    )
    forged_certificate = replace(
        direct_result.certificate,
        trace_id=forged_trace.trace_id,
    )
    forged = replace(
        direct_result,
        trace=forged_trace,
        certificate=forged_certificate,
    )
    kernel, coverage, _ = direct_training_contract
    assert "TRACE_MISMATCH" in verify_direct_lmb_homomorphism_v1(
        kernel, coverage, forged
    )

    original_getsource = direct_module.inspect.getsource
    monkeypatch.setattr(
        direct_module.inspect,
        "getsource",
        lambda target: "tampered implementation" if target is direct_module._action_feature_values else original_getsource(target),
    )
    with pytest.raises(DirectSynthesisInvariantViolation, match="frozen authority"):
        synthesize_direct_lmb_homomorphism_v1(kernel, coverage)


def test_fresh_import_and_construction_survive_behavioral_module_poison(tmp_path) -> None:
    script = tmp_path / "poison_import.py"
    script.write_text(
        """
import json, sys, types
from fractions import Fraction
class Poison(types.ModuleType):
    def __getattr__(self, name):
        raise RuntimeError('behavioral target accessed: ' + name)
sys.modules['acfqp.abstraction.behavioral'] = Poison('acfqp.abstraction.behavioral')
from acfqp.direct_feature_synthesis import synthesize_direct_lmb_homomorphism_v1
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains.matching_buffer import LMBState, LMBStatus, generate_solvable_lmb
k,_=generate_solvable_lmb(tile_count=6,type_count=2,capacity=3,max_layers=2,seed=0)
d=((11,(1,2)),(13,(2,1)),(19,(1,2)),(21,(2,1)),(25,(1,2)),(35,(2,1)),(41,(2,1)),(49,(2,1)),(7,(2,1)))
rho=tuple((Fraction(1,len(d)),LMBState(m,b,LMBStatus.ACTIVE)) for m,b in d)
q=QuerySpec(rho,3,(("match",Fraction(1)),("terminal_clear",Fraction(1))),"default",Fraction(1,20),Fraction(4),"lmb.canonical.matches_plus_clear_le_2n_over_3.v1")
c=SuiteBuildCoverage.from_queries(k,(q,))
r=synthesize_direct_lmb_homomorphism_v1(k,c)
print(json.dumps({"status":r.status.value,"features":r.certificate.selected_state_features,"actions":r.certificate.selected_action_features}))
""",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {
        "status": "EXACT_DIRECT_HOMOMORPHISM",
        "features": ["action_count"],
        "actions": ["completes_match"],
    }


def test_direct_claim_and_phase3e_gates_remain_narrow_and_locked(direct_result) -> None:
    certificate = direct_result.certificate
    assert certificate.official_execution_allowed is False
    assert certificate.official_scalar_cost is None
    assert certificate.official_N_break_even is None
    assert certificate.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert certificate.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert "no feature-invention" in certificate.claim_scope
    assert "partial-model" in certificate.claim_scope
    assert "scale" in certificate.claim_scope
