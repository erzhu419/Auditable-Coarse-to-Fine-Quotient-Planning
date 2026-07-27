"""Optional exact content-ID memoization for immutable test artifacts.

The production schemas deliberately expose content IDs as computed
properties.  Historical integration tests revisit the same frozen object
graph many times, so recomputing an identical canonical serialization can
dominate test runtime.  This pytest plugin memoizes only successful ID
property evaluations on the same frozen object identity.

The plugin is a test-execution optimization.  It does not skip tests, cache
planner results, alter samples, or replace any production algorithm.  Test
modules containing explicit in-place mutation attacks are detected during
collection and run with the original fresh property evaluation.
"""

from __future__ import annotations

from dataclasses import is_dataclass
import functools
import inspect
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable


PLUGIN_ID = "acfqp_exact_content_id_memoization_v1"

# These modules contain the large immutable artifact graphs shared by the
# historical H1/H2 construction and proof Gates.  The allowlist keeps the
# optimization narrow and independently auditable.
MODULE_ALLOWLIST = frozenset(
    {
        "acfqp.certificate_memoization_v1",
        "acfqp.cross_query_promotion_v1",
        "acfqp.h2_durable_proof_state_v1",
        "acfqp.h2_interleaved_durable_epoch_v1",
        "acfqp.h2_temporal_incremental_proof_dag_v1",
        "acfqp.heldout_family_amortization_v1",
        "acfqp.incremental_proof_dag_v1",
        "acfqp.live_query_local_epoch_invalidation_v1",
        "acfqp.multistep_query_refinement_v1",
        "acfqp.observation_partial_rapm_v1",
        "acfqp.observed_typed_coordinate_synthesis_v1",
        "acfqp.partial_model_planner_v1",
        "acfqp.partial_sound_audit_v1",
        "acfqp.query_local_refinement_v1",
    }
)

# Memoizing a content ID across an intentional mutation of the same frozen
# instance would invalidate the attack.  Such modules must retain fresh ID
# evaluation.  The scan is conservative and performed before any fixture.
UNSAFE_SOURCE_MARKERS = (
    "object.__setattr__",
    ".__dict__[",
)


class _PropertyCache:
    """Identity-keyed strong cache with exact object reuse checks."""

    __slots__ = ("entries", "hits", "misses")

    def __init__(self) -> None:
        self.entries: dict[int, tuple[object, str]] = {}
        self.hits = 0
        self.misses = 0

    def resolve(
        self,
        instance: object,
        evaluator: Callable[[object], str],
    ) -> str:
        key = id(instance)
        cached = self.entries.get(key)
        if cached is not None and cached[0] is instance:
            self.hits += 1
            return cached[1]
        value = evaluator(instance)
        if type(value) is not str:
            # Preserve the production property's exact behavior for any
            # non-content-ID property accidentally matching the name rule.
            return value
        self.entries[key] = (instance, value)
        self.misses += 1
        return value


_CACHES: list[_PropertyCache] = []
_PATCHED_PROPERTIES: list[str] = []
_DISABLED_REASON: str | None = None


def _source_is_mutation_attack(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return True
    return any(marker in source for marker in UNSAFE_SOURCE_MARKERS)


def _collected_test_paths(session: Any) -> tuple[Path, ...]:
    return tuple(
        sorted(
            {
                Path(str(item.path)).resolve()
                for item in session.items
                if getattr(item, "path", None) is not None
            }
        )
    )


def _patch_module(module: ModuleType) -> int:
    patched = 0
    for candidate in tuple(vars(module).values()):
        if (
            not inspect.isclass(candidate)
            or candidate.__module__ != module.__name__
            or not is_dataclass(candidate)
        ):
            continue
        parameters = getattr(candidate, "__dataclass_params__", None)
        if parameters is None or not parameters.frozen:
            continue
        for name, descriptor in tuple(vars(candidate).items()):
            if (
                not isinstance(descriptor, property)
                or not name.endswith("_id")
                or descriptor.fget is None
                or descriptor.fset is not None
            ):
                continue
            original = descriptor.fget
            cache = _PropertyCache()

            @functools.wraps(original)
            def cached_property(
                instance: object,
                _original: Callable[[object], str] = original,
                _cache: _PropertyCache = cache,
            ) -> str:
                return _cache.resolve(instance, _original)

            setattr(
                candidate,
                name,
                property(
                    cached_property,
                    None,
                    descriptor.fdel,
                    descriptor.__doc__,
                ),
            )
            _CACHES.append(cache)
            _PATCHED_PROPERTIES.append(
                f"{module.__name__}.{candidate.__name__}.{name}"
            )
            patched += 1
    return patched


def pytest_collection_finish(session: Any) -> None:
    """Patch after collection, before module/session fixtures execute."""

    global _DISABLED_REASON
    unsafe = tuple(
        path
        for path in _collected_test_paths(session)
        if _source_is_mutation_attack(path)
    )
    if unsafe:
        _DISABLED_REASON = (
            "in-place mutation attack module collected: "
            + ", ".join(path.name for path in unsafe)
        )
        return
    for module_name in sorted(MODULE_ALLOWLIST):
        module = sys.modules.get(module_name)
        if module is not None:
            _patch_module(module)


def pytest_terminal_summary(
    terminalreporter: Any,
    exitstatus: int,
    config: Any,
) -> None:
    """Expose exact cache use without changing pytest's result semantics."""

    del exitstatus, config
    if _DISABLED_REASON is not None:
        terminalreporter.write_line(
            f"{PLUGIN_ID}: fresh ({_DISABLED_REASON})"
        )
        return
    hits = sum(cache.hits for cache in _CACHES)
    misses = sum(cache.misses for cache in _CACHES)
    terminalreporter.write_line(
        f"{PLUGIN_ID}: {len(_PATCHED_PROPERTIES)} properties, "
        f"{hits} exact hits, {misses} first evaluations"
    )
