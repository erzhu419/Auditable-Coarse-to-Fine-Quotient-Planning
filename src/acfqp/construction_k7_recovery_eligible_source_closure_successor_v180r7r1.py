"""Additive reachable-source repair for the failed V180r7 runtime closure.

V180r7 supplied every Python module in ``src/acfqp`` to the frozen V2
construction-source helper.  The repository-wide candidate catalogue had
already grown beyond that helper's 1,024-module cap even though the exact
static closure of the recovery runtime was much smaller.

This successor keeps the V2 helper and its cap unchanged.  It verifies one
explicit caller-supplied, symlink-free catalogue, uses the complete catalogue
of module *names* to resolve the V2 static-import rule, and supplies only the
reachable byte/path subset to ``build_construction_source_closure_v2``.  No
source is imported or executed here.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = (
    "construction_k7_recovery_eligible_source_closure_successor_v180r7r1"
)
PRIMARY_RUNTIME_ROOT_MODULES = (
    "acfqp.construction_k7_recovery_eligible_accounted_runtime_v1",
)
RUNTIME_DYNAMIC_ROOT_PREFIX = "acfqp.v075_"

# The complete repository catalogue is used only to resolve module names.  Its
# bytes are nevertheless replayed against regular, symlink-free files so the
# catalogue attestation cannot be minted from caller-claimed hashes.
MAX_CANDIDATE_CATALOG_MODULES = 4_096
MAX_CANDIDATE_CATALOG_SOURCE_BYTES = 64 * 1024 * 1024

# The unchanged V2 cap and the tighter, successor-specific runtime caps are
# separate denominators and are recorded separately in every repair document.
V2_MAX_REACHABLE_MODULES = source_runtime_v2.MAX_MODULES
MAX_RECOVERY_RUNTIME_FILES = 512
MAX_RECOVERY_RUNTIME_SOURCE_BYTES = 16 * 1024 * 1024
MAX_REPAIR_DOCUMENT_BYTES = 16 * 1024 * 1024

_ISSUER = object()


class ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
    ValueError
):
    """The candidate catalogue, reachable subset, or frozen replay drifted."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
        message
    )


def _valid_module_name(value: Any) -> bool:
    return (
        type(value) is str
        and (value == "acfqp" or value.startswith("acfqp."))
        and all(
            part.isidentifier() and not part.startswith("_abc_invalid_")
            for part in value.split(".")
        )
    )


def _module_relative_path(module_name: str, *, is_package: bool) -> str:
    base = module_name.replace(".", "/")
    return f"{base}/__init__.py" if is_package else f"{base}.py"


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCatalogSourceFactV180r7r1:
    """One exact, portable fact from the complete module-name catalogue."""

    module_name: str
    relative_path: str
    source_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        if type(self.relative_path) is not str:
            _fail("catalogue source fact is malformed")
        try:
            digest = parse_content_id(self.source_sha256)
        except (TypeError, ValueError) as error:
            raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
                "catalogue source digest is not one lowercase SHA-256 identity"
            ) from error
        relative = PurePosixPath(self.relative_path)
        if (
            not _valid_module_name(self.module_name)
            or digest != self.source_sha256
            or relative.is_absolute()
            or ".." in relative.parts
            or self.relative_path
            not in (
                _module_relative_path(self.module_name, is_package=False),
                _module_relative_path(self.module_name, is_package=True),
            )
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or self.source_byte_count
            > source_runtime_v2.MAX_SOURCE_BYTES_PER_MODULE
        ):
            _fail("catalogue source fact is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }


def _facts_sha256(
    facts: tuple[RecoveryEligibleCatalogSourceFactV180r7r1, ...],
) -> str:
    return hashlib.sha256(
        canonical_json_bytes([item.to_document() for item in facts])
    ).hexdigest()


def _names_sha256(names: tuple[str, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(names))).hexdigest()


@dataclass(frozen=True, slots=True)
class RecoveryEligibleSourceClosureRepairV180r7r1:
    """Exact full-catalogue and selected V2-closure repair attestation."""

    _issuer: InitVar[object]
    source_closure: source_runtime_v2.ConstructionSourceClosureV2
    catalog_module_names: tuple[str, ...]
    catalog_source_byte_count: int
    catalog_source_facts_sha256: str
    reachable_source_facts: tuple[
        RecoveryEligibleCatalogSourceFactV180r7r1, ...
    ]
    _repair_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.source_closure)
            is not source_runtime_v2.ConstructionSourceClosureV2
            or type(self.catalog_module_names) is not tuple
            or type(self.catalog_source_byte_count) is not int
            or type(self.catalog_source_facts_sha256) is not str
            or type(self.reachable_source_facts) is not tuple
        ):
            _fail("reachable source closure repair is malformed or caller-minted")
        try:
            catalog_facts_digest = parse_content_id(
                self.catalog_source_facts_sha256
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
                "catalogue source-facts digest is malformed"
            ) from error
        reachable_names = tuple(
            item.module_name for item in self.reachable_source_facts
        )
        reachable_by_name = {
            item.module_name: item for item in self.reachable_source_facts
        }
        closure_facts = tuple(
            reachable_by_name.get(module.module_name)
            for module in self.source_closure.modules
        )
        if (
            not self.catalog_module_names
            or self.catalog_module_names
            != tuple(sorted(set(self.catalog_module_names)))
            or len(self.catalog_module_names) > MAX_CANDIDATE_CATALOG_MODULES
            or any(
                not _valid_module_name(name)
                for name in self.catalog_module_names
            )
            or not (
                0
                < self.catalog_source_byte_count
                <= MAX_CANDIDATE_CATALOG_SOURCE_BYTES
            )
            or catalog_facts_digest != self.catalog_source_facts_sha256
            or not self.reachable_source_facts
            or any(
                type(item) is not RecoveryEligibleCatalogSourceFactV180r7r1
                for item in self.reachable_source_facts
            )
            or reachable_names != tuple(sorted(set(reachable_names)))
            or not set(reachable_names) <= set(self.catalog_module_names)
            or self.source_closure.root_modules
            != _runtime_roots(self.catalog_module_names)
            or reachable_names != self.source_closure.module_names
            or len(reachable_names) > V2_MAX_REACHABLE_MODULES
            or len(reachable_names) > MAX_RECOVERY_RUNTIME_FILES
            or sum(
                item.source_byte_count for item in self.reachable_source_facts
            )
            > MAX_RECOVERY_RUNTIME_SOURCE_BYTES
            or sum(
                item.source_byte_count for item in self.reachable_source_facts
            )
            > self.catalog_source_byte_count
            or closure_facts != self.reachable_source_facts
            or any(
                fact is None
                or fact.relative_path != module.relative_path
                or fact.source_sha256 != module.source_sha256
                or fact.source_byte_count != module.source_byte_count
                for fact, module in zip(
                    closure_facts,
                    self.source_closure.modules,
                    strict=True,
                )
            )
        ):
            _fail("reachable source closure repair is malformed or caller-minted")
        object.__setattr__(
            self,
            "_repair_id",
            domains.extension_content_id_v180r7r1(
                domains.CONSTRUCTION_K7_FALLBACK_SOURCE_CLOSURE_REPAIR_V180R7R1_DOMAIN,
                self._payload(),
            ),
        )
        if len(self.canonical_bytes) > MAX_REPAIR_DOCUMENT_BYTES:
            _fail("reachable source closure repair document exceeds its cap")

    @property
    def reachable_module_names(self) -> tuple[str, ...]:
        return tuple(item.module_name for item in self.reachable_source_facts)

    @property
    def reachable_source_byte_count(self) -> int:
        return sum(
            item.source_byte_count for item in self.reachable_source_facts
        )

    @property
    def catalog_module_names_sha256(self) -> str:
        return _names_sha256(self.catalog_module_names)

    @property
    def reachable_source_facts_sha256(self) -> str:
        return _facts_sha256(self.reachable_source_facts)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_recovery_eligible_source_closure_"
                "repair.v180r7r1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "primary_runtime_root_modules": list(
                PRIMARY_RUNTIME_ROOT_MODULES
            ),
            "runtime_dynamic_root_prefix": RUNTIME_DYNAMIC_ROOT_PREFIX,
            "root_modules": list(self.source_closure.root_modules),
            "candidate_catalog": {
                "module_names": list(self.catalog_module_names),
                "module_count": len(self.catalog_module_names),
                "source_byte_count": self.catalog_source_byte_count,
                "module_cap": MAX_CANDIDATE_CATALOG_MODULES,
                "source_byte_cap": MAX_CANDIDATE_CATALOG_SOURCE_BYTES,
                "module_names_sha256": self.catalog_module_names_sha256,
                "source_facts_sha256": self.catalog_source_facts_sha256,
                "source_facts_digest_rule": (
                    "SHA256_CANONICAL_JSON_ORDERED_MODULE_NAME_RELATIVE_PATH_"
                    "SOURCE_SHA256_SOURCE_BYTE_COUNT"
                ),
                "all_paths_regular_and_symlink_free": True,
                "all_caller_supplied_bytes_replayed": True,
                "used_only_for_exact_module_name_resolution": True,
            },
            "reachable_runtime": {
                "module_names": list(self.reachable_module_names),
                "module_count": len(self.reachable_module_names),
                "source_byte_count": self.reachable_source_byte_count,
                "v2_module_cap": V2_MAX_REACHABLE_MODULES,
                "recovery_runtime_file_cap": MAX_RECOVERY_RUNTIME_FILES,
                "recovery_runtime_source_byte_cap": (
                    MAX_RECOVERY_RUNTIME_SOURCE_BYTES
                ),
                "source_facts_sha256": self.reachable_source_facts_sha256,
                "exact_recursive_static_subset_selected": True,
                "only_selected_mapping_passed_to_unchanged_v2_builder": True,
            },
            "unchanged_v2_source_runtime": {
                "schema_version": source_runtime_v2.SCHEMA_VERSION,
                "profile_key": source_runtime_v2.PROFILE_KEY,
                "closure_rule": source_runtime_v2.STATIC_CLOSURE_RULE,
                "max_modules": source_runtime_v2.MAX_MODULES,
                "max_source_bytes_per_module": (
                    source_runtime_v2.MAX_SOURCE_BYTES_PER_MODULE
                ),
                "v2_constants_mutated": False,
            },
            "source_closure": self.source_closure.to_document(),
            "failed_v180r7_authorization_reused": False,
            "scientific_occurrence_executed": False,
            "target_outcomes_accessed": False,
            "construction_only": True,
            "official_execution_allowed": False,
        }

    @property
    def repair_id(self) -> str:
        current = domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_SOURCE_CLOSURE_REPAIR_V180R7R1_DOMAIN,
            self._payload(),
        )
        if current != self._repair_id:
            _fail("reachable source closure repair changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_closure_repair_id": self.repair_id}


def _validated_catalogue(
    *,
    module_sources: Mapping[str, bytes],
    module_paths: Mapping[str, str | os.PathLike[str]],
) -> tuple[
    dict[str, bytes],
    dict[str, str],
    tuple[RecoveryEligibleCatalogSourceFactV180r7r1, ...],
]:
    if not isinstance(module_sources, Mapping) or not isinstance(
        module_paths, Mapping
    ):
        _fail("source catalogue inputs must be mappings")
    try:
        sources = dict(module_sources)
        supplied_paths = dict(module_paths)
        source_names = set(sources)
        path_names = set(supplied_paths)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
            "source catalogue mappings are malformed"
        ) from error
    if (
        not sources
        or source_names != path_names
        or len(sources) > MAX_CANDIDATE_CATALOG_MODULES
        or "acfqp" not in sources
        or any(not _valid_module_name(name) for name in sources)
        or any(type(raw) is not bytes or not raw for raw in sources.values())
        or any(
            len(raw) > source_runtime_v2.MAX_SOURCE_BYTES_PER_MODULE
            for raw in sources.values()
        )
    ):
        _fail("source catalogue shape is malformed or over its module cap")
    total_source_bytes = sum(len(raw) for raw in sources.values())
    if total_source_bytes > MAX_CANDIDATE_CATALOG_SOURCE_BYTES:
        _fail("source catalogue exceeds its aggregate source-byte cap")

    paths: dict[str, str] = {}
    seen_paths: set[str] = set()
    facts: list[RecoveryEligibleCatalogSourceFactV180r7r1] = []
    for name in sorted(sources):
        try:
            path = Path(supplied_paths[name])
        except TypeError as error:
            raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
                "source catalogue path is not path-like"
            ) from error
        if not path.is_absolute():
            _fail("source catalogue paths must be absolute")
        absolute = Path(os.path.abspath(os.fspath(path)))
        path_key = os.fspath(absolute)
        if path_key in seen_paths:
            _fail("source catalogue maps multiple modules to one path")
        seen_paths.add(path_key)
        is_package = absolute.name == "__init__.py"
        relative_path = _module_relative_path(name, is_package=is_package)
        expected_suffix = PurePosixPath(relative_path).parts
        if tuple(absolute.parts[-len(expected_suffix) :]) != expected_suffix:
            _fail("source catalogue path suffix differs from its module name")
        try:
            live_raw = source_runtime_v2._read_regular_symlink_free(  # noqa: SLF001
                absolute
            )
        except (
            source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation
        ) as error:
            raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
                "source catalogue path is not one stable regular symlink-free file"
            ) from error
        raw = sources[name]
        if live_raw != raw:
            _fail("source catalogue bytes differ from the regular source file")
        paths[name] = path_key
        facts.append(
            RecoveryEligibleCatalogSourceFactV180r7r1(
                name,
                relative_path,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
            )
        )
    if sum(item.source_byte_count for item in facts) != total_source_bytes:
        raise AssertionError("catalogue source-byte sum changed")
    return sources, paths, tuple(facts)


def _runtime_roots(catalog_names: tuple[str, ...]) -> tuple[str, ...]:
    dynamic_roots = tuple(
        name
        for name in catalog_names
        if name.startswith(RUNTIME_DYNAMIC_ROOT_PREFIX)
    )
    roots = tuple(sorted((*PRIMARY_RUNTIME_ROOT_MODULES, *dynamic_roots)))
    if (
        not dynamic_roots
        or roots != tuple(sorted(set(roots)))
        or len(roots) > V2_MAX_REACHABLE_MODULES
        or not set(roots) <= set(catalog_names)
    ):
        _fail("recovery runtime roots are absent, duplicated, or over the V2 cap")
    return roots


def _resolve_reachable_module_names(
    *,
    roots: tuple[str, ...],
    sources: Mapping[str, bytes],
    facts: tuple[RecoveryEligibleCatalogSourceFactV180r7r1, ...],
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    """Resolve with package status taken from exact validated path facts."""

    available = frozenset(sources)
    is_package_by_name = {
        item.module_name: item.relative_path.endswith("/__init__.py")
        for item in facts
    }
    pending = list(reversed(roots))
    included: set[str] = set()
    imports_by_name: dict[str, tuple[str, ...]] = {}
    while pending:
        name = pending.pop()
        if name in included:
            continue
        included.add(name)
        if len(included) > V2_MAX_REACHABLE_MODULES:
            _fail("reachable source closure exceeds the unchanged V2 module cap")
        try:
            imports = source_runtime_v2._local_imports_from_raw(  # noqa: SLF001
                module_name=name,
                is_package=is_package_by_name[name],
                raw=sources[name],
                available_names=available,
            )
        except (
            KeyError,
            source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation,
        ) as error:
            raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
                f"static source resolution failed for {name}"
            ) from error
        imports_by_name[name] = imports
        pending.extend(
            reversed(tuple(item for item in imports if item not in included))
        )
        components = name.split(".")
        for end in range(1, len(components)):
            parent = ".".join(components[:end])
            if parent not in sources:
                _fail(f"reachable source closure omitted parent package: {parent}")
            if parent not in included:
                pending.append(parent)
    return tuple(sorted(included)), imports_by_name


def build_recovery_eligible_source_closure_successor_v180r7r1(
    *,
    module_sources: Mapping[str, bytes],
    module_paths: Mapping[str, str | os.PathLike[str]],
) -> RecoveryEligibleSourceClosureRepairV180r7r1:
    """Select and build the exact bounded recovery-runtime source closure."""

    sources, paths, catalog_facts = _validated_catalogue(
        module_sources=module_sources,
        module_paths=module_paths,
    )
    catalog_names = tuple(item.module_name for item in catalog_facts)
    roots = _runtime_roots(catalog_names)
    reachable_names, imports_by_name = _resolve_reachable_module_names(
        roots=roots,
        sources=sources,
        facts=catalog_facts,
    )
    reachable_source_bytes = sum(len(sources[name]) for name in reachable_names)
    if len(reachable_names) > MAX_RECOVERY_RUNTIME_FILES:
        _fail("reachable recovery runtime exceeds its file cap")
    if reachable_source_bytes > MAX_RECOVERY_RUNTIME_SOURCE_BYTES:
        _fail("reachable recovery runtime exceeds its source-byte cap")

    selected_sources = {name: sources[name] for name in reachable_names}
    selected_paths = {name: paths[name] for name in reachable_names}
    try:
        closure = source_runtime_v2.build_construction_source_closure_v2(
            root_modules=roots,
            module_sources=selected_sources,
            module_paths=selected_paths,
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
            "unchanged V2 builder rejected the selected reachable source subset"
        ) from error
    if (
        type(closure) is not source_runtime_v2.ConstructionSourceClosureV2
        or closure.root_modules != roots
        or closure.module_names != reachable_names
        or any(
            module.static_local_imports != imports_by_name[module.module_name]
            for module in closure.modules
        )
    ):
        _fail("unchanged V2 closure differs from full-catalogue static resolution")
    catalog_by_name = {item.module_name: item for item in catalog_facts}
    reachable_facts = tuple(catalog_by_name[name] for name in reachable_names)
    return RecoveryEligibleSourceClosureRepairV180r7r1(
        _ISSUER,
        closure,
        catalog_names,
        sum(item.source_byte_count for item in catalog_facts),
        _facts_sha256(catalog_facts),
        reachable_facts,
    )


def require_recovery_eligible_source_closure_successor_v180r7r1(
    *,
    module_sources: Mapping[str, bytes],
    module_paths: Mapping[str, str | os.PathLike[str]],
    expected_repair_id: str,
) -> RecoveryEligibleSourceClosureRepairV180r7r1:
    """Rebuild the successor and fail closed unless its frozen ID is exact."""

    try:
        expected = parse_content_id(expected_repair_id)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error(
            "expected source-closure repair ID is malformed"
        ) from error
    result = build_recovery_eligible_source_closure_successor_v180r7r1(
        module_sources=module_sources,
        module_paths=module_paths,
    )
    if result.repair_id != expected:
        _fail("reachable source-closure repair drifted from its frozen identity")
    return result


__all__ = (
    "ConstructionK7RecoveryEligibleSourceClosureSuccessorV180r7r1Error",
    "MAX_CANDIDATE_CATALOG_MODULES",
    "MAX_CANDIDATE_CATALOG_SOURCE_BYTES",
    "MAX_RECOVERY_RUNTIME_FILES",
    "MAX_RECOVERY_RUNTIME_SOURCE_BYTES",
    "MAX_REPAIR_DOCUMENT_BYTES",
    "PRIMARY_RUNTIME_ROOT_MODULES",
    "PROFILE_KEY",
    "RUNTIME_DYNAMIC_ROOT_PREFIX",
    "RecoveryEligibleCatalogSourceFactV180r7r1",
    "RecoveryEligibleSourceClosureRepairV180r7r1",
    "SCHEMA_VERSION",
    "V2_MAX_REACHABLE_MODULES",
    "build_recovery_eligible_source_closure_successor_v180r7r1",
    "require_recovery_eligible_source_closure_successor_v180r7r1",
)
