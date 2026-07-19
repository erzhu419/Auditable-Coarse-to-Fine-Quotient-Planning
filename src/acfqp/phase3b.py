"""Contract-0.7 portable abstract-world-model planning campaign.

This slice changes the unit of evidence from an in-process quotient experiment
to a reusable model consumed by a separate planning process.  Construction is
the exact, query-value-free behavioural minimisation control; the planner sees
only the serialized RAPM and a cell-level query.  Ground J0 is deliberately
started only after every portable proposal has been produced and is used only
for independent evaluation.

The profile exercises the normal ``ABSTRACT_CERTIFIED`` route.  It freezes the
interfaces and accounting boundaries needed by later certificate-triggered
local repair, but does not claim that the hybrid or economics gates have run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from acfqp.abstraction import ExactBehavioralQuotient, build_exact_behavioral_quotient
from acfqp.artifacts import (
    PHASE3B_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import safe_chain_fixture
from acfqp.domains.matching_buffer import generate_solvable_lmb
from acfqp.phase3a import NamedQuery, _g2048_query_suite, _lmb_query_suite
from acfqp.planning import (
    FiniteHorizonPolicy,
    audit_abstract_policy,
    lift_semantic_policy,
    solve_ground_pareto,
)
from acfqp.portable import (
    PortableBuildResult,
    PortableQuery,
    build_portable_rapm,
    dump_model,
    dump_query,
    fraction_to_json,
    load_model,
    logical_id,
)
from acfqp.portable_planner import (
    PortableExactEnvelopeAudit,
    PortablePlanResult,
    audit_exact_portable_policy,
    load_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_KEY = "phase3b_portable_rapm_campaign_v0"
EXECUTION_PROFILE = "phase3b_portable_rapm_campaign"
CONTRACT_VERSION = "0.7.0"
STATE_CAP = 50_000

SLICE_PASS = "PHASE3B_PORTABLE_RAPM_PASS"
FULL_PHASE3_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"
LOCAL_HYBRID_NOT_RUN = "LOCAL_HYBRID_GATE_NOT_RUN"
ECONOMICS_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
INVARIANT_FAILURE = "PHASE3B_INVARIANT_VIOLATION"

SUPPORTED_CLAIMS = (
    "complete exact one-step behavioural signatures can synthesize a portable RAPM without Q*, value, or policy signatures",
    "fresh processes can perform repeated multi-step contingent planning using only a serialized RAPM and portable query",
    "the two frozen RAPMs preserve reward, failure probability, and constrained deterministic policies on the registered eleven-query campaign",
)

UNSUPPORTED_CLAIMS = (
    "automatic human-readable predicate or strategic-variable invention",
    "learned or partial-observation world-model induction",
    "certificate-triggered hybrid local-ground recovery",
    "workload break-even or amortized speedup",
    "complete Phase-3 60/20/40 or Phase-5 multiresolution Gate",
    "large-scale, visual, option-level, or cross-domain shared-coordinate generality",
)


class Phase3BInvariantViolation(RuntimeError):
    status = INVARIANT_FAILURE


@dataclass(frozen=True, slots=True)
class DomainWorldModel:
    domain: str
    kernel: Any
    structural_id: str
    train_queries: tuple[NamedQuery, ...]
    campaign_queries: tuple[NamedQuery, ...]
    coverage: SuiteBuildCoverage[Any]
    behavioural: ExactBehavioralQuotient
    portable: PortableBuildResult


@dataclass(frozen=True, slots=True)
class PortableProposal:
    domain_model: DomainWorldModel
    named_query: NamedQuery
    ground_query_id: str
    portable_query: PortableQuery
    result: PortablePlanResult
    process_id: int
    runtime_attestation: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CampaignEvaluation:
    proposal: PortableProposal
    abstract_policy: FiniteHorizonPolicy[Any, Any]
    portable_audit: PortableExactEnvelopeAudit
    audit: Any
    lift: Any
    ground: Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _source_tree_hash() -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = PROJECT_ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for name in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    for path in sorted(set(paths)):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted((PROJECT_ROOT / "specs").glob("*.md"))
    }


def _lmb_campaign_queries(kernel: Any) -> tuple[tuple[NamedQuery, ...], tuple[NamedQuery, ...]]:
    train, heldout = _lmb_query_suite(kernel)
    base = train[0].query
    delta_ten = QuerySpec(
        base.initial_distribution,
        3,
        base.reward_weights,
        base.goal,
        Fraction(1, 10),
        base.normalizer,
        base.normalizer_proof_id,
    )
    terminal_only = QuerySpec(
        base.initial_distribution,
        3,
        (("match", Fraction(0)), ("terminal_clear", Fraction(1))),
        base.goal,
        Fraction(1, 20),
        Fraction(2),
        "lmb.terminal_clear_only.clear_bonus.v1",
    )
    extras = (
        NamedQuery("lmb.alias9.canonical.h3.delta10", "campaign", delta_ten),
        NamedQuery("lmb.alias9.terminal_clear_only.h3", "campaign", terminal_only),
    )
    return train, heldout + extras


def _portable_build(
    kernel: Any,
    behavioural: ExactBehavioralQuotient,
    coverage: SuiteBuildCoverage[Any],
) -> PortableBuildResult:
    failures = set(behavioural.failure_targets)
    if tuple(kernel.registered_reward_features) == ("merge",):
        normalizer_rules = (
            {
                "proof_id": "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {"name": "merge", "value": fraction_to_json(Fraction(1))},
                ),
                "feature_caps": (
                    {
                        "name": "merge",
                        "per_step_cap": fraction_to_json(Fraction(1)),
                        "total_cap": None,
                    },
                ),
            },
        )
    elif tuple(kernel.registered_reward_features) == (
        "match",
        "terminal_clear",
    ):
        match_cap = {
            "name": "match",
            "per_step_cap": fraction_to_json(Fraction(1)),
            "total_cap": fraction_to_json(Fraction(kernel.tile_count // 3)),
        }
        terminal_clear_cap = {
            "name": "terminal_clear",
            "per_step_cap": fraction_to_json(Fraction(kernel.clear_bonus)),
            "total_cap": fraction_to_json(Fraction(kernel.clear_bonus)),
        }
        normalizer_rules = (
            {
                "proof_id": "lmb.canonical.matches_plus_clear_le_2n_over_3.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {"name": "match", "value": fraction_to_json(Fraction(1))},
                    {
                        "name": "terminal_clear",
                        "value": fraction_to_json(Fraction(1)),
                    },
                ),
                "feature_caps": (match_cap, terminal_clear_cap),
            },
            {
                "proof_id": "lmb.match_only.matches_le_n_over_3.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {"name": "match", "value": fraction_to_json(Fraction(1))},
                    {
                        "name": "terminal_clear",
                        "value": fraction_to_json(Fraction(0)),
                    },
                ),
                "feature_caps": (match_cap,),
            },
            {
                "proof_id": "lmb.terminal_clear_only.clear_bonus.v1",
                "kind": "nonnegative_feature_caps_v1",
                "reward_basis": (
                    {"name": "match", "value": fraction_to_json(Fraction(0))},
                    {
                        "name": "terminal_clear",
                        "value": fraction_to_json(Fraction(1)),
                    },
                ),
                "feature_caps": (terminal_clear_cap,),
            },
        )
    else:
        raise Phase3BInvariantViolation(
            "Phase3B has no portable normalizer rule for this reward registry"
        )
    return build_portable_rapm(
        behavioural.quotient_models,
        state_ids=lambda state: object_id(state, "state"),
        semantic_action_ids=lambda action: object_id(action, "semantic-source"),
        ground_action_ids=lambda action: object_id(action, "ground-action-source"),
        normalizer_rules=normalizer_rules,
        state_kinds=lambda state: (
            "failure"
            if state in failures
            else "terminal"
            if kernel.is_terminal(state)
            else "active"
        ),
        goal_ids=tuple(kernel.registered_goals),
        coverage={
            "mode": coverage.mode,
            "declared_support_set_sha256": coverage.declared_support_set_sha256,
            "declared_support_state_ids": coverage.declared_support_state_ids,
            "covered_state_ids": coverage.covered_state_ids,
            "exact_state_cap": coverage.exact_state_cap,
            "admissible_query_support_rule": coverage.admissible_query_support_rule,
            "reuse_outside_coverage_forbidden": (
                coverage.reuse_outside_coverage_forbidden
            ),
        },
    )


def _construct_domains() -> tuple[DomainWorldModel, DomainWorldModel]:
    g2048_kernel, _ = safe_chain_fixture()
    g_train, g_heldout = _g2048_query_suite()
    g_coverage = SuiteBuildCoverage.from_queries(
        g2048_kernel,
        tuple(named.query for named in g_train),
        state_cap=STATE_CAP,
    )
    for named in g_train + g_heldout:
        g_coverage.validate_query_coverage(named.query)
    g_behavioural = build_exact_behavioral_quotient(
        g2048_kernel, g_coverage.covered_states
    )
    if len(g_coverage.covered_states) != 192 or g_behavioural.cell_count != 10:
        raise Phase3BInvariantViolation("G2048 behavioural 192-to-10 golden changed")
    g_ground_pairs = sum(
        len(g2048_kernel.actions(state))
        for state in g_coverage.covered_states
        if not g2048_kernel.is_terminal(state)
    )
    if len(g_behavioural.quotient_models.nominal.entries) >= g_ground_pairs:
        raise Phase3BInvariantViolation("G2048 state-action compression is not strict")
    g_structural_id = object_id(g2048_kernel.structural_key(), "structural")

    lmb_kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    l_train, l_extra = _lmb_campaign_queries(lmb_kernel)
    l_campaign = l_train + l_extra
    l_coverage = SuiteBuildCoverage.from_queries(
        lmb_kernel,
        tuple(named.query for named in l_train),
        state_cap=STATE_CAP,
    )
    for named in l_campaign:
        l_coverage.validate_query_coverage(named.query)
    l_behavioural = build_exact_behavioral_quotient(
        lmb_kernel, l_coverage.covered_states
    )
    if len(l_coverage.covered_states) != 25 or l_behavioural.cell_count != 5:
        raise Phase3BInvariantViolation("LMB behavioural 25-to-5 golden changed")
    l_ground_pairs = sum(
        len(lmb_kernel.actions(state))
        for state in l_coverage.covered_states
        if not lmb_kernel.is_terminal(state)
    )
    if len(l_behavioural.quotient_models.nominal.entries) >= l_ground_pairs:
        raise Phase3BInvariantViolation("LMB state-action compression is not strict")
    l_structural_payload = {
        "fixture_key": "lmb_generated_n6_t2_k3_d2_seed0_v0",
        "tile_types": lmb_kernel.tile_types,
        "blockers": lmb_kernel.blockers,
        "type_count": lmb_kernel.type_count,
        "capacity": lmb_kernel.capacity,
        "max_layers": lmb_kernel.max_layers,
    }
    l_structural_id = object_id(l_structural_payload, "structural")

    g_model = DomainWorldModel(
        "g2048",
        g2048_kernel,
        g_structural_id,
        g_train,
        g_train + g_heldout,
        g_coverage,
        g_behavioural,
        _portable_build(g2048_kernel, g_behavioural, g_coverage),
    )
    l_model = DomainWorldModel(
        "lmb",
        lmb_kernel,
        l_structural_id,
        l_train,
        l_campaign,
        l_coverage,
        l_behavioural,
        _portable_build(lmb_kernel, l_behavioural, l_coverage),
    )
    return g_model, l_model


def _fresh_process_proposals(
    domains: tuple[DomainWorldModel, ...],
) -> tuple[PortableProposal, ...]:
    """Materialize every proposal before any J0 call is allowed to start."""

    proposals: list[PortableProposal] = []
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3b-") as temporary:
        root = Path(temporary)
        runtime_root = root / "runtime"
        runtime_package = runtime_root / "acfqp"
        model_root = root / "models"
        occurrence_root = root / "occurrences"
        runtime_package.mkdir(parents=True)
        model_root.mkdir()
        occurrence_root.mkdir()
        for module_name in ("portable.py", "portable_planner.py", "portable_runtime.py"):
            shutil.copy2(PROJECT_ROOT / "src" / "acfqp" / module_name, runtime_package)
        bubblewrap = shutil.which("bwrap")
        if bubblewrap is None:
            raise Phase3BInvariantViolation(
                "Phase3B requires bubblewrap for the closed portable-planner runtime"
            )
        model_paths: dict[str, Path] = {}
        for domain in domains:
            model_path = model_root / f"{domain.domain}.rapm.json"
            dump_model(domain.portable.model, model_path)
            loaded = load_model(model_path)
            if loaded.model_id != domain.portable.model.model_id:
                raise Phase3BInvariantViolation("portable RAPM round-trip changed model ID")
            model_paths[domain.domain] = model_path

        system_mounts: list[str] = []
        for system_path in ("/usr", "/lib", "/lib64"):
            if Path(system_path).exists():
                system_mounts.extend(("--ro-bind", system_path, system_path))
        ordinal = 0
        for domain in domains:
            for named in domain.campaign_queries:
                ordinal += 1
                portable_query = domain.portable.query_from_spec(named.query)
                occurrence = occurrence_root / f"occurrence-{ordinal:03d}"
                input_root = occurrence / "input"
                output_root = occurrence / "output"
                input_root.mkdir(parents=True)
                output_root.mkdir()
                query_path = input_root / "query.json"
                result_path = output_root / "result.json"
                attestation_path = output_root / "attestation.json"
                dump_query(portable_query, query_path)
                process = subprocess.Popen(
                    (
                        bubblewrap,
                        "--unshare-all",
                        "--die-with-parent",
                        "--new-session",
                        "--clearenv",
                        *system_mounts,
                        "--proc",
                        "/proc",
                        "--dev",
                        "/dev",
                        "--tmpfs",
                        "/tmp",
                        "--ro-bind",
                        str(runtime_root),
                        "/runtime",
                        "--dir",
                        "/input",
                        "--ro-bind",
                        str(model_paths[domain.domain]),
                        "/input/model.json",
                        "--ro-bind",
                        str(query_path),
                        "/input/query.json",
                        "--dir",
                        "/output",
                        "--bind",
                        str(output_root),
                        "/output",
                        "--chdir",
                        "/output",
                        "--setenv",
                        "PATH",
                        "/usr/bin:/bin",
                        "--setenv",
                        "PYTHONPATH",
                        "/runtime",
                        "--setenv",
                        "LANG",
                        "C.UTF-8",
                        "--setenv",
                        "ACFQP_FORBIDDEN_ROOTS",
                        str(PROJECT_ROOT),
                        sys.executable,
                        "-B",
                        "-S",
                        "-m",
                        "acfqp.portable_runtime",
                        "--model",
                        "/input/model.json",
                        "--query",
                        "/input/query.json",
                        "--output",
                        "/output/result.json",
                        "--attestation",
                        "/output/attestation.json",
                    ),
                    cwd=output_root,
                    env={"PATH": "/usr/bin:/bin"},
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    stdout, stderr = process.communicate(timeout=120)
                except subprocess.TimeoutExpired as error:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise Phase3BInvariantViolation(
                        "fresh portable planner timed out: "
                        f"query={named.query_key!r}, stdout={stdout!r}, "
                        f"stderr={stderr!r}"
                    ) from error
                if process.returncode != 0:
                    raise Phase3BInvariantViolation(
                        "fresh portable planner failed: "
                        f"query={named.query_key!r}, stdout={stdout!r}, stderr={stderr!r}"
                    )
                if stdout or stderr:
                    raise Phase3BInvariantViolation(
                        "fresh portable planner emitted unexpected output"
                    )
                result = load_result(
                    result_path,
                    model=domain.portable.model,
                    query=portable_query,
                )
                attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
                attestation_payload = dict(attestation)
                attestation_id = attestation_payload.pop("attestation_id", None)
                if attestation_id != logical_id(
                    "runtime-attestation", attestation_payload
                ):
                    raise Phase3BInvariantViolation(
                        "portable runtime attestation content ID mismatch"
                    )
                if (
                    attestation_payload.get("schema")
                    != "acfqp.portable_runtime_attestation.v1"
                    or attestation_payload.get("model_id")
                    != domain.portable.model.model_id
                    or attestation_payload.get("query_id") != portable_query.query_id
                    or attestation_payload.get("result_id") != result.result_id
                    or attestation_payload.get("model_sha256")
                    != sha256_file(model_paths[domain.domain])
                    or attestation_payload.get("query_sha256") != sha256_file(query_path)
                    or attestation_payload.get("output_sha256") != sha256_file(result_path)
                    or attestation_payload.get("project_checkout_visible") is not False
                    or attestation_payload.get("forbidden_modules_resolved") != []
                    or attestation_payload.get("input_regular_files")
                    != ["model.json", "query.json"]
                    or attestation_payload.get("output_regular_files_before") != []
                    or attestation_payload.get("python_site_disabled") is not True
                    or attestation_payload.get("network_namespace_unshared") is not True
                    or attestation_payload.get("unexpected_module_origins") != []
                    or attestation_payload.get("loaded_acfqp_modules")
                    != ["acfqp", "acfqp.portable", "acfqp.portable_planner"]
                    or attestation_payload.get("runtime_source_sha256")
                    != {
                        f"acfqp.{module_name[:-3]}": sha256_file(
                            PROJECT_ROOT / "src" / "acfqp" / module_name
                        )
                        for module_name in (
                            "portable.py",
                            "portable_planner.py",
                            "portable_runtime.py",
                        )
                    }
                ):
                    raise Phase3BInvariantViolation(
                        "portable runtime isolation attestation failed"
                    )
                if result.selected is None:
                    raise Phase3BInvariantViolation(
                        f"registered portable query is infeasible: {named.query_key}"
                    )
                proposals.append(
                    PortableProposal(
                        domain,
                        named,
                        object_id(named.query, "query"),
                        portable_query,
                        result,
                        process.pid,
                        attestation,
                    )
                )
    return tuple(proposals)


def _evaluate_after_proposal_freeze(
    proposals: tuple[PortableProposal, ...],
) -> tuple[CampaignEvaluation, ...]:
    evaluations: list[CampaignEvaluation] = []
    for proposal in proposals:
        domain = proposal.domain_model
        selected = proposal.result.selected
        if selected is None:  # guarded before crossing the evaluation boundary
            raise Phase3BInvariantViolation("portable proposal lost its selected point")
        abstract_policy = FiniteHorizonPolicy.from_mapping(
            domain.portable.decode_policy(selected.policy)
        )
        portable_audit = audit_exact_portable_policy(
            domain.portable.model,
            proposal.portable_query,
            selected.policy,
            regret_tolerance=Fraction(1, 20),
        )
        audit = audit_abstract_policy(
            domain.kernel,
            proposal.named_query.query,
            domain.behavioural.quotient_models.envelope,
            abstract_policy,
            regret_tolerance=Fraction(1, 20),
        )
        lift = lift_semantic_policy(
            domain.kernel,
            proposal.named_query.query,
            domain.behavioural.partition,
            abstract_policy,
            domain.portable.serialized_adapter(),
        )
        # J0 begins here, after all proposals for the complete ordered workload
        # have crossed the portable process boundary.
        ground = solve_ground_pareto(domain.kernel, proposal.named_query.query)
        if ground.selected is None:
            raise Phase3BInvariantViolation(
                f"registered campaign query is ground-infeasible: {proposal.named_query.query_key}"
            )
        if not audit.certified:
            raise Phase3BInvariantViolation(
                f"portable proposal failed exact audit: {proposal.named_query.query_key}"
            )
        if not portable_audit.certified:
            raise Phase3BInvariantViolation(
                "serialized portable envelope failed exact audit: "
                f"{proposal.named_query.query_key}"
            )
        ground_point = ground.selected
        lifted = lift.evaluation
        if (
            selected.expected_reward != ground_point.expected_reward
            or selected.failure_probability != ground_point.failure_probability
            or lifted.expected_reward != ground_point.expected_reward
            or lifted.failure_probability != ground_point.failure_probability
            or audit.lifted_reward_lower != ground_point.expected_reward
            or audit.lifted_failure_upper != ground_point.failure_probability
            or audit.regret_upper != 0
            or portable_audit.expected_reward != ground_point.expected_reward
            or portable_audit.failure_probability
            != ground_point.failure_probability
            or portable_audit.regret_upper != 0
        ):
            raise Phase3BInvariantViolation(
                f"portable/J0 exact preservation changed: {proposal.named_query.query_key}"
            )
        evaluations.append(
            CampaignEvaluation(
                proposal,
                abstract_policy,
                portable_audit,
                audit,
                lift,
                ground,
            )
        )
    return tuple(evaluations)


def compute_phase3b_campaign(
) -> tuple[tuple[DomainWorldModel, DomainWorldModel], tuple[CampaignEvaluation, ...]]:
    domains = _construct_domains()
    proposals = _fresh_process_proposals(domains)
    if len(proposals) != 11:
        raise Phase3BInvariantViolation("Phase3B campaign must contain eleven queries")
    evaluations = _evaluate_after_proposal_freeze(proposals)
    return domains, evaluations


def _build_epoch_document(domain: DomainWorldModel) -> dict[str, Any]:
    model_document = domain.portable.model.to_dict()
    coverage_id = domain.portable.model.coverage_id
    payload = {
        "domain": domain.domain,
        "structural_id": domain.structural_id,
        "coverage_id": coverage_id,
        "coverage": domain.coverage.descriptor(),
        "portable_rapm_id": domain.portable.model.model_id,
        "kernel_sha256": canonical_sha256(
            domain.kernel.structural_key()
            if hasattr(domain.kernel, "structural_key")
            else {
                "tile_types": domain.kernel.tile_types,
                "blockers": domain.kernel.blockers,
                "type_count": domain.kernel.type_count,
                "capacity": domain.kernel.capacity,
                "max_layers": domain.kernel.max_layers,
            }
        ),
        "partition_id": object_id(model_document["partition"], "partition"),
        "semantic_adapter_id": object_id(
            domain.behavioural.semantic_adapter.assignments,
            "semantic-adapter",
        ),
        "nominal_model_id": object_id(model_document["nominal"], "nominal"),
        "sound_envelope_id": object_id(model_document["envelope"], "envelope"),
        "concretizer_id": object_id(
            model_document["concretizer_registry"], "concretizer"
        ),
        "reward_terminal_registry_id": object_id(
            {
                "reward_features": model_document["reward_features"],
                "normalizer_rules": model_document["normalizer_rules"],
                "registered_goals": tuple(model_document["goal_ids"]),
                "failure_target_state_ids": tuple(
                    sorted(
                        object_id(state, "state")
                        for state in domain.behavioural.failure_targets
                    )
                ),
            },
            "reward-terminal-registry",
        ),
        "synthesizer_id": object_id(
            {
                "algorithm": "exact_one_step_behavioral_fixed_point",
                "refinement_cell_trace": tuple(
                    step.cell_count for step in domain.behavioural.refinement_trace
                ),
                "implementation_schema": "acfqp.behavioral.v1",
            },
            "synthesizer",
        ),
        "source_tree_sha256": _source_tree_hash(),
        "construction": "exact_one_step_behavioral_fixed_point",
        "construction_uses_q_or_value_signatures": False,
        "construction_uses_policy_signatures": False,
        "construction_uses_query_reward_risk_or_horizon": False,
        "heldout_results_used_for_construction": False,
        "covered_ground_states": len(domain.coverage.covered_states),
        "abstract_cells": domain.behavioural.cell_count,
        "abstract_state_action_pairs": len(
            domain.behavioural.quotient_models.nominal.entries
        ),
        "ground_state_action_pairs": sum(
            len(domain.kernel.actions(state))
            for state in domain.coverage.covered_states
            if not domain.kernel.is_terminal(state)
        ),
        "strict_state_action_compression": (
            len(domain.behavioural.quotient_models.nominal.entries)
            < sum(
                len(domain.kernel.actions(state))
                for state in domain.coverage.covered_states
                if not domain.kernel.is_terminal(state)
            )
        ),
        "refinement_cell_trace": tuple(
            step.cell_count for step in domain.behavioural.refinement_trace
        ),
        "portable_roundtrip_identity": True,
        "schema": "acfqp.build_epoch@phase3b.v1",
        "contract_version": CONTRACT_VERSION,
    }
    return {"build_epoch_id": object_id(payload, "build-epoch"), **payload}


def _query_record(evaluation: CampaignEvaluation) -> dict[str, Any]:
    proposal = evaluation.proposal
    return {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "split": proposal.named_query.split,
        "ground_query_id": proposal.ground_query_id,
        "ground_query": proposal.named_query.query,
        "portable_query_id": proposal.portable_query.query_id,
        "portable_model_id": proposal.portable_query.model_id,
        "horizon": proposal.named_query.query.horizon,
    }


def _portable_query_record(evaluation: CampaignEvaluation) -> dict[str, Any]:
    proposal = evaluation.proposal
    return {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "ground_query_id": proposal.ground_query_id,
        "portable_query": proposal.portable_query.to_dict(),
    }


def _portable_plan_record(evaluation: CampaignEvaluation) -> dict[str, Any]:
    proposal = evaluation.proposal
    return {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "ground_query_id": proposal.ground_query_id,
        "fresh_process": True,
        "process_id_observed_positive": proposal.process_id > 0,
        "runtime_attestation": proposal.runtime_attestation,
        "isolation_backend": "bubblewrap_mount_and_network_namespace",
        "filesystem_namespace_isolated": True,
        "project_checkout_visible_to_planner": False,
        "python_site_disabled": True,
        "planner_application_modules_observed": tuple(
            proposal.runtime_attestation["loaded_acfqp_modules"]
        ),
        "planner_unexpected_module_origins": tuple(
            proposal.runtime_attestation["unexpected_module_origins"]
        ),
        "ground_kernel_available_to_planner": False,
        "ground_j0_available_to_planner": False,
        "refiner_available_to_planner": False,
        "plan_result": proposal.result.to_dict(),
    }


def _policy_graph(evaluation: CampaignEvaluation) -> dict[str, Any]:
    proposal = evaluation.proposal
    selected = proposal.result.selected
    if selected is None:
        raise Phase3BInvariantViolation("policy graph requires a selected point")
    model_document = proposal.domain_model.portable.model.to_dict()
    transitions = {
        (entry["cell_id"], entry["action_id"]): entry["model"]
        for entry in model_document["nominal"]
    }
    nodes: list[dict[str, Any]] = []
    branch_count = 0
    for decision in selected.policy.decisions:
        transition = transitions[(decision.cell_id, decision.action_id)]
        successors = tuple(transition["successor_probabilities"])
        branch_count += int(len(successors) > 1)
        nodes.append(
            {
                "remaining": decision.remaining,
                "cell_id": decision.cell_id,
                "action_id": decision.action_id,
                "successors": successors,
                "failure_probability": transition["failure_probability"],
                "termination_probability": transition["termination_probability"],
            }
        )
    payload = {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "ground_query_id": proposal.ground_query_id,
        "portable_query_id": proposal.portable_query.query_id,
        "portable_model_id": proposal.portable_query.model_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "nodes": tuple(nodes),
        "decision_node_count": len(nodes),
        "stochastic_branch_node_count": branch_count,
    }
    return {"policy_graph_id": object_id(payload, "policy-graph"), **payload}


def _certificate(evaluation: CampaignEvaluation, policy_graph_id: str) -> dict[str, Any]:
    proposal = evaluation.proposal
    audit = evaluation.audit
    selected = proposal.result.selected
    if selected is None:
        raise Phase3BInvariantViolation("certificate requires a selected point")
    payload = {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "ground_query_id": proposal.ground_query_id,
        "portable_query_id": proposal.portable_query.query_id,
        "portable_model_id": proposal.portable_query.model_id,
        "portable_result_id": proposal.result.result_id,
        "policy_graph_id": policy_graph_id,
        "route": "ABSTRACT_CERTIFIED",
        "proposal_expected_reward": selected.expected_reward,
        "proposal_failure_probability": selected.failure_probability,
        "portable_envelope_reward": evaluation.portable_audit.expected_reward,
        "portable_envelope_failure": evaluation.portable_audit.failure_probability,
        "portable_envelope_regret_upper": evaluation.portable_audit.regret_upper,
        "portable_envelope_certified": evaluation.portable_audit.certified,
        "reward_lower": audit.lifted_reward_lower,
        "failure_upper": audit.lifted_failure_upper,
        "regret_upper": audit.regret_upper,
        "regret_tolerance": audit.regret_tolerance,
        "risk_tolerance": audit.risk_tolerance,
        "certified": audit.certified,
        "local_ground_nodes": (),
        "full_ground_fallback_invocations": 0,
    }
    return {"certificate_id": object_id(payload, "certificate"), **payload}


def _j0_row(evaluation: CampaignEvaluation, certificate_id: str) -> dict[str, Any]:
    proposal = evaluation.proposal
    selected = proposal.result.selected
    ground = evaluation.ground.selected
    if selected is None or ground is None:
        raise Phase3BInvariantViolation("evaluation row requires feasible policies")
    lifted = evaluation.lift.evaluation
    return {
        "domain": proposal.domain_model.domain,
        "query_key": proposal.named_query.query_key,
        "ground_query_id": proposal.ground_query_id,
        "portable_query_id": proposal.portable_query.query_id,
        "certificate_id": certificate_id,
        "j0_started_after_all_portable_proposals": True,
        "j0_dependency_role": "evaluation_only",
        "ground_expected_reward": ground.expected_reward,
        "ground_failure_probability": ground.failure_probability,
        "portable_expected_reward": selected.expected_reward,
        "portable_failure_probability": selected.failure_probability,
        "lifted_expected_reward": lifted.expected_reward,
        "lifted_failure_probability": lifted.failure_probability,
        "reward_gap": ground.expected_reward - lifted.expected_reward,
        "failure_gap": lifted.failure_probability - ground.failure_probability,
        "abstract_composed_candidate_count": proposal.result.composed_candidate_count,
        "ground_composed_candidate_count": evaluation.ground.composed_candidate_count,
    }


def build_phase3b_documents(
    domains: tuple[DomainWorldModel, DomainWorldModel],
    evaluations: tuple[CampaignEvaluation, ...],
    *,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    epochs = tuple(_build_epoch_document(domain) for domain in domains)
    query_records = tuple(_query_record(evaluation) for evaluation in evaluations)
    portable_queries = tuple(
        _portable_query_record(evaluation) for evaluation in evaluations
    )
    portable_plans = tuple(
        _portable_plan_record(evaluation) for evaluation in evaluations
    )
    graphs = tuple(_policy_graph(evaluation) for evaluation in evaluations)
    certificates = tuple(
        _certificate(evaluation, graph["policy_graph_id"])
        for evaluation, graph in zip(evaluations, graphs, strict=True)
    )
    j0_rows = tuple(
        _j0_row(evaluation, certificate["certificate_id"])
        for evaluation, certificate in zip(evaluations, certificates, strict=True)
    )

    if not any(graph["stochastic_branch_node_count"] > 0 for graph in graphs):
        raise Phase3BInvariantViolation("campaign lacks a contingent stochastic branch")
    if not all(certificate["certified"] for certificate in certificates):
        raise Phase3BInvariantViolation("campaign contains an uncertified query")

    unique_ground_queries = {record["ground_query_id"] for record in query_records}
    unique_portable_queries = {
        record["portable_query_id"] for record in query_records
    }
    per_domain_counts = {
        domain.domain: sum(
            record["domain"] == domain.domain for record in query_records
        )
        for domain in domains
    }
    per_domain_unique_portable = {
        domain.domain: len(
            {
                record["portable_query_id"]
                for record in query_records
                if record["domain"] == domain.domain
            }
        )
        for domain in domains
    }
    if (
        len(unique_ground_queries) != 11
        or len(unique_portable_queries) < 8
        or any(count < 4 for count in per_domain_counts.values())
        or any(count < 4 for count in per_domain_unique_portable.values())
    ):
        raise Phase3BInvariantViolation("registered repeated-query gate changed")

    workload_payload = {
        "profile_key": PROFILE_KEY,
        "build_epoch_ids": {
            epoch["domain"]: epoch["build_epoch_id"] for epoch in epochs
        },
        "domain_bindings": {
            domain.domain: {
                "structural_id": domain.structural_id,
                "build_epoch_id": next(
                    epoch["build_epoch_id"]
                    for epoch in epochs
                    if epoch["domain"] == domain.domain
                ),
                "portable_rapm_id": domain.portable.model.model_id,
                "coverage_id": domain.portable.model.coverage_id,
                "coverage_seed_ground_query_ids": tuple(
                    object_id(named.query, "query")
                    for named in domain.train_queries
                ),
            }
            for domain in domains
        },
        "ordered_ground_query_ids": tuple(
            record["ground_query_id"] for record in query_records
        ),
        "domain_order": tuple(domain.domain for domain in domains),
        "query_occurrence_count": len(query_records),
        "distinct_ground_query_count": len(unique_ground_queries),
        "distinct_portable_query_count": len(unique_portable_queries),
        "byte_equivalent_portable_projection_count": (
            len(query_records) - len(unique_portable_queries)
        ),
        "minimum_distinct_queries": 8,
        "minimum_queries_per_domain": 4,
        "coverage_rule": "positive_support_subset_of_frozen_suite_closure",
        "normalizer_proof_ids": tuple(
            sorted(
                {
                    evaluation.proposal.named_query.query.normalizer_proof_id
                    for evaluation in evaluations
                }
            )
        ),
        "registered_goal_ids": ("default",),
        "allowed_routes": (
            "ABSTRACT_CERTIFIED",
            "LOCAL_GROUND_RECOVERY",
            "FULL_GROUND_FALLBACK",
            "REBUILD_REQUIRED",
            "INFEASIBLE_QUERY",
        ),
        "normal_route": "ABSTRACT_CERTIFIED",
        "declared_later_routes": (
            "LOCAL_GROUND_RECOVERY",
            "FULL_GROUND_FALLBACK",
            "REBUILD_REQUIRED",
            "INFEASIBLE_QUERY",
        ),
        "build_before_evaluation": True,
        "all_portable_proposals_before_j0": True,
    }
    workload_spec = {
        "workload_id": object_id(workload_payload, "workload"),
        **workload_payload,
    }
    query_registry = {
        "construction_inputs": "train support union only",
        "query_values_used_for_construction": False,
        "heldout_results_used_for_construction": False,
        "records": query_records,
    }
    reuse = {
        "one_unchanged_model_per_domain": True,
        "model_ids": {
            domain.domain: domain.portable.model.model_id for domain in domains
        },
        "query_occurrence_count": len(query_records),
        "distinct_ground_query_count": len(unique_ground_queries),
        "distinct_portable_query_count": len(unique_portable_queries),
        "per_domain_query_counts": per_domain_counts,
        "per_domain_distinct_portable_query_counts": per_domain_unique_portable,
        "all_queries_in_coverage": True,
        "all_routes": tuple(certificate["route"] for certificate in certificates),
        "fresh_process_for_every_occurrence": True,
    }
    work_counters = {
        "cost_protocol_status": ECONOMICS_NOT_RUN,
        "scalar_break_even": None,
        "reason": (
            "Phase3B reports non-interchangeable exact work counters separately; "
            "no frozen scalar hardware/cost conversion is applied"
        ),
        "build": {
            domain.domain: {
                "covered_ground_states": len(domain.coverage.covered_states),
                "ground_state_action_pairs": sum(
                    len(domain.kernel.actions(state))
                    for state in domain.coverage.covered_states
                    if not domain.kernel.is_terminal(state)
                ),
                "ground_one_step_outcomes": sum(
                    len(domain.kernel.step(state, action))
                    for state in domain.coverage.covered_states
                    if not domain.kernel.is_terminal(state)
                    for action in domain.kernel.actions(state)
                ),
                "behavioral_refinement_rounds": (
                    len(domain.behavioural.refinement_trace) - 1
                ),
                "portable_model_bytes_canonical_json": len(
                    json.dumps(
                        domain.portable.model.to_dict(),
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ),
            }
            for domain in domains
        },
        "query": tuple(
            {
                "ground_query_id": row["ground_query_id"],
                "load": {
                    "portable_model_loads": 1,
                    "portable_query_loads": 1,
                    "portable_model_bytes": len(
                        json.dumps(
                            evaluation.proposal.domain_model.portable.model.to_dict(),
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ),
                    "portable_query_bytes": len(
                        json.dumps(
                            evaluation.proposal.portable_query.to_dict(),
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ),
                },
                "abstract_plan": {
                    "composed_candidate_count": row[
                        "abstract_composed_candidate_count"
                    ],
                    "pareto_frontier_points": len(
                        evaluation.proposal.result.frontier
                    ),
                    "selected_decision_nodes": len(
                        evaluation.proposal.result.selected.policy.decisions
                    )
                    if evaluation.proposal.result.selected is not None
                    else 0,
                },
                "portable_envelope_audit": {
                    "reachable_cell_horizon_pairs": (
                        evaluation.portable_audit.reachable_cell_horizon_pairs
                    ),
                },
                "ground_certificate_audit": {
                    "reachable_cell_horizon_pairs": len(
                        evaluation.audit.reachable_bounds
                    ),
                },
                "local_ground": {"candidate_count": 0},
                "full_fallback": {"invocation_count": 0, "candidate_count": 0},
                "evaluation_only_j0": {
                    "composed_candidate_count": row[
                        "ground_composed_candidate_count"
                    ]
                },
                "abstract_composed_candidate_count": row[
                    "abstract_composed_candidate_count"
                ],
                "audit_reachable_cell_horizon_pairs": len(
                    evaluation.audit.reachable_bounds
                ),
                "local_ground_candidate_count": 0,
                "full_fallback_candidate_count": 0,
                "evaluation_only_j0_composed_candidate_count": row[
                    "ground_composed_candidate_count"
                ],
            }
            for row, evaluation in zip(j0_rows, evaluations, strict=True)
        ),
    }
    work_counters["reconciliation"] = {
        "query_occurrence_count": len(work_counters["query"]),
        "portable_model_loads": sum(
            row["load"]["portable_model_loads"] for row in work_counters["query"]
        ),
        "portable_query_loads": sum(
            row["load"]["portable_query_loads"] for row in work_counters["query"]
        ),
        "abstract_composed_candidate_count": sum(
            row["abstract_plan"]["composed_candidate_count"]
            for row in work_counters["query"]
        ),
        "local_ground_candidate_count": sum(
            row["local_ground"]["candidate_count"] for row in work_counters["query"]
        ),
        "full_fallback_invocation_count": sum(
            row["full_fallback"]["invocation_count"]
            for row in work_counters["query"]
        ),
        "evaluation_only_j0_composed_candidate_count": sum(
            row["evaluation_only_j0"]["composed_candidate_count"]
            for row in work_counters["query"]
        ),
    }
    report_payload = {
        "profile_key": PROFILE_KEY,
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "local_hybrid_gate_status": LOCAL_HYBRID_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
        "query_occurrence_count": len(query_records),
        "distinct_ground_query_count": len(unique_ground_queries),
        "distinct_portable_query_count": len(unique_portable_queries),
        "all_queries_certified": True,
        "all_exact_reward_and_failure_gaps_zero": True,
        "fresh_process_planning": True,
        "q_value_signatures_used": False,
        "local_repair_exercised": False,
        "scalar_break_even_claimed": False,
    }
    report = {
        "report_id": object_id(report_payload, "phase3b-report"),
        **report_payload,
    }
    metrics = {
        "ground_states": {
            domain.domain: len(domain.coverage.covered_states) for domain in domains
        },
        "abstract_cells": {
            domain.domain: domain.behavioural.cell_count for domain in domains
        },
        "abstract_state_action_pairs": {
            domain.domain: len(domain.behavioural.quotient_models.nominal.entries)
            for domain in domains
        },
        "query_occurrences": len(query_records),
        "distinct_portable_queries": len(unique_portable_queries),
        "total_abstract_composed_candidates": sum(
            row["abstract_composed_candidate_count"] for row in j0_rows
        ),
        "evaluation_only_total_ground_composed_candidates": sum(
            row["ground_composed_candidate_count"] for row in j0_rows
        ),
        "certified_queries": sum(certificate["certified"] for certificate in certificates),
    }
    events = (
        {"sequence": 1, "event": "workload_registry_frozen"},
        {"sequence": 2, "event": "exact_behavioral_world_models_built"},
        {"sequence": 3, "event": "portable_roundtrip_verified"},
        {"sequence": 4, "event": "all_fresh_process_proposals_complete"},
        {"sequence": 5, "event": "evaluation_only_j0_started"},
        {"sequence": 6, "event": "independent_exact_audits_complete"},
        {"sequence": 7, "event": SLICE_PASS},
        {"sequence": 8, "event": FULL_PHASE3_NOT_RUN},
        {"sequence": 9, "event": LOCAL_HYBRID_NOT_RUN},
        {"sequence": 10, "event": ECONOMICS_NOT_RUN},
    )

    stable_documents: dict[str, Any] = {
        "workload/spec.json": workload_spec,
        "workload/query_registry.json": query_registry,
        "build/epochs.json": {"epochs": epochs},
        "build/g2048/portable_rapm.json": domains[0].portable.model.to_dict(),
        "build/lmb/portable_rapm.json": domains[1].portable.model.to_dict(),
        "campaign/portable_queries.jsonl": portable_queries,
        "campaign/portable_plans.jsonl": portable_plans,
        "campaign/policy_graphs.json": {"policy_graphs": graphs},
        "audit/certificates.jsonl": certificates,
        "evaluation/j0_rows.jsonl": j0_rows,
        "evaluation/reuse.json": reuse,
        "accounting/work_counters.json": work_counters,
        "result/phase3b_report.json": report,
        "metrics.json": metrics,
        "events.jsonl": events,
    }
    semantic_hash = canonical_sha256(stable_documents)
    source_hash = _source_tree_hash()
    run_payload = {
        "schema_version": "phase3b.v1",
        "contract_version": CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "status": SLICE_PASS,
        "semantic_hash": semantic_hash,
        "source_tree_sha256": source_hash,
        "spec_hashes": _spec_hashes(),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    run = {
        "run_id": object_id(run_payload, "run"),
        **run_payload,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    return {"run.json": run, **stable_documents}


def run_phase3b(output_dir: Path) -> dict[str, Any]:
    started_at = _utc_now()
    domains, evaluations = compute_phase3b_campaign()
    documents = build_phase3b_documents(
        domains,
        evaluations,
        started_at=started_at,
        finished_at=_utc_now(),
    )
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        required_paths=PHASE3B_REQUIRED_PATHS,
    )
    failures = verify_artifact_bundle(output_dir)
    if failures:
        raise Phase3BInvariantViolation(
            "written Phase3B bundle failed integrity verification: "
            + "; ".join(failures)
        )
    run = documents["run.json"]
    return {
        "status": SLICE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "local_hybrid_gate_status": LOCAL_HYBRID_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "run_id": run["run_id"],
        "semantic_hash": run["semantic_hash"],
        "bundle_sha256": manifest["bundle_sha256"],
        "output_dir": str(output_dir),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the contract-0.7 portable RAPM repeated-planning campaign"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase3b"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        summary = run_phase3b(args.output)
    except Phase3BInvariantViolation as error:
        print(
            json.dumps(
                {"status": error.status, "detail": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONTRACT_VERSION",
    "ECONOMICS_NOT_RUN",
    "EXECUTION_PROFILE",
    "FULL_PHASE3_NOT_RUN",
    "INVARIANT_FAILURE",
    "LOCAL_HYBRID_NOT_RUN",
    "PROFILE_KEY",
    "SLICE_PASS",
    "Phase3BInvariantViolation",
    "build_phase3b_documents",
    "compute_phase3b_campaign",
    "run_phase3b",
]
