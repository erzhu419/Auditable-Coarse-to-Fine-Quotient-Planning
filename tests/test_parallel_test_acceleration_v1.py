"""Regressions for exact immutable content-ID test memoization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests import acfqp_exact_id_cache_v1 as cache_module


@dataclass(frozen=True, slots=True)
class _FrozenArtifact:
    payload: str

    @property
    def artifact_id(self) -> str:
        return f"id:{self.payload}"


def test_identity_cache_returns_exact_first_value_without_cross_object_reuse():
    calls = 0
    cache = cache_module._PropertyCache()

    def evaluate(instance: object) -> str:
        nonlocal calls
        calls += 1
        assert type(instance) is _FrozenArtifact
        return instance.artifact_id

    first = _FrozenArtifact("same")
    second = _FrozenArtifact("same")
    assert cache.resolve(first, evaluate) == "id:same"
    assert cache.resolve(first, evaluate) == "id:same"
    assert cache.resolve(second, evaluate) == "id:same"
    assert calls == 2
    assert (cache.hits, cache.misses) == (1, 2)


def test_in_place_mutation_attack_detection_is_conservative(tmp_path: Path):
    safe = tmp_path / "test_safe.py"
    safe.write_text("value = 1\n", encoding="utf-8")
    unsafe = tmp_path / "test_attack.py"
    unsafe.write_text(
        "object.__setattr__(target, 'field', value)\n",
        encoding="utf-8",
    )
    assert cache_module._source_is_mutation_attack(safe) is False
    assert cache_module._source_is_mutation_attack(unsafe) is True
    assert cache_module._source_is_mutation_attack(
        tmp_path / "missing.py"
    ) is True
