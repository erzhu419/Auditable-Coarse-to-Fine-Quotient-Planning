from __future__ import annotations

import hashlib
from pathlib import Path
import stat

import pytest

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import preregister_v180r7r1_source_catalog_manifest as manifest


def _manifest_document() -> dict[str, object]:
    if manifest.OUTPUT_PATH.exists():
        raw = manifest.OUTPUT_PATH.read_bytes()
        document = loads_canonical_json(raw)
        assert type(document) is dict
        assert canonical_json_bytes(document) == raw
        return document
    return manifest.build_v180r7r1_source_catalog_manifest()


def test_v180r7r1_source_catalog_manifest_is_exact_and_outcome_free() -> None:
    document = _manifest_document()
    assert document["source_boundary_commit"] == (
        "0d9d32dcb2aa3652696ccc0b5010dfc39455e8af"
    )
    assert document["source_inventory_preregistration_id"] == (
        "30a0aa732e44389f9b246a3664bacf13f5465233c7a1e3a1782baac80dbf38b8"
    )
    assert document["source_catalog_module_count"] == 1_955
    assert document["source_catalog_source_byte_count"] == 49_484_313
    facts = document["source_catalog_facts"]
    assert len(facts) == 1_955
    assert [row["module_name"] for row in facts] == sorted(
        {row["module_name"] for row in facts}
    )
    assert hashlib.sha256(canonical_json_bytes(facts)).hexdigest() == document[
        "source_catalog_facts_sha256"
    ]
    repair = document["source_closure_repair"]
    assert repair["candidate_catalog"]["module_count"] == 1_955
    assert repair["candidate_catalog"]["source_byte_count"] == 49_484_313
    assert repair["candidate_catalog"]["source_facts_sha256"] == document[
        "source_catalog_facts_sha256"
    ]
    assert len(repair["root_modules"]) == 151
    assert repair["reachable_runtime"]["module_count"] == 307
    assert repair["reachable_runtime"]["source_byte_count"] == 15_129_926
    assert document["source_catalog_manifest_id"] == manifest._content_id(
        {
            key: value
            for key, value in document.items()
            if key != "source_catalog_manifest_id"
        }
    )
    assert document["fresh_execution_authorization_issued"] is False
    assert document["fresh_fallback_execution_started"] is False
    assert document["scientific_occurrence_executed"] is False
    assert document["production_outcome_accessed"] is False
    assert document["success_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["construction_only"] is True


def test_v180r7r1_manifest_embeds_every_committed_file_fact() -> None:
    document = _manifest_document()
    for fact in document["source_catalog_facts"]:
        raw = (manifest.ROOT / "src" / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["source_byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["source_sha256"]
    producer = document["manifest_producer_source_fact"]
    producer_raw = manifest.Path(__file__).resolve().parents[1] / producer[
        "relative_path"
    ]
    raw = producer_raw.read_bytes()
    assert len(raw) == producer["byte_count"]
    assert hashlib.sha256(raw).hexdigest() == producer["sha256"]
    assert producer["excluded_from_frozen_worker_source_catalog"] is True
    assert document["manifest_identity_hardcoded_in_catalogued_source"] is False


def test_v180r7r1_manifest_domain_and_source_avoid_an_identity_cycle() -> None:
    assert manifest.SOURCE_CATALOG_MANIFEST_DOMAIN == (
        "acfqp:construction-k7-full-ground-fallback-source-catalog-manifest:"
        "v180r7r1"
    )
    source = Path(manifest.__file__).read_text(encoding="utf-8")
    assert "EXPECTED_MANIFEST_ID" not in source
    assert "source_catalog_manifest_id\": _content_id(payload)" in source
    assert str(Path("scripts/preregister_v180r7r1_source_catalog_manifest.py")) not in {
        row["relative_path"]
        for row in _manifest_document()["source_catalog_facts"]
    }


def test_v180r7r1_manifest_write_is_o_excl_and_fsyncs_file_and_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "manifest.json"
    fsync_descriptors: list[int] = []
    monkeypatch.setattr(manifest.os, "fsync", fsync_descriptors.append)
    manifest._write_once(target, b"{}")
    assert target.read_bytes() == b"{}"
    assert stat.S_IMODE(target.stat().st_mode) == 0o400
    assert len(fsync_descriptors) == 2
    with pytest.raises(FileExistsError):
        manifest._write_once(target, b"{}")


def test_v180r7r1_manifest_main_is_fixed_to_the_precommitted_path() -> None:
    source = Path(manifest.__file__).read_text(encoding="utf-8")
    assert "v180r7r1_source_catalog_manifest.json" in source
    assert "os.O_EXCL" in source
    assert "os.fsync(descriptor)" in source
    assert "os.fsync(directory)" in source
    assert "if OUTPUT_PATH.exists()" in source
