#!/usr/bin/env python3
"""Independently verify a contract-0.7 portable RAPM campaign bundle."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.artifacts import (  # noqa: E402
    PHASE3B_DOCUMENT_CONTRACTS,
    PHASE3B_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
)
from acfqp.abstraction import build_exact_behavioral_quotient  # noqa: E402
from acfqp.build_coverage import SuiteBuildCoverage  # noqa: E402
from acfqp.core import QuerySpec  # noqa: E402
from acfqp.domains import safe_chain_fixture  # noqa: E402
from acfqp.domains.matching_buffer import generate_solvable_lmb  # noqa: E402
from acfqp.phase3a import _g2048_query_suite, _lmb_query_suite  # noqa: E402
from acfqp.planning import (  # noqa: E402
    FiniteHorizonPolicy,
    audit_abstract_policy,
    lift_semantic_policy,
    solve_ground_pareto,
)
from acfqp.portable import (  # noqa: E402
    PortableQuery,
    PortableRAPM,
    build_portable_rapm,
    canonical_json as portable_canonical_json,
    dump_model,
    dump_query,
    fraction_from_json,
    fraction_to_json,
    logical_id,
)
from acfqp.portable_planner import (  # noqa: E402
    PortablePlanResult,
    audit_exact_portable_policy,
    solve_portable_pareto,
)


SLICE_PASS = "PHASE3B_PORTABLE_RAPM_PASS"
FULL_PHASE3_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"
LOCAL_HYBRID_NOT_RUN = "LOCAL_HYBRID_GATE_NOT_RUN"
ECONOMICS_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
PROFILE_KEY = "phase3b_portable_rapm_campaign_v0"
EXECUTION_PROFILE = "phase3b_portable_rapm_campaign"
CONTRACT_VERSION = "0.7.0"

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


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _source_tree_hash() -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for name in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = ROOT / name
        if path.is_file():
            paths.append(path)
    for path in sorted(set(paths)):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted((ROOT / "specs").glob("*.md"))
    }


_DYNAMIC_IMPORT_DEPENDENCY = "<dynamic-import>"
_DYNAMIC_MODULE_PREFIXES = (
    "importlib",
    "pkgutil",
    "runpy",
    "zipimport",
)
_DYNAMIC_BUILTIN_NAMES = {
    "__import__",
    "compile",
    "eval",
    "exec",
}
_DYNAMIC_ATTRIBUTE_NAMES = {
    "__import__",
    "exec_module",
    "find_spec",
    "import_module",
    "load_module",
    "module_from_spec",
    "spec_from_file_location",
}


def _import_dependencies(
    path: Path,
    *,
    module_name: str | None = None,
) -> set[str]:
    """Return conservative absolute import dependencies for a Python source file.

    Relative imports are resolved in the module's package, and direct uses of
    Python's dynamic import primitives are represented by a sentinel.  The
    audit is intentionally conservative: an imported attribute is also treated
    as a possible submodule so ``from . import oracle`` cannot hide a forbidden
    module dependency.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if module_name is None:
        try:
            relative = path.resolve().relative_to((ROOT / "src").resolve())
        except ValueError as error:
            raise ValueError(
                "module_name is required for sources outside the project src tree"
            ) from error
        module_parts = list(relative.with_suffix("").parts)
        if module_parts[-1] == "__init__":
            module_parts.pop()
        module_name = ".".join(module_parts)
    package = (
        module_name
        if path.name == "__init__.py"
        else module_name.rpartition(".")[0]
    )
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dependencies.add(alias.name)
                if alias.name.startswith(_DYNAMIC_MODULE_PREFIXES):
                    dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                if not package:
                    raise ValueError("relative import has no package context")
                module = importlib.util.resolve_name(
                    "." * node.level + module,
                    package,
                )
            dependencies.add(module)
            dependencies.update(
                f"{module}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            )
            if module.startswith(_DYNAMIC_MODULE_PREFIXES) or (
                module == "builtins"
                and any(alias.name in _DYNAMIC_BUILTIN_NAMES for alias in node.names)
            ):
                dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
        elif isinstance(node, ast.Call):
            function = node.func
            if (
                isinstance(function, ast.Name)
                and function.id in _DYNAMIC_BUILTIN_NAMES
            ):
                dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
            elif (
                isinstance(function, ast.Name)
                and function.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value
                in _DYNAMIC_BUILTIN_NAMES | _DYNAMIC_ATTRIBUTE_NAMES
            ):
                dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
        elif (
            isinstance(node, ast.Attribute)
            and node.attr in _DYNAMIC_BUILTIN_NAMES | _DYNAMIC_ATTRIBUTE_NAMES
        ):
            dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
        elif (
            isinstance(node, ast.Constant)
            and node.value in _DYNAMIC_BUILTIN_NAMES | _DYNAMIC_ATTRIBUTE_NAMES
        ):
            # Conservatively catches dictionary/getattr indirection such as
            # ``__builtins__["__import__"]``.  The audited modules have no
            # legitimate reason to name these primitives in executable code.
            dependencies.add(_DYNAMIC_IMPORT_DEPENDENCY)
    return dependencies


def _isolated_portable_replay(
    model: PortableRAPM,
    query: PortableQuery,
) -> tuple[PortablePlanResult, dict[str, Any]]:
    """Replay one occurrence in a fresh closed bubblewrap namespace."""

    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise ValueError("independent Phase3B verification requires bubblewrap")
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3b-verify-") as temporary:
        root = Path(temporary)
        runtime_package = root / "runtime" / "acfqp"
        input_root = root / "input"
        output_root = root / "output"
        runtime_package.mkdir(parents=True)
        input_root.mkdir()
        output_root.mkdir()
        for module_name in ("portable.py", "portable_planner.py", "portable_runtime.py"):
            shutil.copy2(ROOT / "src" / "acfqp" / module_name, runtime_package)
        model_path = input_root / "model.json"
        query_path = input_root / "query.json"
        result_path = output_root / "result.json"
        attestation_path = output_root / "attestation.json"
        dump_model(model, model_path)
        dump_query(query, query_path)
        system_mounts: list[str] = []
        for system_path in ("/usr", "/lib", "/lib64"):
            if Path(system_path).exists():
                system_mounts.extend(("--ro-bind", system_path, system_path))
        try:
            process = subprocess.run(
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
                    str(root / "runtime"),
                    "/runtime",
                    "--dir",
                    "/input",
                    "--ro-bind",
                    str(model_path),
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
                    str(ROOT),
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
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError(f"independent portable sandbox failed: {error}") from error
        if process.returncode != 0 or process.stdout or process.stderr:
            raise ValueError(
                "independent portable sandbox returned unexpected process output: "
                f"code={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        try:
            result_document = _load(result_path)
            attestation = _load(attestation_path)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise ValueError(
                f"independent portable sandbox emitted invalid artifacts: {error}"
            ) from error
        return (
            PortablePlanResult.from_dict(result_document, model=model, query=query),
            attestation,
        )


def _lmb_campaign_queries(kernel: Any) -> tuple[Any, ...]:
    """Recreate the registered LMB campaign without importing its producer."""

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
    named_type = type(train[0])
    return train + heldout + (
        named_type("lmb.alias9.canonical.h3.delta10", "campaign", delta_ten),
        named_type("lmb.alias9.terminal_clear_only.h3", "campaign", terminal_only),
    )


def _normalizer_rules(domain: str, kernel: Any) -> tuple[dict[str, Any], ...]:
    if domain == "g2048":
        return (
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
    return (
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
@lru_cache(maxsize=1)
def _recompute_construction() -> dict[str, dict[str, Any]]:
    """Rebuild both query-value-free models without invoking J0 or a planner."""

    g_kernel, _ = safe_chain_fixture()
    g_train, g_heldout = _g2048_query_suite()
    g_coverage = SuiteBuildCoverage.from_queries(
        g_kernel, tuple(named.query for named in g_train), state_cap=50_000
    )

    l_kernel, _ = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=2,
        seed=0,
    )
    l_train, _ = _lmb_query_suite(l_kernel)
    l_coverage = SuiteBuildCoverage.from_queries(
        l_kernel, tuple(named.query for named in l_train), state_cap=50_000
    )

    result: dict[str, dict[str, Any]] = {}
    for domain, kernel, coverage, train_queries, campaign_queries in (
        ("g2048", g_kernel, g_coverage, g_train, g_train + g_heldout),
        (
            "lmb",
            l_kernel,
            l_coverage,
            l_train,
            _lmb_campaign_queries(l_kernel),
        ),
    ):
        behavioural = build_exact_behavioral_quotient(
            kernel, coverage.covered_states
        )
        failure_targets = set(behavioural.failure_targets)
        portable_build = build_portable_rapm(
            behavioural.quotient_models,
            state_ids=lambda state: object_id(state, "state"),
            semantic_action_ids=lambda action: object_id(action, "semantic-source"),
            ground_action_ids=lambda action: object_id(action, "ground-action-source"),
            normalizer_rules=_normalizer_rules(domain, kernel),
            state_kinds=lambda state: (
                "failure"
                if state in failure_targets
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
                "admissible_query_support_rule": (
                    coverage.admissible_query_support_rule
                ),
                "reuse_outside_coverage_forbidden": (
                    coverage.reuse_outside_coverage_forbidden
                ),
            },
        )
        portable = portable_build.model
        model_document = portable.to_dict()
        kernel_payload = (
            kernel.structural_key()
            if hasattr(kernel, "structural_key")
            else {
                "tile_types": kernel.tile_types,
                "blockers": kernel.blockers,
                "type_count": kernel.type_count,
                "capacity": kernel.capacity,
                "max_layers": kernel.max_layers,
            }
        )
        ground_pairs = sum(
            len(kernel.actions(state))
            for state in coverage.covered_states
            if not kernel.is_terminal(state)
        )
        result[domain] = {
            "kernel": kernel,
            "coverage": coverage,
            "behavioural": behavioural,
            "portable_build": portable_build,
            "train_queries": train_queries,
            "campaign_queries": campaign_queries,
            "model": portable,
            "structural_id": object_id(
                kernel.structural_key()
                if hasattr(kernel, "structural_key")
                else {
                    "fixture_key": "lmb_generated_n6_t2_k3_d2_seed0_v0",
                    "tile_types": kernel.tile_types,
                    "blockers": kernel.blockers,
                    "type_count": kernel.type_count,
                    "capacity": kernel.capacity,
                    "max_layers": kernel.max_layers,
                },
                "structural",
            ),
            "coverage_id": portable.coverage_id,
            "kernel_sha256": canonical_sha256(kernel_payload),
            "partition_id": object_id(model_document["partition"], "partition"),
            "semantic_adapter_id": object_id(
                behavioural.semantic_adapter.assignments, "semantic-adapter"
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
                    "registered_goals": tuple(kernel.registered_goals),
                    "failure_target_state_ids": tuple(
                        sorted(
                            object_id(state, "state")
                            for state in behavioural.failure_targets
                        )
                    ),
                },
                "reward-terminal-registry",
            ),
            "synthesizer_id": object_id(
                {
                    "algorithm": "exact_one_step_behavioral_fixed_point",
                    "refinement_cell_trace": tuple(
                        step.cell_count for step in behavioural.refinement_trace
                    ),
                    "implementation_schema": "acfqp.behavioral.v1",
                },
                "synthesizer",
            ),
            "refinement_cell_trace": [
                step.cell_count for step in behavioural.refinement_trace
            ],
            "covered_ground_states": len(coverage.covered_states),
            "abstract_cells": behavioural.cell_count,
            "ground_state_action_pairs": ground_pairs,
            "abstract_state_action_pairs": len(
                behavioural.quotient_models.nominal.entries
            ),
        }
    return result


def _expected_epoch(domain: str, replay: dict[str, Any]) -> dict[str, Any]:
    model_document = replay["model"].to_dict()
    coverage = replay["coverage"]
    payload = {
        "domain": domain,
        "structural_id": replay["structural_id"],
        "coverage_id": replay["coverage_id"],
        "coverage": coverage.descriptor(),
        "portable_rapm_id": replay["model"].model_id,
        "kernel_sha256": replay["kernel_sha256"],
        "partition_id": replay["partition_id"],
        "semantic_adapter_id": replay["semantic_adapter_id"],
        "nominal_model_id": replay["nominal_model_id"],
        "sound_envelope_id": replay["sound_envelope_id"],
        "concretizer_id": replay["concretizer_id"],
        "reward_terminal_registry_id": replay["reward_terminal_registry_id"],
        "synthesizer_id": replay["synthesizer_id"],
        "source_tree_sha256": _source_tree_hash(),
        "construction": "exact_one_step_behavioral_fixed_point",
        "construction_uses_q_or_value_signatures": False,
        "construction_uses_policy_signatures": False,
        "construction_uses_query_reward_risk_or_horizon": False,
        "heldout_results_used_for_construction": False,
        "covered_ground_states": replay["covered_ground_states"],
        "abstract_cells": replay["abstract_cells"],
        "abstract_state_action_pairs": replay["abstract_state_action_pairs"],
        "ground_state_action_pairs": replay["ground_state_action_pairs"],
        "strict_state_action_compression": True,
        "refinement_cell_trace": tuple(replay["refinement_cell_trace"]),
        "portable_roundtrip_identity": True,
        "schema": "acfqp.build_epoch@phase3b.v1",
        "contract_version": CONTRACT_VERSION,
    }
    return to_jsonable({"build_epoch_id": object_id(payload, "build-epoch"), **payload})


def _manual_authority_binding(
    domain: str,
    model: PortableRAPM,
    replay: dict[str, Any],
) -> tuple[str, ...]:
    """Bind serialized envelope/kappa to live authority without serializer reuse."""

    issues: list[str] = []
    document = model.to_dict()
    registry = replay["portable_build"].registry
    behavioural = replay["behavioural"]
    kernel = replay["kernel"]
    serialized_envelope = {
        (record["cell_id"], record["action_id"]): record
        for record in document["envelope"]
    }
    serialized_kappa = {
        (record["state_id"], record["action_id"]): record
        for record in document["concretizer_registry"]
    }
    expected_entry_keys: set[tuple[str, str]] = set()
    expected_kappa_keys: set[tuple[str, str]] = set()
    for entry in behavioural.quotient_models.envelope.entries:
        cell_id = registry.cell_id(entry.cell)
        action_id = registry.semantic_action_id(entry.cell, entry.action)
        entry_key = (cell_id, action_id)
        expected_entry_keys.add(entry_key)
        stored_entry = serialized_envelope.get(entry_key)
        if stored_entry is None:
            issues.append(f"{domain}: serialized envelope is missing {entry_key!r}")
            continue
        stored_realizations = {
            realization["state_id"]: realization
            for realization in stored_entry["realizations"]
        }
        expected_state_ids = {
            registry.state_id(realization.state) for realization in entry.realizations
        }
        if set(stored_realizations) != expected_state_ids:
            issues.append(
                f"{domain}: envelope realization state set differs at {entry_key!r}"
            )
        for realization in entry.realizations:
            state = realization.state
            state_id = registry.state_id(state)
            stored = stored_realizations.get(state_id)
            if stored is None:
                continue
            stored_rewards = tuple(
                (
                    item["name"],
                    fraction_from_json(item["value"], field="authority reward"),
                )
                for item in stored["reward_features"]
            )
            expected_rewards = tuple(sorted(realization.reward_features))
            stored_successors = {
                item["cell_id"]: fraction_from_json(
                    item["probability"], field="authority successor probability"
                )
                for item in stored["successor_probabilities"]
            }
            expected_successors = {
                registry.cell_id(successor): Fraction(probability)
                for successor, probability in realization.successor_probabilities
            }
            if (
                stored_rewards != expected_rewards
                or stored_successors != expected_successors
                or fraction_from_json(
                    stored["failure_probability"], field="authority failure probability"
                )
                != realization.failure_probability
                or fraction_from_json(
                    stored["termination_probability"],
                    field="authority termination probability",
                )
                != realization.termination_probability
            ):
                issues.append(
                    f"{domain}: serialized envelope payload differs at "
                    f"state={state_id!r}, action={action_id!r}"
                )

            kappa_key = (state_id, action_id)
            expected_kappa_keys.add(kappa_key)
            stored_support_record = serialized_kappa.get(kappa_key)
            if stored_support_record is None:
                issues.append(f"{domain}: serialized concretizer is missing {kappa_key!r}")
                continue
            raw_support = tuple(
                behavioural.semantic_adapter.concretize(kernel, state, entry.action)
            )
            if len({action for _, action in raw_support}) != len(raw_support):
                issues.append(
                    f"{domain}: live semantic adapter repeats a ground action at {kappa_key!r}"
                )
            expected_support: dict[str, Fraction] = {}
            for probability, ground_action in raw_support:
                ground_id = registry.ground_action_id(state, ground_action)
                expected_support[ground_id] = expected_support.get(
                    ground_id, Fraction(0)
                ) + Fraction(probability)
            stored_support = {
                item["ground_action_id"]: fraction_from_json(
                    item["probability"], field="authority concretizer probability"
                )
                for item in stored_support_record["support"]
            }
            if (
                stored_support_record["cell_id"] != cell_id
                or stored_support != expected_support
                or sum(expected_support.values(), Fraction(0)) != 1
            ):
                issues.append(
                    f"{domain}: serialized concretizer differs from authority at {kappa_key!r}"
                )
    if set(serialized_envelope) != expected_entry_keys:
        issues.append(f"{domain}: serialized envelope entry key set differs from authority")
    if set(serialized_kappa) != expected_kappa_keys:
        issues.append(f"{domain}: serialized concretizer key set differs from authority")
    return tuple(issues)


def _expected_query_record(domain: str, named: Any, replay: dict[str, Any]) -> dict[str, Any]:
    portable_query = replay["portable_build"].query_from_spec(named.query)
    return to_jsonable(
        {
            "domain": domain,
            "query_key": named.query_key,
            "split": named.split,
            "ground_query_id": object_id(named.query, "query"),
            "ground_query": named.query,
            "portable_query_id": portable_query.query_id,
            "portable_model_id": portable_query.model_id,
            "horizon": named.query.horizon,
        }
    )


def _expected_policy_graph(
    domain: str,
    named: Any,
    ground_query_id: str,
    query: PortableQuery,
    result: PortablePlanResult,
    model: PortableRAPM,
) -> dict[str, Any]:
    selected = result.selected
    if selected is None:
        raise ValueError("registered campaign plan is infeasible")
    transitions = {
        (entry["cell_id"], entry["action_id"]): entry["model"]
        for entry in model.to_dict()["nominal"]
    }
    nodes: list[dict[str, Any]] = []
    branch_count = 0
    for decision in selected.policy.decisions:
        transition = transitions[(decision.cell_id, decision.action_id)]
        successors = transition["successor_probabilities"]
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
        "domain": domain,
        "query_key": named.query_key,
        "ground_query_id": ground_query_id,
        "portable_query_id": query.query_id,
        "portable_model_id": query.model_id,
        "selector_class": "deterministic_finite_horizon_markov",
        "nodes": tuple(nodes),
        "decision_node_count": len(nodes),
        "stochastic_branch_node_count": branch_count,
    }
    return to_jsonable(
        {"policy_graph_id": object_id(payload, "policy-graph"), **payload}
    )


_GROUND_EVALUATION_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}


def _independent_ground_evaluation(
    replay: dict[str, Any], named: Any, result: PortablePlanResult
) -> dict[str, Any]:
    cache_key = (
        replay["model"].model_id,
        object_id(named.query, "query"),
        result.result_id,
    )
    cached = _GROUND_EVALUATION_CACHE.get(cache_key)
    if cached is not None:
        return cached
    selected = result.selected
    if selected is None:
        raise ValueError("registered portable result has no selected policy")
    abstract_policy = FiniteHorizonPolicy.from_mapping(
        replay["portable_build"].decode_policy(selected.policy)
    )
    portable_audit = audit_exact_portable_policy(
        replay["model"],
        replay["portable_build"].query_from_spec(named.query),
        selected.policy,
        regret_tolerance=Fraction(1, 20),
    )
    audit = audit_abstract_policy(
        replay["kernel"],
        named.query,
        replay["behavioural"].quotient_models.envelope,
        abstract_policy,
        regret_tolerance=Fraction(1, 20),
    )
    lift = lift_semantic_policy(
        replay["kernel"],
        named.query,
        replay["behavioural"].partition,
        abstract_policy,
        replay["portable_build"].serialized_adapter(),
    )
    ground = solve_ground_pareto(replay["kernel"], named.query)
    if ground.selected is None:
        raise ValueError("registered ground query is infeasible")
    evaluation = {
        "selected": selected,
        "abstract_policy": abstract_policy,
        "portable_audit": portable_audit,
        "audit": audit,
        "lift": lift,
        "ground": ground,
    }
    _GROUND_EVALUATION_CACHE[cache_key] = evaluation
    return evaluation


def _expected_certificate(
    domain: str,
    named: Any,
    ground_query_id: str,
    query: PortableQuery,
    result: PortablePlanResult,
    policy_graph_id: str,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    selected = evaluation["selected"]
    audit = evaluation["audit"]
    portable_audit = evaluation["portable_audit"]
    payload = {
        "domain": domain,
        "query_key": named.query_key,
        "ground_query_id": ground_query_id,
        "portable_query_id": query.query_id,
        "portable_model_id": query.model_id,
        "portable_result_id": result.result_id,
        "policy_graph_id": policy_graph_id,
        "route": "ABSTRACT_CERTIFIED",
        "proposal_expected_reward": selected.expected_reward,
        "proposal_failure_probability": selected.failure_probability,
        "portable_envelope_reward": portable_audit.expected_reward,
        "portable_envelope_failure": portable_audit.failure_probability,
        "portable_envelope_regret_upper": portable_audit.regret_upper,
        "portable_envelope_certified": portable_audit.certified,
        "reward_lower": audit.lifted_reward_lower,
        "failure_upper": audit.lifted_failure_upper,
        "regret_upper": audit.regret_upper,
        "regret_tolerance": audit.regret_tolerance,
        "risk_tolerance": audit.risk_tolerance,
        "certified": audit.certified,
        "local_ground_nodes": (),
        "full_ground_fallback_invocations": 0,
    }
    return to_jsonable({"certificate_id": object_id(payload, "certificate"), **payload})


def _expected_j0_row(
    domain: str,
    named: Any,
    ground_query_id: str,
    query: PortableQuery,
    result: PortablePlanResult,
    certificate_id: str,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    selected = evaluation["selected"]
    ground = evaluation["ground"].selected
    lifted = evaluation["lift"].evaluation
    if ground is None:
        raise ValueError("registered ground result has no selected policy")
    return to_jsonable(
        {
            "domain": domain,
            "query_key": named.query_key,
            "ground_query_id": ground_query_id,
            "portable_query_id": query.query_id,
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
            "abstract_composed_candidate_count": result.composed_candidate_count,
            "ground_composed_candidate_count": evaluation[
                "ground"
            ].composed_candidate_count,
        }
    )


def verify_phase3b(bundle: Path) -> dict[str, Any]:
    """Verify integrity plus every semantic claim against an independent replay."""

    failures = list(verify_artifact_bundle(bundle))
    recomputed_semantic_hash: str | None = None
    run: dict[str, Any] = {}
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        return {"verified": False, "failures": tuple(failures)}

    try:
        manifest = _load(manifest_path)
        if set(manifest) != {
            "schema",
            "schema_version",
            "required_paths",
            "files",
            "bundle_sha256",
        }:
            failures.append("Phase3B manifest field set mismatch")
        if (
            manifest.get("schema") != "acfqp.manifest@phase05.v1"
            or manifest.get("schema_version") != "phase05.v1"
        ):
            failures.append("Phase3B manifest schema mismatch")
        records = {
            record["path"]: record
            for record in manifest.get("files", [])
            if isinstance(record, dict) and isinstance(record.get("path"), str)
        }
        if set(manifest.get("required_paths", ())) != set(PHASE3B_REQUIRED_PATHS):
            failures.append("Phase3B required-path set mismatch")
        if set(records) != set(PHASE3B_REQUIRED_PATHS):
            failures.append("Phase3B manifest contains a wrong document set")
        for path, (role, schema) in PHASE3B_DOCUMENT_CONTRACTS.items():
            record = records.get(path)
            if record is not None and (
                record.get("role") != role or record.get("schema") != schema
            ):
                failures.append(f"Phase3B role/schema mismatch: {path}")

        run = _load(bundle / "run.json")
        workload = _load(bundle / "workload/spec.json")
        registry = _load(bundle / "workload/query_registry.json")
        epochs = _load(bundle / "build/epochs.json")
        report = _load(bundle / "result/phase3b_report.json")
        reuse = _load(bundle / "evaluation/reuse.json")
        accounting = _load(bundle / "accounting/work_counters.json")
        metrics = _load(bundle / "metrics.json")
        events = _load_jsonl(bundle / "events.jsonl")
        portable_query_rows = _load_jsonl(
            bundle / "campaign/portable_queries.jsonl"
        )
        portable_plan_rows = _load_jsonl(
            bundle / "campaign/portable_plans.jsonl"
        )
        certificates = _load_jsonl(bundle / "audit/certificates.jsonl")
        j0_rows = _load_jsonl(bundle / "evaluation/j0_rows.jsonl")
        graphs_document = _load(bundle / "campaign/policy_graphs.json")
        graph_rows = (
            graphs_document.get("policy_graphs", [])
            if isinstance(graphs_document, dict)
            else []
        )
        if set(graphs_document) != {"policy_graphs"}:
            failures.append("policy graph document field set mismatch")

        models: dict[str, PortableRAPM] = {}
        for domain in ("g2048", "lmb"):
            model = PortableRAPM.from_dict(
                _load(bundle / f"build/{domain}/portable_rapm.json")
            )
            if model.model_id != model.recompute_model_id():
                failures.append(f"portable model ID does not recompute: {domain}")
            models[domain] = model

        planner_dependencies = _import_dependencies(
            ROOT / "src/acfqp/portable_planner.py"
        )
        forbidden_planner_prefixes = (
            "acfqp.domains",
            "acfqp.planning",
            "acfqp.refinement",
            "acfqp.abstraction",
        )
        forbidden = sorted(
            dependency
            for dependency in planner_dependencies
            if dependency == _DYNAMIC_IMPORT_DEPENDENCY
            or dependency.startswith(forbidden_planner_prefixes)
        )
        if forbidden:
            failures.append(
                "portable planner imports forbidden ground/build dependencies: "
                f"{forbidden!r}"
            )
        behavioural_dependencies = _import_dependencies(
            ROOT / "src/acfqp/abstraction/behavioral.py"
        )
        forbidden = sorted(
            dependency
            for dependency in behavioural_dependencies
            if dependency == _DYNAMIC_IMPORT_DEPENDENCY
            or dependency.startswith(
                (
                    "acfqp.abstraction.oracle",
                    "acfqp.planning.ground",
                    "acfqp.refinement",
                )
            )
        )
        if forbidden:
            failures.append(
                "behavioural synthesizer imports forbidden Q/value/refinement dependencies: "
                f"{forbidden!r}"
            )

        replayed = _recompute_construction()
        expected_epochs = {
            domain: _expected_epoch(domain, replayed[domain])
            for domain in ("g2048", "lmb")
        }
        expected_epochs_document = {
            "epochs": [expected_epochs["g2048"], expected_epochs["lmb"]]
        }
        if epochs != expected_epochs_document:
            failures.append("build epochs/content IDs differ from independent rebuild")
        for domain in ("g2048", "lmb"):
            replay = replayed[domain]
            if models[domain].to_dict() != replay["model"].to_dict():
                failures.append(f"independent behavioural rebuild changed model: {domain}")
            failures.extend(
                _manual_authority_binding(domain, models[domain], replay)
            )
            if not (
                replay["abstract_cells"] < replay["covered_ground_states"]
                and replay["abstract_state_action_pairs"]
                < replay["ground_state_action_pairs"]
            ):
                failures.append(f"recomputed compression Gate failed: {domain}")

        expected_campaign = tuple(
            (domain, named, replayed[domain])
            for domain in ("g2048", "lmb")
            for named in replayed[domain]["campaign_queries"]
        )
        expected_query_records = tuple(
            _expected_query_record(domain, named, replay)
            for domain, named, replay in expected_campaign
        )
        expected_registry = to_jsonable(
            {
                "construction_inputs": "train support union only",
                "query_values_used_for_construction": False,
                "heldout_results_used_for_construction": False,
                "records": expected_query_records,
            }
        )
        if registry != expected_registry:
            failures.append("ground query registry differs from independent reconstruction")
        registry_records = registry.get("records", [])
        ground_ids = [
            record.get("ground_query_id")
            for record in registry_records
            if isinstance(record, dict)
        ]
        if len(ground_ids) != len(set(ground_ids)):
            failures.append("ground query IDs are not unique")
        for record in registry_records:
            if isinstance(record, dict) and record.get("ground_query_id") != object_id(
                record.get("ground_query"), "query"
            ):
                failures.append(
                    f"ground query content ID mismatch: {record.get('query_key')}"
                )

        row_groups = (
            registry_records,
            portable_query_rows,
            portable_plan_rows,
            graph_rows,
            certificates,
            j0_rows,
        )
        if any(not isinstance(rows, list) for rows in row_groups) or any(
            len(rows) != 11 for rows in row_groups
        ):
            failures.append("Phase3B ordered campaign row counts differ from eleven")

        verified_rows: list[dict[str, Any]] = []
        comparable_count = min(
            (len(rows) for rows in row_groups if isinstance(rows, list)),
            default=0,
        )
        for index in range(min(len(expected_campaign), comparable_count)):
            domain, named, replay = expected_campaign[index]
            ground_id = object_id(named.query, "query")
            expected_query = replay["portable_build"].query_from_spec(named.query)
            expected_query_row = {
                "domain": domain,
                "query_key": named.query_key,
                "ground_query_id": ground_id,
                "portable_query": expected_query.to_dict(),
            }
            query_row = portable_query_rows[index]
            if query_row != expected_query_row:
                failures.append(
                    f"portable projection is not bound to ground query: {named.query_key}"
                )
            try:
                query = PortableQuery.from_dict(
                    query_row["portable_query"], models[domain]
                )
                if query.to_dict() != expected_query.to_dict():
                    failures.append(
                        f"portable query reconstruction mismatch: {named.query_key}"
                    )
                plan_row = portable_plan_rows[index]
                result = PortablePlanResult.from_dict(
                    plan_row["plan_result"], model=models[domain], query=query
                )
                portable_replay = solve_portable_pareto(models[domain], query)
                if portable_replay.to_dict() != result.to_dict():
                    failures.append(f"portable plan replay mismatch: {named.query_key}")
                expected_plan_row_fields = {
                    "domain",
                    "query_key",
                    "ground_query_id",
                    "fresh_process",
                    "process_id_observed_positive",
                    "runtime_attestation",
                    "isolation_backend",
                    "filesystem_namespace_isolated",
                    "project_checkout_visible_to_planner",
                    "python_site_disabled",
                    "planner_application_modules_observed",
                    "planner_unexpected_module_origins",
                    "ground_kernel_available_to_planner",
                    "ground_j0_available_to_planner",
                    "refiner_available_to_planner",
                    "plan_result",
                }
                if set(plan_row) != expected_plan_row_fields:
                    failures.append(
                        f"portable plan wrapper field set mismatch: {named.query_key}"
                    )
                expected_plan_fields = {
                    "domain": domain,
                    "query_key": named.query_key,
                    "ground_query_id": ground_id,
                    "fresh_process": True,
                    "process_id_observed_positive": True,
                    "ground_kernel_available_to_planner": False,
                    "ground_j0_available_to_planner": False,
                    "refiner_available_to_planner": False,
                    "plan_result": result.to_dict(),
                }
                if any(
                    plan_row.get(field) != value
                    for field, value in expected_plan_fields.items()
                ):
                    failures.append(
                        f"portable plan wrapper/isolation mismatch: {named.query_key}"
                    )
                attestation = plan_row.get("runtime_attestation")
                if not isinstance(attestation, dict):
                    failures.append(
                        f"runtime isolation attestation missing: {named.query_key}"
                    )
                else:
                    attestation_payload = dict(attestation)
                    attestation_id = attestation_payload.pop("attestation_id", None)
                    expected_attestation_fields = {
                        "schema",
                        "isolation_backend",
                        "python_site_disabled",
                        "project_checkout_visible",
                        "network_namespace_unshared",
                        "forbidden_modules_resolved",
                        "input_regular_files",
                        "output_regular_files_before",
                        "loaded_acfqp_modules",
                        "loaded_module_origins",
                        "unexpected_module_origins",
                        "runtime_source_sha256",
                        "model_sha256",
                        "query_sha256",
                        "output_sha256",
                        "model_id",
                        "query_id",
                        "result_id",
                    }
                    model_file_hash = hashlib.sha256(
                        (
                            portable_canonical_json(models[domain].to_dict()) + "\n"
                        ).encode("utf-8")
                    ).hexdigest()
                    query_file_hash = hashlib.sha256(
                        (
                            portable_canonical_json(query.to_dict()) + "\n"
                        ).encode("utf-8")
                    ).hexdigest()
                    result_file_hash = hashlib.sha256(
                        (
                            portable_canonical_json(result.to_dict()) + "\n"
                        ).encode("utf-8")
                    ).hexdigest()
                    if (
                        attestation_id
                        != logical_id("runtime-attestation", attestation_payload)
                        or attestation_payload.get("schema")
                        != "acfqp.portable_runtime_attestation.v1"
                        or attestation_payload.get("model_id") != models[domain].model_id
                        or attestation_payload.get("query_id") != query.query_id
                        or attestation_payload.get("result_id") != result.result_id
                        or attestation_payload.get("model_sha256") != model_file_hash
                        or attestation_payload.get("query_sha256") != query_file_hash
                        or attestation_payload.get("output_sha256") != result_file_hash
                        or attestation_payload.get("isolation_backend")
                        != "bubblewrap_mount_and_network_namespace"
                        or attestation_payload.get("python_site_disabled") is not True
                        or attestation_payload.get("project_checkout_visible") is not False
                        or attestation_payload.get("network_namespace_unshared") is not True
                        or attestation_payload.get("forbidden_modules_resolved") != []
                        or attestation_payload.get("input_regular_files")
                        != ["model.json", "query.json"]
                        or attestation_payload.get("output_regular_files_before") != []
                        or attestation_payload.get("loaded_acfqp_modules")
                        != ["acfqp", "acfqp.portable", "acfqp.portable_planner"]
                        or attestation_payload.get("unexpected_module_origins") != []
                        or attestation_payload.get("runtime_source_sha256")
                        != {
                            f"acfqp.{module_name.removesuffix('.py')}": sha256_file(
                                ROOT / "src" / "acfqp" / module_name
                            )
                            for module_name in (
                                "portable.py",
                                "portable_planner.py",
                                "portable_runtime.py",
                            )
                        }
                        or set(attestation_payload) != expected_attestation_fields
                    ):
                        failures.append(
                            f"runtime isolation attestation mismatch: {named.query_key}"
                        )
                    loaded_origins = attestation_payload.get("loaded_module_origins")
                    if (
                        not isinstance(loaded_origins, list)
                        or not loaded_origins
                        or any(
                            not isinstance(item, dict)
                            or set(item) != {"module", "origin"}
                            or not isinstance(item.get("module"), str)
                            or not isinstance(item.get("origin"), str)
                            or not item["origin"].startswith(("/usr/", "/runtime/"))
                            for item in loaded_origins
                        )
                    ):
                        failures.append(
                            f"runtime module-origin evidence mismatch: {named.query_key}"
                        )
                    if (
                        plan_row.get("isolation_backend")
                        != "bubblewrap_mount_and_network_namespace"
                        or plan_row.get("filesystem_namespace_isolated") is not True
                        or plan_row.get("project_checkout_visible_to_planner") is not False
                        or plan_row.get("python_site_disabled") is not True
                        or plan_row.get("planner_application_modules_observed")
                        != ["acfqp", "acfqp.portable", "acfqp.portable_planner"]
                        or plan_row.get("planner_unexpected_module_origins") != []
                    ):
                        failures.append(
                            f"portable runtime isolation wrapper mismatch: {named.query_key}"
                        )

                    isolated_result, isolated_attestation = _isolated_portable_replay(
                        models[domain], query
                    )
                    if isolated_result.to_dict() != result.to_dict():
                        failures.append(
                            f"fresh sandbox plan replay mismatch: {named.query_key}"
                        )
                    if isolated_attestation != attestation:
                        failures.append(
                            f"fresh sandbox attestation replay mismatch: {named.query_key}"
                        )

                evaluation = _independent_ground_evaluation(replay, named, result)
                selected = evaluation["selected"]
                audit = evaluation["audit"]
                portable_audit = evaluation["portable_audit"]
                lifted = evaluation["lift"].evaluation
                ground_selected = evaluation["ground"].selected
                if ground_selected is None or not (
                    audit.certified
                    and portable_audit.certified
                    and selected.expected_reward == ground_selected.expected_reward
                    and selected.failure_probability
                    == ground_selected.failure_probability
                    and lifted.expected_reward == ground_selected.expected_reward
                    and lifted.failure_probability
                    == ground_selected.failure_probability
                    and audit.lifted_reward_lower == ground_selected.expected_reward
                    and audit.lifted_failure_upper
                    == ground_selected.failure_probability
                    and audit.regret_upper == 0
                    and portable_audit.expected_reward
                    == ground_selected.expected_reward
                    and portable_audit.failure_probability
                    == ground_selected.failure_probability
                    and portable_audit.regret_upper == 0
                ):
                    failures.append(
                        f"independent lift/audit/J0 preservation failed: {named.query_key}"
                    )

                expected_graph = _expected_policy_graph(
                    domain, named, ground_id, query, result, models[domain]
                )
                if graph_rows[index] != expected_graph:
                    failures.append(
                        f"independently recomputed policy graph mismatch: {named.query_key}"
                    )
                expected_certificate = _expected_certificate(
                    domain,
                    named,
                    ground_id,
                    query,
                    result,
                    expected_graph["policy_graph_id"],
                    evaluation,
                )
                if certificates[index] != expected_certificate:
                    failures.append(
                        f"independently recomputed certificate mismatch: {named.query_key}"
                    )
                expected_j0 = _expected_j0_row(
                    domain,
                    named,
                    ground_id,
                    query,
                    result,
                    expected_certificate["certificate_id"],
                    evaluation,
                )
                if j0_rows[index] != expected_j0:
                    failures.append(
                        f"independently recomputed J0 row mismatch: {named.query_key}"
                    )
                verified_rows.append(
                    {
                        "domain": domain,
                        "ground_query_id": ground_id,
                        "portable_query": query,
                        "result": result,
                        "evaluation": evaluation,
                        "certificate": expected_certificate,
                    }
                )
            except (KeyError, TypeError, ValueError) as error:
                failures.append(
                    f"independent per-query replay failed: {named.query_key}: {error}"
                )

        if len(verified_rows) == 11:
            expected_ground_ids = tuple(
                row["ground_query_id"] for row in verified_rows
            )
            portable_ids = tuple(
                row["portable_query"].query_id for row in verified_rows
            )
            unique_portable_ids = set(portable_ids)
            workload_payload = {
                "profile_key": PROFILE_KEY,
                "build_epoch_ids": {
                    domain: expected_epochs[domain]["build_epoch_id"]
                    for domain in ("g2048", "lmb")
                },
                "domain_bindings": {
                    domain: {
                        "structural_id": replayed[domain]["structural_id"],
                        "build_epoch_id": expected_epochs[domain]["build_epoch_id"],
                        "portable_rapm_id": models[domain].model_id,
                        "coverage_id": models[domain].coverage_id,
                        "coverage_seed_ground_query_ids": tuple(
                            object_id(named.query, "query")
                            for named in replayed[domain]["train_queries"]
                        ),
                    }
                    for domain in ("g2048", "lmb")
                },
                "ordered_ground_query_ids": expected_ground_ids,
                "domain_order": ("g2048", "lmb"),
                "query_occurrence_count": 11,
                "distinct_ground_query_count": len(set(expected_ground_ids)),
                "distinct_portable_query_count": len(unique_portable_ids),
                "byte_equivalent_portable_projection_count": 11
                - len(unique_portable_ids),
                "minimum_distinct_queries": 8,
                "minimum_queries_per_domain": 4,
                "coverage_rule": "positive_support_subset_of_frozen_suite_closure",
                "normalizer_proof_ids": tuple(
                    sorted(
                        {
                            named.query.normalizer_proof_id
                            for _, named, _ in expected_campaign
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
            expected_workload = to_jsonable(
                {
                    "workload_id": object_id(workload_payload, "workload"),
                    **workload_payload,
                }
            )
            if workload != expected_workload:
                failures.append("WorkloadSpec/content ID differs from replayed campaign")

            per_domain_counts = {
                domain: sum(row["domain"] == domain for row in verified_rows)
                for domain in ("g2048", "lmb")
            }
            per_domain_unique = {
                domain: len(
                    {
                        row["portable_query"].query_id
                        for row in verified_rows
                        if row["domain"] == domain
                    }
                )
                for domain in ("g2048", "lmb")
            }
            expected_reuse = to_jsonable(
                {
                    "one_unchanged_model_per_domain": True,
                    "model_ids": {
                        domain: models[domain].model_id
                        for domain in ("g2048", "lmb")
                    },
                    "query_occurrence_count": 11,
                    "distinct_ground_query_count": 11,
                    "distinct_portable_query_count": len(unique_portable_ids),
                    "per_domain_query_counts": per_domain_counts,
                    "per_domain_distinct_portable_query_counts": per_domain_unique,
                    "all_queries_in_coverage": True,
                    "all_routes": tuple(
                        row["certificate"]["route"] for row in verified_rows
                    ),
                    "fresh_process_for_every_occurrence": True,
                }
            )
            if reuse != expected_reuse:
                failures.append("reuse audit differs from independent replay")

            report_payload = {
                "profile_key": PROFILE_KEY,
                "status": SLICE_PASS,
                "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
                "local_hybrid_gate_status": LOCAL_HYBRID_NOT_RUN,
                "workload_economics_gate_status": ECONOMICS_NOT_RUN,
                "supported_claims": SUPPORTED_CLAIMS,
                "unsupported_claims": UNSUPPORTED_CLAIMS,
                "query_occurrence_count": 11,
                "distinct_ground_query_count": 11,
                "distinct_portable_query_count": len(unique_portable_ids),
                "all_queries_certified": True,
                "all_exact_reward_and_failure_gaps_zero": True,
                "fresh_process_planning": True,
                "q_value_signatures_used": False,
                "local_repair_exercised": False,
                "scalar_break_even_claimed": False,
            }
            expected_report = to_jsonable(
                {
                    "report_id": object_id(report_payload, "phase3b-report"),
                    **report_payload,
                }
            )
            if report != expected_report:
                failures.append("Phase3B report/content ID/claims mismatch")

            expected_metrics = {
                "ground_states": {
                    domain: replayed[domain]["covered_ground_states"]
                    for domain in ("g2048", "lmb")
                },
                "abstract_cells": {
                    domain: replayed[domain]["abstract_cells"]
                    for domain in ("g2048", "lmb")
                },
                "abstract_state_action_pairs": {
                    domain: replayed[domain]["abstract_state_action_pairs"]
                    for domain in ("g2048", "lmb")
                },
                "query_occurrences": 11,
                "distinct_portable_queries": len(unique_portable_ids),
                "total_abstract_composed_candidates": sum(
                    row["result"].composed_candidate_count for row in verified_rows
                ),
                "evaluation_only_total_ground_composed_candidates": sum(
                    row["evaluation"]["ground"].composed_candidate_count
                    for row in verified_rows
                ),
                "certified_queries": sum(
                    row["evaluation"]["audit"].certified
                    for row in verified_rows
                ),
            }
            if metrics != expected_metrics:
                failures.append("metrics differ from independent replay")

            expected_query_counters = [
                {
                    "ground_query_id": row["ground_query_id"],
                    "load": {
                        "portable_model_loads": 1,
                        "portable_query_loads": 1,
                        "portable_model_bytes": len(
                            json.dumps(
                                models[row["domain"]].to_dict(),
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ),
                        "portable_query_bytes": len(
                            json.dumps(
                                row["portable_query"].to_dict(),
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ),
                    },
                    "abstract_plan": {
                        "composed_candidate_count": row[
                            "result"
                        ].composed_candidate_count,
                        "pareto_frontier_points": len(row["result"].frontier),
                        "selected_decision_nodes": len(
                            row["result"].selected.policy.decisions
                        )
                        if row["result"].selected is not None
                        else 0,
                    },
                    "portable_envelope_audit": {
                        "reachable_cell_horizon_pairs": row["evaluation"][
                            "portable_audit"
                        ].reachable_cell_horizon_pairs,
                    },
                    "ground_certificate_audit": {
                        "reachable_cell_horizon_pairs": len(
                            row["evaluation"]["audit"].reachable_bounds
                        ),
                    },
                    "local_ground": {"candidate_count": 0},
                    "full_fallback": {
                        "invocation_count": 0,
                        "candidate_count": 0,
                    },
                    "evaluation_only_j0": {
                        "composed_candidate_count": row["evaluation"][
                            "ground"
                        ].composed_candidate_count,
                    },
                    "abstract_composed_candidate_count": row[
                        "result"
                    ].composed_candidate_count,
                    "audit_reachable_cell_horizon_pairs": len(
                        row["evaluation"]["audit"].reachable_bounds
                    ),
                    "local_ground_candidate_count": 0,
                    "full_fallback_candidate_count": 0,
                    "evaluation_only_j0_composed_candidate_count": row[
                        "evaluation"
                    ]["ground"].composed_candidate_count,
                }
                for row in verified_rows
            ]
            expected_accounting = {
                "cost_protocol_status": ECONOMICS_NOT_RUN,
                "scalar_break_even": None,
                "reason": (
                    "Phase3B reports non-interchangeable exact work counters separately; "
                    "no frozen scalar hardware/cost conversion is applied"
                ),
                "build": {
                    domain: {
                        "covered_ground_states": replayed[domain][
                            "covered_ground_states"
                        ],
                        "ground_state_action_pairs": replayed[domain][
                            "ground_state_action_pairs"
                        ],
                        "ground_one_step_outcomes": sum(
                            len(replayed[domain]["kernel"].step(state, action))
                            for state in replayed[domain]["coverage"].covered_states
                            if not replayed[domain]["kernel"].is_terminal(state)
                            for action in replayed[domain]["kernel"].actions(state)
                        ),
                        "behavioral_refinement_rounds": len(
                            replayed[domain]["behavioural"].refinement_trace
                        )
                        - 1,
                        "portable_model_bytes_canonical_json": len(
                            json.dumps(
                                models[domain].to_dict(),
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ),
                    }
                    for domain in ("g2048", "lmb")
                },
                "query": expected_query_counters,
                "reconciliation": {
                    "query_occurrence_count": len(expected_query_counters),
                    "portable_model_loads": sum(
                        row["load"]["portable_model_loads"]
                        for row in expected_query_counters
                    ),
                    "portable_query_loads": sum(
                        row["load"]["portable_query_loads"]
                        for row in expected_query_counters
                    ),
                    "abstract_composed_candidate_count": sum(
                        row["abstract_plan"]["composed_candidate_count"]
                        for row in expected_query_counters
                    ),
                    "local_ground_candidate_count": sum(
                        row["local_ground"]["candidate_count"]
                        for row in expected_query_counters
                    ),
                    "full_fallback_invocation_count": sum(
                        row["full_fallback"]["invocation_count"]
                        for row in expected_query_counters
                    ),
                    "evaluation_only_j0_composed_candidate_count": sum(
                        row["evaluation_only_j0"]["composed_candidate_count"]
                        for row in expected_query_counters
                    ),
                },
            }
            if accounting != expected_accounting:
                failures.append("work accounting differs from independent replay")

        expected_events = (
            "workload_registry_frozen",
            "exact_behavioral_world_models_built",
            "portable_roundtrip_verified",
            "all_fresh_process_proposals_complete",
            "evaluation_only_j0_started",
            "independent_exact_audits_complete",
            SLICE_PASS,
            FULL_PHASE3_NOT_RUN,
            LOCAL_HYBRID_NOT_RUN,
            ECONOMICS_NOT_RUN,
        )
        if events != [
            {"sequence": index, "event": event}
            for index, event in enumerate(expected_events, start=1)
        ]:
            failures.append("Phase3B event content/order mismatch")
        if (
            accounting.get("cost_protocol_status") != ECONOMICS_NOT_RUN
            or accounting.get("scalar_break_even") is not None
        ):
            failures.append("Phase3B accounting overclaims the economics Gate")

        stable_paths = tuple(
            path for path in PHASE3B_REQUIRED_PATHS if path != "run.json"
        )
        stable_documents = {
            path: (
                _load_jsonl(bundle / path)
                if path.endswith(".jsonl")
                else _load(bundle / path)
            )
            for path in stable_paths
        }
        recomputed_semantic_hash = canonical_sha256(stable_documents)
        if recomputed_semantic_hash != run.get("semantic_hash"):
            failures.append("Phase3B semantic hash mismatch")

        expected_run_fields = {
            "run_id",
            "schema_version",
            "contract_version",
            "profile_key",
            "execution_profile",
            "status",
            "semantic_hash",
            "source_tree_sha256",
            "spec_hashes",
            "python",
            "platform",
            "started_at",
            "finished_at",
        }
        if set(run) != expected_run_fields:
            failures.append("Phase3B run field set mismatch")
        run_payload = {
            key: value
            for key, value in run.items()
            if key not in {"run_id", "started_at", "finished_at"}
        }
        if run.get("run_id") != object_id(run_payload, "run"):
            failures.append("Phase3B run content ID mismatch")
        if (
            run.get("schema_version") != "phase3b.v1"
            or run.get("contract_version") != CONTRACT_VERSION
            or run.get("profile_key") != PROFILE_KEY
            or run.get("execution_profile") != EXECUTION_PROFILE
            or run.get("status") != SLICE_PASS
            or run.get("source_tree_sha256") != _source_tree_hash()
            or run.get("spec_hashes") != _spec_hashes()
        ):
            failures.append("Phase3B schema/profile/source/spec hash mismatch")
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        failures.append(f"Phase3B verifier exception: {error}")

    return {
        "verified": not failures,
        "failures": tuple(failures),
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_semantic_hash,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = verify_phase3b(args.bundle)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
