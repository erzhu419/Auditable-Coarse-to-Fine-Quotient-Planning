from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

import acfqp.phase3d as phase3d_module
from acfqp.general_local_solver import (
    ALGORITHM_ID,
    AUTHORIZED_EXHAUSTED,
    CAPABILITY_SCHEMA,
    CERTIFIED,
    POLICY_CLASS,
    REQUEST_SCHEMA,
    SEARCH_CAP_EXHAUSTED,
    SELECTION_RULE,
    SLICE_SCHEMA,
    solve_general_local_recovery,
    validate_general_local_result,
)
from acfqp.phase3d import _validate_general_worker_result


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _oid(prefix: str, value) -> str:
    return f"{prefix}-{hashlib.sha256(_canonical(value).encode()).hexdigest()[:16]}"


def _logical_id(prefix: str, value) -> str:
    return f"{prefix}:{hashlib.sha256(_canonical(value).encode()).hexdigest()}"


def _named_id(prefix: str, label: str) -> str:
    digest = hashlib.sha256(label.encode()).hexdigest()[:16]
    return f"{prefix}-{label}-{digest}"


def _proof(label: str) -> str:
    return _named_id("proof-node", label)


def _state(label: str) -> str:
    return _named_id("state", label)


def _action_id(label: str) -> str:
    return _named_id("ground-action", label)


def _sha(value) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode()).hexdigest()


def _f(value: Fraction | int) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _form(constant: Fraction | int, terms: dict[str, Fraction]) -> dict:
    payload = {
        "constant": _f(constant),
        "terms": [
            {"port_id": port_id, "coefficient": _f(coefficient)}
            for port_id, coefficient in sorted(terms.items())
        ],
    }
    return {"form_id": _logical_id("sparse-form", payload), **payload}


def _action(
    action_id: str,
    reward: Fraction | int,
    failure: Fraction | int,
    *,
    exits: tuple[tuple[str, Fraction], ...] = (),
) -> dict:
    exit_mass = sum((probability for _, probability in exits), Fraction(0))
    return {
        "action_id": _action_id(action_id),
        "immediate_reward": _f(reward),
        "failure_probability": _f(failure),
        "termination_probability": _f(1 - exit_mass),
        "exits": [
            {"exit_port_id": port_id, "probability": _f(probability)}
            for port_id, probability in sorted(exits)
        ],
    }


def _cell(
    node_id: str,
    input_port_id: str,
    members: dict[str, list[dict]],
) -> dict:
    member_rows = [
        {
            "state_id": _state(state_id),
            "actions": sorted(actions, key=lambda row: row["action_id"]),
        }
        for state_id, actions in members.items()
    ]
    return {
        "node_id": node_id,
        "cell": f"cell:{node_id}",
        "remaining": 1,
        "input_port_id": input_port_id,
        "members": sorted(member_rows, key=lambda row: row["state_id"]),
    }


def _bundle(
    *,
    cells: list[dict],
    defaults: dict[str, tuple[Fraction, Fraction]],
    reward_floor: Fraction,
    failure_ceiling: Fraction,
    reward_forms: list[dict],
    failure_forms: list[dict],
    exit_ports: dict[str, tuple[Fraction, Fraction]] | None = None,
    limits: dict[str, int] | None = None,
) -> tuple[dict, dict, dict]:
    capability_payload = {
        "schema": CAPABILITY_SCHEMA,
        "frontier_id": _named_id("failed-proof-frontier", "synthetic"),
        "reward_floor": _f(reward_floor),
        "failure_ceiling": _f(failure_ceiling),
        "input_ports": [
            {
                "port_id": port_id,
                "default_reward_lower": _f(values[0]),
                "default_failure_upper": _f(values[1]),
            }
            for port_id, values in sorted(defaults.items())
        ],
        "exit_ports": [
            {
                "port_id": port_id,
                "reward_lower": _f(values[0]),
                "failure_upper": _f(values[1]),
            }
            for port_id, values in sorted((exit_ports or {}).items())
        ],
        "root_reward_forms": sorted(reward_forms, key=lambda row: row["form_id"]),
        "root_failure_forms": sorted(failure_forms, key=lambda row: row["form_id"]),
    }
    capability = {
        **capability_payload,
        "capability_id": _logical_id(
            "sparse-robust-affine-capability", capability_payload
        ),
    }
    slice_payload = {
        "schema": SLICE_SCHEMA,
        "authorization_id": _named_id("local-authorization", "synthetic"),
        "frontier_id": _named_id("failed-proof-frontier", "synthetic"),
        "cells": sorted(cells, key=lambda row: row["node_id"]),
    }
    ground_slice = {
        **slice_payload,
        "slice_id": _oid("sparse-frontier-ground-slice", slice_payload),
    }
    selected_limits = limits or {
        "max_subset_evaluations": 100,
        "max_policy_assignments": 1000,
        "max_root_frontier_points": 100,
        "max_dominance_comparisons": 10000,
        "max_affine_term_evaluations": 100000,
        "max_rational_bits": 1024,
    }
    request_payload = {
        "schema": REQUEST_SCHEMA,
        "occurrence_id": _named_id("occurrence", "synthetic"),
        "frontier_id": capability["frontier_id"],
        "capability_id": capability["capability_id"],
        "slice_id": ground_slice["slice_id"],
        "capability_sha256": _sha(capability),
        "slice_sha256": _sha(ground_slice),
        "algorithm_id": ALGORITHM_ID,
        "selection_rule": SELECTION_RULE,
        "policy_class": POLICY_CLASS,
        "search_limits": selected_limits,
    }
    request = {
        **request_payload,
        "request_id": _oid("general-local-request", request_payload),
    }
    return capability, ground_slice, request


def _two_cell_budget(*, limits=None, failure_ceiling=Fraction(1, 10)):
    # The trade action obtains all value/risk through a scalar abstract exit.
    port_a = _proof("a")
    port_b = _proof("b")
    trade_exit = _proof("trade-exit")
    safe = _action("safe", 0, 0)
    trade = _action("trade", 0, 0, exits=((trade_exit, Fraction(1)),))
    cells = [
        _cell(port_a, port_a, {"a": [safe, trade]}),
        _cell(port_b, port_b, {"b": [safe, trade]}),
    ]
    weighted = _form(0, {port_a: Fraction(1, 2), port_b: Fraction(1, 2)})
    return _bundle(
        cells=cells,
        defaults={
            port_a: (Fraction(0), Fraction(1)),
            port_b: (Fraction(0), Fraction(1)),
        },
        reward_floor=Fraction(1, 2),
        failure_ceiling=failure_ceiling,
        reward_forms=[weighted],
        failure_forms=[weighted],
        exit_ports={trade_exit: (Fraction(1), Fraction(1, 5))},
        limits=limits,
    )


def test_joint_two_cell_risk_budget_finds_mixed_deterministic_policy():
    capability, ground_slice, request = _two_cell_budget()
    result = solve_general_local_recovery(capability, ground_slice, request)

    assert result.status == CERTIFIED
    expected_nodes = tuple(sorted((_proof("a"), _proof("b"))))
    assert result.localized_node_ids == expected_nodes
    assert result.root_reward_lower == Fraction(1, 2)
    assert result.root_failure_upper == Fraction(1, 10)
    selected = {row.node_id: row.action_id for row in result.decisions}
    assert selected[expected_nodes[0]] == _action_id("safe")
    assert selected[expected_nodes[1]] == _action_id("trade")
    assert result.theoretical_total_policy_space == 9
    assert result.counters["policy_assignments"] == 9
    assert len(result.subset_records) == 4
    assert len(result.subset_records[-1].root_frontier) == 3
    validate_general_local_result(result.to_dict())


def test_phase3d_operational_mode_does_not_replay_general_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capability, ground_slice, request = _two_cell_budget()
    result = solve_general_local_recovery(
        capability, ground_slice, request
    ).to_dict()

    def forbidden_replay(*_args, **_kwargs):
        raise AssertionError("host general local solver replay was called")

    monkeypatch.setattr(
        phase3d_module, "solve_general_local_recovery", forbidden_replay
    )
    _validate_general_worker_result(
        result,
        capability,
        ground_slice,
        request,
        operational_no_full_replay=True,
    )
    with pytest.raises(AssertionError, match="host general local solver replay"):
        _validate_general_worker_result(
            result,
            capability,
            ground_slice,
            request,
            operational_no_full_replay=False,
        )


def test_joint_member_composition_uses_cell_min_reward_and_max_risk():
    port_c = _proof("c")
    cells = [
        _cell(
            port_c,
            port_c,
            {
                "x": [
                    _action("safe", 1, 0),
                    _action("trade", 2, Fraction(1, 5)),
                ],
                "y": [
                    _action("safe", 0, 0),
                    _action("trade", 1, Fraction(1, 5)),
                ],
            },
        )
    ]
    identity = _form(0, {port_c: Fraction(1)})
    capability, ground_slice, request = _bundle(
        cells=cells,
        defaults={port_c: (Fraction(0), Fraction(1))},
        reward_floor=Fraction(1),
        failure_ceiling=Fraction(1, 5),
        reward_forms=[identity],
        failure_forms=[identity],
    )
    result = solve_general_local_recovery(capability, ground_slice, request)

    assert result.status == CERTIFIED
    assert result.localized_node_ids == (port_c,)
    assert result.root_reward_lower == 1
    assert result.root_failure_upper == Fraction(1, 5)
    assert {row.state_id: row.action_id for row in result.decisions} == {
        _state("x"): _action_id("safe"),
        _state("y"): _action_id("trade"),
    }
    assert result.theoretical_total_policy_space == 5
    assert result.counters["policy_assignments"] == 5
    assert len(result.subset_records[-1].root_frontier) == 2


def test_compiled_merged_successor_requires_globally_useful_locally_dominated_choice():
    # Trusted elimination of s1->c->{e,f}, s2->d->e gives masses 19/20 and
    # 1/20.  At c alone, e=risky/f=safe dominates e=safe/f=risky; globally the
    # heavy d->e path reverses which assignment can satisfy the root chance cap.
    port_e = _proof("e")
    port_f = _proof("f")
    cells = [
        _cell(
            port_e,
            port_e,
            {"e": [_action("safe", 0, 0), _action("risky", 10, Fraction(1, 10))]},
        ),
        _cell(
            port_f,
            port_f,
            {"f": [_action("safe", 0, 0), _action("risky", 9, Fraction(1, 5))]},
        ),
    ]
    root = _form(0, {port_e: Fraction(19, 20), port_f: Fraction(1, 20)})
    capability, ground_slice, request = _bundle(
        cells=cells,
        defaults={
            port_e: (Fraction(10), Fraction(1, 10)),
            port_f: (Fraction(0), Fraction(0)),
        },
        reward_floor=Fraction(9, 20),
        failure_ceiling=Fraction(1, 20),
        reward_forms=[root],
        failure_forms=[root],
    )
    result = solve_general_local_recovery(capability, ground_slice, request)

    assert result.status == CERTIFIED
    assert result.localized_node_ids == tuple(sorted((port_e, port_f)))
    assert result.root_reward_lower == Fraction(9, 20)
    assert result.root_failure_upper == Fraction(1, 100)
    assert {row.node_id: row.action_id for row in result.decisions} == {
        port_e: _action_id("safe"),
        port_f: _action_id("risky"),
    }
    assert {
        (point.reward_floor, point.failure_ceiling)
        for point in result.subset_records[-1].root_frontier
    } == {
        (Fraction(0), Fraction(0)),
        (Fraction(9, 20), Fraction(1, 100)),
        (Fraction(19, 2), Fraction(19, 200)),
        (Fraction(199, 20), Fraction(21, 200)),
    }


def test_assignment_and_frontier_caps_are_explicit_not_infeasibility():
    assignment_limits = {
        "max_subset_evaluations": 100,
        "max_policy_assignments": 8,
        "max_root_frontier_points": 100,
        "max_dominance_comparisons": 10000,
        "max_affine_term_evaluations": 100000,
        "max_rational_bits": 1024,
    }
    capability, ground_slice, request = _two_cell_budget(limits=assignment_limits)
    capped = solve_general_local_recovery(capability, ground_slice, request)
    assert capped.status == SEARCH_CAP_EXHAUSTED
    assert capped.cap_reason == "max_policy_assignments"
    assert capped.counters["policy_assignments"] == 8
    assert not capped.search_complete
    assert not capped.minimality_proven
    assert not capped.certified

    exact_limits = {**assignment_limits, "max_policy_assignments": 9}
    capability, ground_slice, request = _two_cell_budget(limits=exact_limits)
    assert solve_general_local_recovery(capability, ground_slice, request).status == CERTIFIED

    frontier_limits = {
        **exact_limits,
        "max_root_frontier_points": 2,
    }
    capability, ground_slice, request = _two_cell_budget(limits=frontier_limits)
    capped = solve_general_local_recovery(capability, ground_slice, request)
    assert capped.status == SEARCH_CAP_EXHAUSTED
    assert capped.cap_reason == "max_root_frontier_points"


def test_authorized_exhaustion_is_distinct_and_complete():
    capability, ground_slice, request = _two_cell_budget(
        failure_ceiling=Fraction(0)
    )
    result = solve_general_local_recovery(capability, ground_slice, request)
    assert result.status == AUTHORIZED_EXHAUSTED
    assert result.search_complete
    assert result.minimality_proven
    assert not result.certified
    assert result.counters["policy_assignments"] == 9


def test_result_id_binds_derived_fields_and_validator_rejects_resigned_lie():
    capability, ground_slice, request = _two_cell_budget()
    document = solve_general_local_recovery(
        capability, ground_slice, request
    ).to_dict()
    forged = copy.deepcopy(document)
    forged["certified"] = False
    with pytest.raises(ValueError, match="result_id"):
        validate_general_local_result(forged)

    payload = dict(forged)
    payload.pop("result_id")
    forged["result_id"] = _logical_id("general-local-result", payload)
    with pytest.raises(ValueError, match="certified"):
        validate_general_local_result(forged)


def _isolated_runtime_command(tmp_path: Path, *, extra_input: bool = False):
    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        pytest.skip("bubblewrap unavailable")
    capability, ground_slice, request = _two_cell_budget()
    runtime_root = tmp_path / "runtime"
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    runtime_root.mkdir()
    input_root.mkdir()
    output_root.mkdir()
    source_root = Path(__file__).resolve().parents[1] / "src" / "acfqp"
    for name in ("general_local_solver.py", "general_local_runtime.py"):
        shutil.copy2(source_root / name, runtime_root / name)
    capability_path = input_root / "capability.json"
    slice_path = input_root / "slice.json"
    request_path = input_root / "request.json"
    for path, value in (
        (capability_path, capability),
        (slice_path, ground_slice),
        (request_path, request),
    ):
        path.write_text(_canonical(value) + "\n", encoding="utf-8")
    if extra_input:
        (input_root / "forbidden.json").write_text("{}\n", encoding="utf-8")
    system_mounts: list[str] = []
    for path in ("/usr", "/lib", "/lib64"):
        if Path(path).exists():
            system_mounts.extend(("--ro-bind", path, path))
    command = (
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
        "--ro-bind",
        str(input_root),
        "/input",
        "--bind",
        str(output_root),
        "/output",
        "--setenv",
        "PYTHONHASHSEED",
        "0",
        "/usr/bin/python3",
        "-S",
        "/runtime/general_local_runtime.py",
        "--capability",
        "/input/capability.json",
        "--slice",
        "/input/slice.json",
        "--request",
        "/input/request.json",
        "--output",
        "/output/result.json",
        "--attestation",
        "/output/attestation.json",
    )
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0 and process.stderr.startswith("bwrap:"):
        pytest.skip(f"bubblewrap namespace unavailable: {process.stderr.strip()}")
    return process, output_root


def test_runtime_replays_three_capabilities_and_binds_output(tmp_path):
    process, output_root = _isolated_runtime_command(tmp_path)
    assert process.returncode == 0, process.stderr
    result_path = output_root / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    attestation = json.loads(
        (output_root / "attestation.json").read_text(encoding="utf-8")
    )
    validate_general_local_result(result)
    assert result["status"] == CERTIFIED
    assert attestation["result_id"] == result["result_id"]
    assert attestation["output_sha256"] == hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()
    assert attestation["input_regular_files"] == [
        "capability.json",
        "request.json",
        "slice.json",
    ]
    assert attestation["python_site_disabled"] is True
    assert attestation["project_checkout_visible"] is False
    assert attestation["network_namespace_unshared"] is True
    assert attestation["unexpected_module_origins"] == []


def test_runtime_rejects_extra_worker_input_capability(tmp_path):
    process, output_root = _isolated_runtime_command(tmp_path, extra_input=True)
    assert process.returncode != 0
    assert "outside the three-file capability" in process.stderr
    assert not (output_root / "result.json").exists()
