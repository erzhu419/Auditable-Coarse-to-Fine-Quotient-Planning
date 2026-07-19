from __future__ import annotations

import itertools
import json
import shutil
from fractions import Fraction
from pathlib import Path

import pytest

from acfqp.aliased_safe_chain import (
    CandidateProbe,
    Witness,
    rank_joint_candidates,
    run_aliased_safe_chain,
)
from acfqp.artifacts import (
    canonical_sha256,
    sha256_file,
    verify_artifact_bundle,
    write_json,
    write_jsonl,
)
from acfqp.refinement import Predicate, RankedSplitCandidate


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

import sys

sys.path.insert(0, str(SCRIPTS))
from verify_aliased_cegar import verify_aliased_cegar  # noqa: E402


@pytest.fixture(scope="session")
def clean_bundle(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    bundle = tmp_path_factory.mktemp("aliased-cegar") / "bundle"
    summary = run_aliased_safe_chain(bundle)
    assert verify_artifact_bundle(bundle) == []
    return bundle, summary


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resign(bundle: Path, relative_path: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    record = next(
        item for item in manifest["files"] if item["path"] == relative_path
    )
    target = bundle / relative_path
    record["bytes"] = target.stat().st_size
    record["sha256"] = sha256_file(target)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )


def _tampered_copy(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def test_clean_bundle_verifies(clean_bundle: tuple[Path, dict]) -> None:
    bundle, summary = clean_bundle
    report = verify_aliased_cegar(bundle)
    assert summary["status"] == "CERTIFIED"
    assert report["verified"], report["failures"]
    assert report["semantic_hash"] == summary["semantic_hash"]


def test_clean_rerun_semantic_hash_is_stable(
    clean_bundle: tuple[Path, dict],
    tmp_path: Path,
) -> None:
    first_bundle, first_summary = clean_bundle
    second_bundle = tmp_path / "rerun"
    second_summary = run_aliased_safe_chain(second_bundle)
    assert second_summary["semantic_hash"] == first_summary["semantic_hash"]
    assert _read_json(first_bundle / "run.json")["semantic_hash"] == _read_json(
        second_bundle / "run.json"
    )["semantic_hash"]
    report = verify_aliased_cegar(second_bundle)
    assert report["verified"], report["failures"]


@pytest.mark.parametrize(
    ("case", "expected_failure"),
    [
        ("predicate_truth", "witness inventory mismatch"),
        ("child_member", "accepted split/lineage mismatch: children"),
        ("split_order", "accepted split/lineage mismatch: parent_cell"),
        ("failure_upper", "lifted_failure_upper mismatch"),
        ("claim", "narrow claim boundary mismatch"),
        ("fallback_event", "fallback event is forbidden"),
    ],
)
def test_resigned_semantic_tampering_is_rejected(
    clean_bundle: tuple[Path, dict],
    tmp_path: Path,
    case: str,
    expected_failure: str,
) -> None:
    source, _ = clean_bundle
    bundle = _tampered_copy(source, tmp_path / case)

    if case == "predicate_truth":
        relative = "refinement/iterations/001/witness.json"
        document = _read_json(bundle / relative)
        value = document["witnesses"][0]["left_geometry"][
            "first_survivor_adjacent_nonmerged_count"
        ]
        value["numerator"] = 1 - value["numerator"]
        write_json(bundle / relative, document)
    elif case == "child_member":
        relative = "refinement/iterations/001/accepted_split.json"
        document = _read_json(bundle / relative)
        document["children"][0]["member_state_ids"][0] = document["children"][1][
            "member_state_ids"
        ][0]
        write_json(bundle / relative, document)
    elif case == "split_order":
        relative = "refinement/iterations/001/accepted_split.json"
        document = _read_json(bundle / relative)
        later = _read_json(
            bundle / "refinement/iterations/002/accepted_split.json"
        )
        document["parent_cell"] = later["parent_cell"]
        write_json(bundle / relative, document)
    elif case == "failure_upper":
        relative = "audit/audit_02.json"
        document = _read_json(bundle / relative)
        document["lifted_failure_upper"] = {"numerator": 1, "denominator": 2}
        write_json(bundle / relative, document)
    elif case == "claim":
        relative = "result/cegar_certificate.json"
        document = _read_json(bundle / relative)
        document["supported_claim"] = "automatic state quotient discovery"
        write_json(bundle / relative, document)
    else:
        relative = "events.jsonl"
        events = [
            json.loads(line)
            for line in (bundle / relative).read_text(encoding="utf-8").splitlines()
            if line
        ]
        events.append({"sequence": 10, "event": "ground_fallback"})
        write_jsonl(bundle / relative, events)

    _resign(bundle, relative)
    assert verify_artifact_bundle(bundle) == []
    report = verify_aliased_cegar(bundle)
    assert not report["verified"]
    assert any(expected_failure in failure for failure in report["failures"])


def _probe(
    candidate_id: str,
    *,
    reduction: int,
    newly: int,
    failure: int,
    rate: int,
    predicate_name: str,
    witness_id: str,
) -> CandidateProbe:
    predicate = Predicate(predicate_name, "<=", Fraction(1, 2), lambda _: 0)
    ranked = RankedSplitCandidate(
        predicate,
        audit_width_reduction=Fraction(reduction),
        newly_certified_pairs=newly,
        failure_width_reduction=Fraction(failure),
        rate_cost=Fraction(rate),
    )
    witness = Witness("cell", "action", 1, None, None, Fraction(1))
    return CandidateProbe(
        candidate_id,
        "cell",
        "action",
        1,
        predicate,
        witness_id,
        (witness_id,),
        witness,
        "SPLIT_ACCEPTED",
        ranked,
        Fraction(1),
        Fraction(0),
        False,
        Fraction(1),
        Fraction(1),
        (("left",), ("right",)),
    )


def test_joint_candidate_full_tie_order_is_permutation_invariant() -> None:
    probes = (
        _probe(
            "score",
            reduction=2,
            newly=0,
            failure=0,
            rate=1,
            predicate_name="z-score",
            witness_id="witness-z",
        ),
        _probe(
            "newly",
            reduction=1,
            newly=2,
            failure=0,
            rate=1,
            predicate_name="z-newly",
            witness_id="witness-z",
        ),
        _probe(
            "failure",
            reduction=1,
            newly=1,
            failure=2,
            rate=1,
            predicate_name="z-failure",
            witness_id="witness-z",
        ),
        _probe(
            "rate",
            reduction=1,
            newly=1,
            failure=1,
            rate=1,
            predicate_name="z-rate",
            witness_id="witness-z",
        ),
        _probe(
            "predicate",
            reduction=2,
            newly=1,
            failure=1,
            rate=2,
            predicate_name="a",
            witness_id="witness-z",
        ),
        _probe(
            "witness-a",
            reduction=2,
            newly=1,
            failure=1,
            rate=2,
            predicate_name="b",
            witness_id="witness-a",
        ),
        _probe(
            "witness-b",
            reduction=2,
            newly=1,
            failure=1,
            rate=2,
            predicate_name="b",
            witness_id="witness-b",
        ),
    )
    expected = (
        "score",
        "newly",
        "failure",
        "rate",
        "predicate",
        "witness-a",
        "witness-b",
    )
    for permutation in itertools.permutations(probes):
        observed = tuple(
            probe.candidate_id for probe in rank_joint_candidates(permutation)
        )
        assert observed == expected
