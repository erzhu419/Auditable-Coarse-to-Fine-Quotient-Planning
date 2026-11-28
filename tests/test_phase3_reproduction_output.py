"""Reproduction entry points must leave published results in place."""
import os
from pathlib import Path

import pytest

import learned_portal_phase3 as phase3


def test_default_stage_outputs_and_release_aliases(tmp_path, monkeypatch):
    release = tmp_path / "learned_portal_phase3"
    release.mkdir()
    monkeypatch.setattr(phase3, "__file__", str(release / "__init__.py"))
    for stage in ("v1", "v2", "r747", "r675", "r7a"):
        output = phase3.phase3_output_directory(stage)
        assert output == tmp_path / ".tmp" / f"{stage}_reproduction"
        assert output.is_dir()

    alias = tmp_path / "alias"
    alias.symlink_to(release, target_is_directory=True)
    for directory in (release, alias):
        with pytest.raises(ValueError, match="separate"):
            phase3.phase3_output_directory("r7a", directory)


def test_custom_output_cannot_follow_links_into_release(tmp_path):
    old = tmp_path / "published.json"
    old.write_text("archived")
    directory = phase3.phase3_output_directory("v1", Path(tmp_path, "custom"))
    link = directory / "p3_neurips_benchmark_results.json"
    for create_link in (link.symlink_to, lambda target: os.link(target, link)):
        create_link(old)
        with pytest.raises(ValueError, match="Linked"):
            phase3.phase3_output_directory("v1", directory)
        link.unlink()
    assert old.read_text() == "archived"
