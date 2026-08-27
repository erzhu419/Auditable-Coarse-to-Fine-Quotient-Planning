"""Frozen pre-V42 standard-2048 workload-history freshness evidence.

The V42 preregistration must not select a board, D4 orbit, or deterministic
outcome seed visible in the Git-retained pre-V42 formal/development source
closure.  A plain list of hand-picked predecessor modules is too easy to make
incomplete.  This module therefore defines one deterministic, outcome-free
scan of every text blob reachable from the frozen pre-V42 Git boundary.  It
does not claim knowledge of unretained, external, or deleted executions.

Only source text is inspected.  No standard-2048 target, planner, tape, or
campaign function is imported or executed by the scanner.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp.phase3e_ids import canonical_json_bytes


SCHEMA_VERSION = "42.0.0"
HISTORY_BOUNDARY_COMMIT = "349cdb47b9eeaf18906ccad1fb27aec0dca768cd"
HISTORY_BOUNDARY_TREE = "4815ea8731779b0f259c74f08aaf31d3e93b93b1"
HISTORY_SCAN_ALGORITHM = "ALL_REACHABLE_UTF8_BLOBS_UNCONDITIONAL_AST_JSON_TEXT_V2"
MAXIMUM_SCANNED_BLOB_BYTES = 64 * 1024 * 1024

# Filled only after the deterministic scanner is reviewed.  Keeping the
# sentinel fail-closed makes an accidentally half-generated preregistration
# impossible to freeze.
EXPECTED_HISTORY_SCAN_SUMMARY: dict[str, Any] = {
    "schema": "acfqp.standard_2048_history_scan.v42",
    "schema_version": SCHEMA_VERSION,
    "algorithm": HISTORY_SCAN_ALGORITHM,
    "history_boundary_commit": HISTORY_BOUNDARY_COMMIT,
    "history_boundary_tree": HISTORY_BOUNDARY_TREE,
    "reachable_commit_count": 1_433,
    "reachable_commit_set_sha256": (
        "b772eeb267b26c1727079ad316b86d917009cab6f2362dfa483a38cbd91f9606"
    ),
    "reachable_object_with_path_count": 10_650,
    "reachable_blob_count": 6_163,
    "maximum_reachable_blob_byte_count": 59_473_200,
    "maximum_scanned_blob_byte_count": 67_108_864,
    "skipped_oversize_blob_count": 0,
    "scanned_utf8_blob_count": 6_163,
    "scanned_utf8_blob_manifest_sha256": (
        "cf98270a660524d1285f40b643b781054122b882d33ef443534eee7e10815308"
    ),
    "standard_2048_text_blob_count": 454,
    "standard_2048_text_blob_id_set_sha256": (
        "09cf4a43f77afc85ad737c75cbd82d8610c8a13a1fc0715dc6762b80c7a9de5c"
    ),
    "literal_board_count": 673,
    "literal_board_set_sha256": (
        "8a507980fe94e0fed6e6d5585c742492598572b7ca362c76d7fee4da18316d62"
    ),
    "d4_orbit_count": 665,
    "d4_orbit_set_sha256": (
        "d96095da6430484a799582b36e36c88df95bbb74746a5077f3d31c9d4c906752"
    ),
    "literal_seed_count": 57,
    "literal_seed_set_sha256": (
        "e4e019ae0c194c81314aa5826667677f3e04d308498c050d84435e13f4066f2c"
    ),
    "seed_template_count": 18,
    "seed_template_set_sha256": (
        "b033585930af28f9f375b3e8ffdf63757afab81c11ec261b25c83ba9376e0c06"
    ),
}
EXPECTED_HISTORY_MANIFEST_ID = (
    "c94d62bbcaa3cea0869a4a00b0944808b5e893a7a4c276e93a3b583df4aa5d29"
)
FROZEN_CANDIDATE_PROOF: dict[str, Any] = {
    "history_scan_summary": EXPECTED_HISTORY_SCAN_SUMMARY,
    "candidate_boards": [
        {
            "board": [2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            "board_sha256": "c96ce0447c09bd8cd6e3f4e3f2c52b7aafc57f5c42c44916cd524b352d558626",
            "d4_orbit_representative": [
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0
            ],
            "d4_orbit_sha256": "5dbca2dd1b81355fdd9d6c8a3786356b9ef08aed81d385ae1aca45a85918d7e2",
            "exact_board_absent_from_history": True,
            "d4_orbit_absent_from_history": True,
        },
        {
            "board": [0, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "board_sha256": "bd21ca1e7b49fea1ccd42ae43a464488f3f53a0b2cfd0d4b0ab692b84e407aa5",
            "d4_orbit_representative": [
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 2, 0
            ],
            "d4_orbit_sha256": "cef1bba164aca47e43fec82cf9a4c25c1062e0b002d550e21efd287ada3060dc",
            "exact_board_absent_from_history": True,
            "d4_orbit_absent_from_history": True,
        },
    ],
    "candidate_seeds": [
        {
            "seed": "standard-2048-v42-fresh-terminal-00-7f3c8b19-20260827",
            "seed_sha256": "56d10fbd0f1b8cd342a27a34df0370976c222829118bd43ef48b6c8efdd42354",
            "literal_seed_absent_from_history": True,
            "seed_bytes_absent_from_every_history_blob": True,
            "seed_not_generated_by_historical_template": True,
        },
        {
            "seed": "standard-2048-v42-fresh-terminal-01-92a64de5-20260827",
            "seed_sha256": "f2fd6553df60e476d9cf9fe4680924457379fa78598d1a2553e16767a8bffcb3",
            "literal_seed_absent_from_history": True,
            "seed_bytes_absent_from_every_history_blob": True,
            "seed_not_generated_by_historical_template": True,
        },
    ],
    "candidate_board_orbits_pairwise_distinct": True,
    "all_candidates_fresh": True,
}


class ConstructionK7Standard2048HistoryManifestV42Error(ValueError):
    """The frozen historical blob closure or freshness proof changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048HistoryManifestV42Error(message)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _git_bytes(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        _fail(
            f"git {' '.join(arguments)} failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout


def _literal_integer_vector(node: ast.AST) -> tuple[int, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[int] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or type(element.value) is not int:
            return None
        values.append(element.value)
    return tuple(values)


def _literal_board(node: ast.AST) -> tuple[int, ...] | None:
    direct = _literal_integer_vector(node)
    if direct is not None and len(direct) == 16 and all(rank >= 0 for rank in direct):
        return direct
    if not isinstance(node, (ast.List, ast.Tuple)) or len(node.elts) != 4:
        return None
    rows = tuple(_literal_integer_vector(row) for row in node.elts)
    if any(row is None or len(row) != 4 for row in rows):
        return None
    flattened = tuple(rank for row in rows for rank in row)  # type: ignore[union-attr]
    return flattened if all(rank >= 0 for rank in flattened) else None


def _d4_orbit_representative(board: tuple[int, ...]) -> tuple[int, ...]:
    if len(board) != 16:
        _fail("history board is not 4 by 4")
    matrix = [list(board[index * 4 : (index + 1) * 4]) for index in range(4)]
    candidates: list[tuple[int, ...]] = []
    for reflected in (False, True):
        current = [row[::-1] for row in matrix] if reflected else [row[:] for row in matrix]
        for _ in range(4):
            candidates.append(tuple(rank for row in current for rank in row))
            current = [list(row) for row in zip(*current[::-1])]
    return min(candidates)


def _joined_string_pattern(node: ast.JoinedStr) -> str:
    pieces: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and type(value.value) is str:
            pieces.append(re.escape(value.value))
        elif isinstance(value, ast.FormattedValue):
            # Historical seed indices are decimal, commonly zero padded.  A
            # broad nonempty token is conservative for unfamiliar templates.
            pieces.append(r"[^\x00\r\n]+")
        else:  # pragma: no cover - exhaustive for valid JoinedStr nodes
            pieces.append(r"[^\x00\r\n]+")
    return "^" + "".join(pieces) + "$"


@dataclass(frozen=True, slots=True)
class _BlobFact:
    object_id: str
    representative_path: str
    byte_count: int
    sha256: str

    def document(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "representative_path": self.representative_path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
        }


def _reachable_object_paths(root: Path) -> tuple[tuple[str, str], ...]:
    raw = _git_bytes(root, "rev-list", "--objects", HISTORY_BOUNDARY_COMMIT)
    rows: list[tuple[str, str]] = []
    for line in raw.decode("utf-8", errors="surrogateescape").splitlines():
        object_id, separator, path = line.partition(" ")
        if separator and path:
            rows.append((object_id, path))
    return tuple(rows)


def _read_reachable_blobs(
    root: Path, objects: Iterable[tuple[str, str]]
) -> tuple[tuple[tuple[_BlobFact, bytes], ...], dict[str, int]]:
    rows: list[tuple[_BlobFact, bytes]] = []
    unique: dict[str, str] = {}
    for object_id, path in objects:
        unique.setdefault(object_id, path)
    request = b"".join(object_id.encode("ascii") + b"\n" for object_id in unique)
    checked = subprocess.run(
        ("git", "cat-file", "--batch-check"),
        cwd=root,
        input=request,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if checked.returncode != 0:
        _fail(
            "git cat-file --batch-check failed: "
            + checked.stderr.decode("utf-8", errors="replace").strip()
        )
    checked_lines = checked.stdout.splitlines()
    if len(checked_lines) != len(unique):
        _fail("history batch-check line count changed")
    eligible: dict[str, str] = {}
    reachable_blob_count = 0
    maximum_reachable_blob_byte_count = 0
    skipped_oversize_blob_count = 0
    for requested_id, line in zip(unique, checked_lines, strict=True):
        columns = line.decode("ascii").split()
        if len(columns) != 3 or columns[0] != requested_id:
            _fail("history batch-check output changed")
        try:
            size = int(columns[2])
        except ValueError as error:
            raise ConstructionK7Standard2048HistoryManifestV42Error(
                "history batch-check size is malformed"
            ) from error
        if columns[1] == "blob":
            reachable_blob_count += 1
            maximum_reachable_blob_byte_count = max(
                maximum_reachable_blob_byte_count, size
            )
            if size <= MAXIMUM_SCANNED_BLOB_BYTES:
                eligible[requested_id] = unique[requested_id]
            else:
                skipped_oversize_blob_count += 1
    request = b"".join(object_id.encode("ascii") + b"\n" for object_id in eligible)
    completed = subprocess.run(
        ("git", "cat-file", "--batch"),
        cwd=root,
        input=request,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        _fail(
            "git cat-file --batch failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    stream = memoryview(completed.stdout)
    offset = 0
    for requested_id, path in eligible.items():
        newline = completed.stdout.find(b"\n", offset)
        if newline < 0:
            _fail("history batch header is truncated")
        header = completed.stdout[offset:newline].decode("ascii")
        offset = newline + 1
        columns = header.split()
        if len(columns) == 2 and columns[1] == "missing":
            _fail("history batch object is missing")
        if len(columns) != 3:
            _fail("history batch header is malformed")
        observed_id, kind, size_text = columns
        if observed_id != requested_id:
            _fail("history batch object ordering changed")
        try:
            size = int(size_text)
        except ValueError as error:  # pragma: no cover - Git contract
            raise ConstructionK7Standard2048HistoryManifestV42Error(
                "history blob size is malformed"
            ) from error
        content = bytes(stream[offset : offset + size])
        offset += size
        if bytes(stream[offset : offset + 1]) != b"\n":
            _fail("history batch object delimiter changed")
        offset += 1
        if kind != "blob" or size > MAXIMUM_SCANNED_BLOB_BYTES:
            _fail("history batch content escaped the checked blob inventory")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        rows.append(
            (
                _BlobFact(
                    object_id=requested_id,
                    representative_path=path,
                    byte_count=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                ),
                content,
            )
        )
    if offset != len(completed.stdout):
        _fail("history batch output has trailing bytes")
    rows.sort(key=lambda row: (row[0].object_id, row[0].representative_path))
    return tuple(rows), {
        "reachable_object_with_path_count": len(unique),
        "reachable_blob_count": reachable_blob_count,
        "maximum_reachable_blob_byte_count": maximum_reachable_blob_byte_count,
        "maximum_scanned_blob_byte_count": MAXIMUM_SCANNED_BLOB_BYTES,
        "skipped_oversize_blob_count": skipped_oversize_blob_count,
    }


def scan_standard_2048_git_history_v42(root: Path) -> dict[str, Any]:
    """Return the deterministic pre-V42 history closure without executing it."""

    root = root.resolve()
    observed_tree = _git_bytes(
        root, "rev-parse", f"{HISTORY_BOUNDARY_COMMIT}^{{tree}}"
    ).decode("ascii").strip()
    if observed_tree != HISTORY_BOUNDARY_TREE:
        _fail("history boundary tree changed")
    commit_ids = tuple(
        sorted(
            _git_bytes(root, "rev-list", HISTORY_BOUNDARY_COMMIT)
            .decode("ascii")
            .splitlines()
        )
    )
    object_paths = _reachable_object_paths(root)
    blob_rows, blob_denominator = _read_reachable_blobs(root, object_paths)
    boards: set[tuple[int, ...]] = set()
    seed_literals: set[str] = set()
    seed_patterns: set[str] = set()
    standard_2048_text_blob_ids: set[str] = set()
    for fact, raw in blob_rows:
        text = raw.decode("utf-8")
        if "standard-2048" in text or "standard_2048" in text:
            standard_2048_text_blob_ids.add(fact.object_id)
        # The representative path supplied by `rev-list --objects` is not a
        # semantic authority: one blob may have appeared under multiple paths.
        # Every UTF-8 blob is therefore offered unconditionally to both parsers.
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                board = _literal_board(node)
                if board is not None:
                    boards.add(board)
                if isinstance(node, ast.Constant) and type(node.value) is str:
                    if node.value.startswith("standard-2048-"):
                        seed_literals.add(node.value)
                elif isinstance(node, ast.JoinedStr):
                    literal = "".join(
                        value.value
                        for value in node.values
                        if isinstance(value, ast.Constant)
                        and type(value.value) is str
                    )
                    if literal.startswith("standard-2048-"):
                        seed_patterns.add(_joined_string_pattern(node))
        # Canonical JSON evidence can carry list boards that never appeared as
        # Python literals.  Walking the decoded value is deliberately broad.
        try:
            import json

            decoded = json.loads(text)
        except (ValueError, TypeError):
            decoded = None
        stack = [decoded]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                if (
                    len(value) == 16
                    and all(type(rank) is int and rank >= 0 for rank in value)
                ):
                    boards.add(tuple(value))
                stack.extend(value)
            elif type(value) is str and value.startswith("standard-2048-"):
                seed_literals.add(value)
    board_rows = sorted(boards)
    orbit_rows = sorted({_d4_orbit_representative(board) for board in boards})
    literal_rows = sorted(seed_literals)
    pattern_rows = sorted(seed_patterns)
    blob_facts = [fact.document() for fact, _ in blob_rows]
    return {
        "schema": "acfqp.standard_2048_history_scan.v42",
        "schema_version": SCHEMA_VERSION,
        "algorithm": HISTORY_SCAN_ALGORITHM,
        "history_boundary_commit": HISTORY_BOUNDARY_COMMIT,
        "history_boundary_tree": HISTORY_BOUNDARY_TREE,
        "reachable_commit_count": len(commit_ids),
        "reachable_commit_set_sha256": _sha256_json(list(commit_ids)),
        **blob_denominator,
        "scanned_utf8_blob_count": len(blob_facts),
        "scanned_utf8_blob_manifest_sha256": _sha256_json(blob_facts),
        "standard_2048_text_blob_count": len(standard_2048_text_blob_ids),
        "standard_2048_text_blob_id_set_sha256": _sha256_json(
            sorted(standard_2048_text_blob_ids)
        ),
        "literal_board_count": len(board_rows),
        "literal_board_set_sha256": _sha256_json([list(row) for row in board_rows]),
        "d4_orbit_count": len(orbit_rows),
        "d4_orbit_set_sha256": _sha256_json([list(row) for row in orbit_rows]),
        "literal_seed_count": len(literal_rows),
        "literal_seed_set_sha256": _sha256_json(literal_rows),
        "seed_template_count": len(pattern_rows),
        "seed_template_set_sha256": _sha256_json(pattern_rows),
        # Runtime-only material used by freshness tests and omitted from the
        # frozen preregistration document.
        "_literal_boards": board_rows,
        "_d4_orbits": orbit_rows,
        "_literal_seeds": literal_rows,
        "_seed_patterns": pattern_rows,
        "_blob_texts": tuple(raw for _, raw in blob_rows),
    }


def history_scan_summary_v42(scan: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in scan.items() if not key.startswith("_")}


def candidate_freshness_proof_v42(
    scan: dict[str, Any],
    *,
    boards: tuple[tuple[int, ...], ...],
    seeds: tuple[str, ...],
) -> dict[str, Any]:
    if (
        type(boards) is not tuple
        or type(seeds) is not tuple
        or len(boards) != len(seeds)
        or any(
            type(board) is not tuple
            or len(board) != 16
            or any(type(rank) is not int or rank < 0 for rank in board)
            for board in boards
        )
        or any(type(seed) is not str or not seed for seed in seeds)
    ):
        _fail("candidate freshness inputs changed")
    historical_boards = set(scan["_literal_boards"])
    historical_orbits = set(scan["_d4_orbits"])
    historical_seeds = set(scan["_literal_seeds"])
    patterns = tuple(re.compile(pattern) for pattern in scan["_seed_patterns"])
    blob_texts: tuple[bytes, ...] = scan["_blob_texts"]
    board_rows = []
    for board in boards:
        orbit = _d4_orbit_representative(board)
        board_rows.append(
            {
                "board": list(board),
                "board_sha256": _sha256_json(list(board)),
                "d4_orbit_representative": list(orbit),
                "d4_orbit_sha256": _sha256_json(list(orbit)),
                "exact_board_absent_from_history": board not in historical_boards,
                "d4_orbit_absent_from_history": orbit not in historical_orbits,
            }
        )
    seed_rows = []
    for seed in seeds:
        seed_rows.append(
            {
                "seed": seed,
                "seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
                "literal_seed_absent_from_history": seed not in historical_seeds,
                "seed_bytes_absent_from_every_history_blob": all(
                    seed.encode("utf-8") not in raw for raw in blob_texts
                ),
                "seed_not_generated_by_historical_template": not any(
                    pattern.fullmatch(seed) for pattern in patterns
                ),
            }
        )
    pairwise_orbits = {
        tuple(row["d4_orbit_representative"]) for row in board_rows
    }
    return {
        "history_scan_summary": history_scan_summary_v42(scan),
        "candidate_boards": board_rows,
        "candidate_seeds": seed_rows,
        "candidate_board_orbits_pairwise_distinct": len(pairwise_orbits) == len(boards),
        "all_candidates_fresh": all(
            row["exact_board_absent_from_history"]
            and row["d4_orbit_absent_from_history"]
            for row in board_rows
        )
        and all(
            row["literal_seed_absent_from_history"]
            and row["seed_bytes_absent_from_every_history_blob"]
            and row["seed_not_generated_by_historical_template"]
            for row in seed_rows
        )
        and len(pairwise_orbits) == len(boards),
    }


def freeze_history_manifest_v42(
    candidate_proof: dict[str, Any] = FROZEN_CANDIDATE_PROOF,
) -> dict[str, Any]:
    if candidate_proof != FROZEN_CANDIDATE_PROOF:
        _fail("history candidate proof differs from the exact frozen document")
    summary = candidate_proof.get("history_scan_summary")
    if summary != EXPECTED_HISTORY_SCAN_SUMMARY:
        _fail("history scan summary differs from the frozen pre-V42 closure")
    if candidate_proof.get("all_candidates_fresh") is not True:
        _fail("V42 board or seed is not fresh across the complete history closure")
    payload = {
        "schema": "acfqp.standard_2048_history_freshness_manifest.v42",
        "schema_version": SCHEMA_VERSION,
        "history_scan_summary": summary,
        "candidate_boards": candidate_proof["candidate_boards"],
        "candidate_seeds": candidate_proof["candidate_seeds"],
        "candidate_board_orbits_pairwise_distinct": candidate_proof[
            "candidate_board_orbits_pairwise_distinct"
        ],
        "all_candidates_fresh": True,
        "freshness_scope": "GIT_RETAINED_SOURCE_VISIBLE_PRE_V42_CLOSURE_ONLY",
        "unretained_external_or_deleted_history_excluded": True,
        "universal_never_run_claimed": False,
        "live_tmp_diagnostic_used_as_replay_authority": False,
        "outcome_or_tape_materialized": False,
    }
    document = {
        **payload,
        "history_freshness_manifest_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_HISTORY_MANIFEST_V42_DOMAIN, payload
        ),
    }
    if (
        EXPECTED_HISTORY_MANIFEST_ID != "0" * 64
        and document["history_freshness_manifest_id"]
        != EXPECTED_HISTORY_MANIFEST_ID
    ):
        _fail("history freshness manifest identity changed")
    return document


__all__ = (
    "EXPECTED_HISTORY_MANIFEST_ID",
    "EXPECTED_HISTORY_SCAN_SUMMARY",
    "FROZEN_CANDIDATE_PROOF",
    "HISTORY_BOUNDARY_COMMIT",
    "HISTORY_BOUNDARY_TREE",
    "candidate_freshness_proof_v42",
    "freeze_history_manifest_v42",
    "history_scan_summary_v42",
    "scan_standard_2048_git_history_v42",
)
