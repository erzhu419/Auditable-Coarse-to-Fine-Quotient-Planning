"""No-ground current-identity candidate for the canonical H1 fallback.

Contract 2.0.52 slice 1 separates expensive semantic establishment from the
route-time identity join.  A build/evaluation issuer first projects the
registered current Phase-0.5 source into independent build/kernel and query
attestations.  A second issuer verifies claimant durable-proof bytes against
that already-issued identity, validates the retained verifier handle, and
binds it to a real selected plan.  Only then may the route-time candidate join
those two attestations to the exact H1 recipe.

The route-time freezer and its bytes verifier do not accept proof bytes, a
bundle path, a caller-supplied identity, or caller-supplied zero counters.
They do not invoke the durable-proof verifier, a kernel, outcome enumeration,
J0, a planner, or a fallback solver.  The source archive accepted by this
construction slice is only a caller-supplied, self-consistent compile fixture.
It is not evidence that those bytes are the live/current issuer source and is
not issuer-code provenance.

Route-time call counts are explicitly UNOBSERVED.  The module records only a
forbidden-API declaration until a later observed access log exists.  The
module-level retention registries are defense in depth for ordinary callers;
no same-process unforgeability is claimed against an adversary that can mutate
private module state.  This module therefore issues one construction candidate
only.  Every production consumer must reject it as an authority.  It does not
authorize the formal V7 route decision, production execution, CounterRecords,
vectors, terminal closure, or either Phase-3E Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from fractions import Fraction
import hashlib
import hmac
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp.construction_k7_h1_direct_fallback_two_role_recipe_v1 import (
    H1DirectFallbackTwoRoleRecipeV1,
)
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    DurableProofVerificationOutcomeV1,
    VerifiedDurableProofCacheConsumptionV1,
    bind_verified_durable_exact_infeasibility_to_plan_v1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
    verify_phase3e_exact_infeasibility_durable_proof_bytes_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN,
    PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.52"
PROFILE_KEY = "construction_k7_h1_production_current_identity_v1"

CONSTRUCTION_ONLY = True
PRODUCTION_CURRENT_IDENTITY_CANDIDATE_PRESENT = True
PRODUCTION_CURRENT_IDENTITY_AUTHORITY_PRESENT = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

BUILD_KERNEL_DOMAIN = (
    CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN
)
QUERY_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN
CURRENT_SOURCE_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN
PROOF_MATCH_DOMAIN = (
    CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN
)
CURRENT_IDENTITY_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN
)
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    BUILD_KERNEL_DOMAIN,
    QUERY_DOMAIN,
    CURRENT_SOURCE_DOMAIN,
    PROOF_MATCH_DOMAIN,
    CURRENT_IDENTITY_DOMAIN,
    VERIFICATION_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - import-time registry invariant
    raise RuntimeError("H1 current-identity domains are not uniquely registered")

SOURCE_ARCHIVE_ROOT_MODULES = tuple(
    sorted(
        (
            "acfqp.construction_k7_h1_production_current_identity_v1",
            "acfqp.phase3e_exact_infeasibility_durable_proof_v1",
        )
    )
)

EXPECTED_CURRENT_PROOF_ID = (
    "9f682a2c1b6e9ce1e697b9910e01b41180353eae24a9d5f720e071b802b6a6c8"
)
EXPECTED_CURRENT_PROOF_SHA256 = (
    "d795e6cdca04070632912c0f9cfe0a2e49f14710020fb2481c5a43aa892ed1ca"
)
EXPECTED_CURRENT_PROOF_BYTE_COUNT = 37591
EXPECTED_H1_PREEXECUTION_BYTE_COUNT = 20999
EXPECTED_CURRENT_SOURCE_PROJECTION_ID = (
    "5d0608b23694579b3c54456a2ba50f5a546b0b3c9cac09c3df49639486528879"
)
EXPECTED_CURRENT_IDENTITY = DurableExactInfeasibilityIdentityV1(
    "3c689610f7b5358b45d0064d7c4bd861e29b0d713e195c14d31fd3409b8ed772",
    "8e9efba98884756a3fff0cc3e13bec933004f1d09641ebc37935ec810566675b",
    "ed53cf49bb895269269bf4b8c8e5aca18fd47ade8118cdb0dc7ca515cfce7479",
    "c8f347139f268539030d19707322f34ab23d6c0997077879363443d4547d5e3c",
    "cbd5c4fe5354087101b37eb3f6a835231ef57234fef3a3a8d6eb4079c3cc6e4f",
    "b5a66f43f6355237d4f6ec3259cbeb843f10745cb4fc5163750810d8776dfac4",
    "d81f993f15dfc17c63deb7c220cf7cc7a91c9c35e473203a2e2d07fb563a2314",
    "deb6e10fac7a4044f261d21f1044726d7e211a435ac9fd6f9e306586a638bece",
)

EXPECTED_H1_RECIPE_CHAIN = MappingProxyType(
    {
        "recipe_id": "ff4bbaf12d2b52fec981f4c40fbfed1bdc2de8d287ec4eaa3de926b693f3e711",
        "preexecution_sha256": "2c5cb193388ac80a80542858d2f2679e2df097fa57d619c25b591b54b824f370",
        "preexecution_candidate_id": "ec46c1a2cc2f9a541e805b16c11ffbcdf1bef703a6bc0710cb1c7c563d5d7b04",
        "current_identity_attestation_id": "3939cca957ccbafcac790bb1283780936fb9d2d10bd442afa1d49019452b08f5",
        "route_decision_context_id": "377e85bcad571f37c64daae5d3cc86211a431a765d3a627013785f860b54d9f1",
        "decision_point_id": "03579a219ba85f7c73d8a96fe2280aa712019ea267599e4ccdb788f82afbe88c",
        "ground_fallback_cap_profile_id": "ede7f5d85e78b4250dae462e215c019a15f074bc9ba025a853a08283a428e3ea",
        "ground_fallback_cardinality_bound_id": "9adf14f196e9c0eb4d10a76cdb2d50d4e03f9590f68afad6f393ff5de914dad9",
        "cardinality_evidence_id": "47f5137a8a214a82db40aef78dcac63acc02adf0ee2ed8e364dfd2573655d22e",
        "route_upper_formula_id": "ed1fa7a5340ac7259403dbadb32a24087793a28a8064ff3a54d429c7538e42c5",
        "route_upper_derivation_proof_id": "499e02d7324352789a17bc27608c0d93ed0e92ce831b514443b2839046ece4b8",
        "route_upper_id": "81519c729e256599c69a1dd274fa5cd783a8da8a2a4a186bb588bbf984892f0c",
        "route_decision_id": "5971678fbb5a50b4c3b53544c218265d14e032b31bb81c72c1a6d07ac633e3a4",
        "selected_plan_id": "b766e2a06ee20b9f8eb7dfbb07f7e98907a936afb6b2aa82b489f5c53ee7ac35",
        "logical_occurrence_id": "cf55df626af7aa241dd6310ea1bfca1df441144661693940ee9c26253d768c16",
        "route_attempt_id": "925dd4f785597276420ffe7250e9b450dd8ef94ec289b78851295e13bfbe1edb",
    }
)

_BUILD_KERNEL_ISSUER = object()
_QUERY_ISSUER = object()
_CURRENT_SOURCE_ISSUER = object()
_PROOF_MATCH_ISSUER = object()
_CURRENT_IDENTITY_ISSUER = object()
_VERIFICATION_ISSUER = object()
_LIVE: dict[int, tuple[object, str, bytes]] = {}
_PENDING_ISSUANCE: dict[int, tuple[object, str]] = {}
_FROZEN_GETFRAME = sys._getframe  # noqa: SLF001


class ConstructionK7H1ProductionCurrentIdentityV1Error(ValueError):
    """The independent current-source/proof/recipe join is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ProductionCurrentIdentityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _document_bytes(value: Mapping[str, Any], label: str) -> bytes:
    if type(value) is not dict:
        _fail(f"{label} must be one exact object")
    try:
        raw = canonical_json_bytes(dict(value))
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            f"{label} is outside the canonical value language"
        ) from error
    _canonical_document(raw, label)
    return raw


_ISSUANCE_KEY_BY_ROLE = {
    "H1_CURRENT_BUILD_KERNEL_ATTESTATION": "CURRENT_SOURCE",
    "H1_CURRENT_QUERY_ATTESTATION": "CURRENT_SOURCE",
    "H1_CURRENT_SOURCE_FIXTURE": "CURRENT_SOURCE",
    "H1_DURABLE_PROOF_MATCH_ATTESTATION": "PROOF_MATCH",
    "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE": "CURRENT_IDENTITY_CANDIDATE",
    "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE_VERIFICATION": (
        "CANDIDATE_VERIFICATION"
    ),
}
_ISSUER_BY_ROLE = {
    "H1_CURRENT_BUILD_KERNEL_ATTESTATION": _BUILD_KERNEL_ISSUER,
    "H1_CURRENT_QUERY_ATTESTATION": _QUERY_ISSUER,
    "H1_CURRENT_SOURCE_FIXTURE": _CURRENT_SOURCE_ISSUER,
    "H1_DURABLE_PROOF_MATCH_ATTESTATION": _PROOF_MATCH_ISSUER,
    "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE": _CURRENT_IDENTITY_ISSUER,
    "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE_VERIFICATION": (
        _VERIFICATION_ISSUER
    ),
}


def _mark_exact_issuance(issuer: object, value: object, role: str) -> None:
    """Require dataclass init -> exact public issuer ancestry once."""

    try:
        generated_init_frame = _FROZEN_GETFRAME(2)
        public_issuer_frame = _FROZEN_GETFRAME(3)
        key = _ISSUANCE_KEY_BY_ROLE[role]
        expected_code = _FROZEN_PUBLIC_ISSUER_CODES[key]
        expected_issuer = _ISSUER_BY_ROLE[role]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "H1 current-identity issuance ancestry is unavailable"
        ) from error
    if (
        issuer is not expected_issuer
        or generated_init_frame.f_code is not type(value).__init__.__code__
        or public_issuer_frame.f_globals is not _FROZEN_PUBLIC_ISSUER_GLOBALS
        or public_issuer_frame.f_code is not expected_code
        or id(value) in _PENDING_ISSUANCE
        or id(value) in _LIVE
    ):
        _fail(f"{role} bypassed its exact public issuer")
    _PENDING_ISSUANCE[id(value)] = (value, role)


def _retain(value: object, role: str, document: Mapping[str, Any]) -> None:
    raw = canonical_json_bytes(dict(document))
    try:
        caller = _FROZEN_GETFRAME(1)
        expected_code = _FROZEN_PUBLIC_ISSUER_CODES[_ISSUANCE_KEY_BY_ROLE[role]]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "H1 current-identity retention ancestry is unavailable"
        ) from error
    pending = _PENDING_ISSUANCE.get(id(value))
    if (
        pending is None
        or pending[0] is not value
        or pending[1] != role
        or caller.f_globals is not _FROZEN_PUBLIC_ISSUER_GLOBALS
        or caller.f_code is not expected_code
        or id(value) in _LIVE
    ):
        _fail(f"{role} was not produced by its exact public issuer")
    del _PENDING_ISSUANCE[id(value)]
    _LIVE[id(value)] = (value, role, raw)


def _require_live(value: object, role: str, document: Mapping[str, Any]) -> None:
    retained = _LIVE.get(id(value))
    raw = canonical_json_bytes(dict(document))
    if (
        retained is None
        or retained[0] is not value
        or retained[1] != role
        or not hmac.compare_digest(retained[2], raw)
    ):
        _fail(f"{role} is copied, stale, mutated, or caller-minted")


def _profile_id(domain: str, raw: bytes, label: str) -> str:
    return content_id(domain, _canonical_document(raw, label))


def _visible_recipe_projection(
    recipe: H1DirectFallbackTwoRoleRecipeV1,
) -> dict[str, str]:
    if type(recipe) is not H1DirectFallbackTwoRoleRecipeV1:
        _fail("H1 current identity requires the exact typed H1 recipe")
    source = recipe.source
    return {
        "recipe_id": recipe.recipe_id,
        "preexecution_sha256": source.preexecution_sha256,
        "preexecution_candidate_id": source.preexecution_candidate_id,
        "current_identity_attestation_id": source.current_identity_attestation_id,
        "route_decision_context_id": source.route_decision_context_id,
        "decision_point_id": source.decision_point_id,
        "route_upper_id": source.legacy_selected_upper_id,
        "route_decision_id": source.legacy_route_decision_id,
        "selected_plan_id": source.selected_plan_id,
        "logical_occurrence_id": source.logical_occurrence_id,
        "route_attempt_id": source.route_attempt_id,
    }


def _preexecution_nested_id(
    document: Mapping[str, Any], object_name: str, field_name: str
) -> str:
    selected = document.get(object_name)
    if type(selected) is not dict:
        _fail(f"H1 preexecution candidate lacks exact {object_name} bytes")
    return _cid(selected.get(field_name), f"{object_name}.{field_name}")


def _exact_preregistered_recipe_chain(
    recipe: H1DirectFallbackTwoRoleRecipeV1,
    *,
    preexecution_candidate_bytes: bytes,
) -> dict[str, str]:
    """Observe the complete chain from the exact preexecution bytes.

    Digest and embedded-ID matching deliberately precede recipe-registry or
    typed projection access.  The five identities omitted by the legacy
    ``LegacyH1PreexecutionProjectionV1`` are read from the verified bytes;
    they are never filled from the expected-identity table.
    """

    if (
        type(preexecution_candidate_bytes) is not bytes
        or len(preexecution_candidate_bytes) != EXPECTED_H1_PREEXECUTION_BYTE_COUNT
        or not hmac.compare_digest(
            _sha256(preexecution_candidate_bytes),
            EXPECTED_H1_RECIPE_CHAIN["preexecution_sha256"],
        )
    ):
        _fail("H1 preexecution candidate bytes do not match the preregistered digest")
    document = _canonical_document(
        preexecution_candidate_bytes, "H1 preexecution candidate"
    )
    supplied_id = _cid(
        document.get("direct_fallback_preexecution_candidate_id"),
        "H1 preexecution candidate",
    )
    payload = dict(document)
    payload.pop("direct_fallback_preexecution_candidate_id", None)
    if (
        supplied_id != EXPECTED_H1_RECIPE_CHAIN["preexecution_candidate_id"]
        or not hmac.compare_digest(
            content_id(
                CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
                payload,
            ),
            supplied_id,
        )
    ):
        _fail("H1 preexecution candidate embedded identity is not preregistered")
    hidden_recipe_chain = {
        "ground_fallback_cap_profile_id": _preexecution_nested_id(
            document, "cap_profile", "ground_fallback_cap_profile_id"
        ),
        "ground_fallback_cardinality_bound_id": _preexecution_nested_id(
            document,
            "cardinality_bound",
            "ground_fallback_cardinality_bound_id",
        ),
        "cardinality_evidence_id": _preexecution_nested_id(
            document, "cardinality", "cardinality_evidence_id"
        ),
        "route_upper_formula_id": _preexecution_nested_id(
            document, "route_upper_formula", "formula_id"
        ),
        "route_upper_derivation_proof_id": _preexecution_nested_id(
            document, "route_upper_derivation_proof", "derivation_proof_id"
        ),
    }
    try:
        replayed_recipe = recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1(
            raw=recipe.canonical_bytes,
            preexecution_candidate_bytes=preexecution_candidate_bytes,
        )
    except (TypeError, ValueError, recipe_v1.ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "H1 recipe does not replay from the exact preexecution bytes"
        ) from error
    visible = _visible_recipe_projection(replayed_recipe)
    observed = {
        **visible,
        **hidden_recipe_chain,
    }
    if (
        replayed_recipe.to_document() != recipe.to_document()
        or observed != dict(EXPECTED_H1_RECIPE_CHAIN)
    ):
        _fail("H1 recipe is not the preregistered Contract-2.0.50 chain")
    return observed


@dataclass(frozen=True, slots=True)
class H1CurrentBuildKernelAttestationV1:
    """Build-lane source, structure, kernel-law and BuildEpoch attestation."""

    _issuer: InitVar[object]
    current_source_proof_id: str
    current_source_proof_sha256: str
    current_source_proof_byte_count: int
    current_source_verification_id: str
    structural_profile_bytes: bytes = field(repr=False)
    source_projection_bytes: bytes = field(repr=False)
    kernel_profile_bytes: bytes = field(repr=False)
    build_epoch_bytes: bytes = field(repr=False)
    source_closure_id: str
    source_archive_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    runtime_lock_verification_id: str
    archive_compile_verification_id: str
    source_module_ids: tuple[str, ...]
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUILD_KERNEL_ISSUER:
            _fail("H1 current build/kernel attestation is caller-minted")
        for value, label in (
            (self.current_source_proof_id, "current-source proof"),
            (self.current_source_proof_sha256, "current-source proof digest"),
            (self.current_source_verification_id, "current-source verification"),
            (self.source_closure_id, "current source closure"),
            (self.source_archive_id, "current source archive"),
            (self.source_archive_sha256, "current source archive digest"),
            (self.runtime_lock_verification_id, "runtime lock verification"),
            (self.archive_compile_verification_id, "archive compile verification"),
        ):
            _cid(value, label)
        for module_id in self.source_module_ids:
            _cid(module_id, "current source module")
        if (
            type(self.current_source_proof_byte_count) is not int
            or self.current_source_proof_byte_count <= 0
            or type(self.source_archive_byte_count) is not int
            or self.source_archive_byte_count <= 0
            or type(self.source_module_ids) is not tuple
            or not self.source_module_ids
            or len(set(self.source_module_ids)) != len(self.source_module_ids)
        ):
            _fail("H1 current build/kernel extents or source members are invalid")
        structural = self.structural_profile
        source = self.source_projection
        kernel = self.kernel_profile
        build = self.build_epoch
        if (
            kernel.get("structural_id") != self.structural_id
            or build.get("kernel_id") != self.kernel_id
            or build.get("source_projection_id") != self.source_projection_id
        ):
            _fail("H1 current build/kernel profile crosswalk is invalid")
        object.__setattr__(
            self,
            "_attestation_id",
            content_id(BUILD_KERNEL_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(
            _issuer, self, "H1_CURRENT_BUILD_KERNEL_ATTESTATION"
        )

    @property
    def structural_profile(self) -> dict[str, Any]:
        return _canonical_document(
            self.structural_profile_bytes, "current structural profile"
        )

    @property
    def source_projection(self) -> dict[str, Any]:
        return _canonical_document(
            self.source_projection_bytes, "current source projection"
        )

    @property
    def kernel_profile(self) -> dict[str, Any]:
        return _canonical_document(self.kernel_profile_bytes, "current kernel profile")

    @property
    def build_epoch(self) -> dict[str, Any]:
        return _canonical_document(self.build_epoch_bytes, "current BuildEpoch")

    @property
    def structural_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN,
            self.structural_profile_bytes,
            "current structural profile",
        )

    @property
    def source_projection_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN,
            self.source_projection_bytes,
            "current source projection",
        )

    @property
    def kernel_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN,
            self.kernel_profile_bytes,
            "current kernel profile",
        )

    @property
    def build_epoch_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN,
            self.build_epoch_bytes,
            "current BuildEpoch",
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_build_kernel_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "current_source_proof_id": self.current_source_proof_id,
            "current_source_proof_sha256": self.current_source_proof_sha256,
            "current_source_proof_byte_count": self.current_source_proof_byte_count,
            "current_source_verification_id": self.current_source_verification_id,
            "structural_profile": self.structural_profile,
            "structural_id": self.structural_id,
            "source_projection": self.source_projection,
            "source_projection_id": self.source_projection_id,
            "kernel_profile": self.kernel_profile,
            "kernel_id": self.kernel_id,
            "build_epoch": self.build_epoch,
            "BuildEpoch_id": self.build_epoch_id,
            "source_closure_id": self.source_closure_id,
            "source_archive_id": self.source_archive_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "runtime_lock_verification_id": self.runtime_lock_verification_id,
            "archive_compile_verification_id": self.archive_compile_verification_id,
            "source_module_ids": list(self.source_module_ids),
            "current_source_role": (
                "PREREGISTERED_PROOF_DERIVED_CURRENT_SOURCE_CANDIDATE"
            ),
            "preregistered_current_identity_id": (
                EXPECTED_CURRENT_IDENTITY.exact_infeasibility_identity_id
            ),
            "preregistered_source_projection_id": (
                EXPECTED_CURRENT_SOURCE_PROJECTION_ID
            ),
            "selected_bundle_bytes_matched_before_semantic_verifier": True,
            "current_identity_derived_from_selected_bundle_output": False,
            "claimant_proof_input_accepted": False,
            "semantic_replay_lane": "EVALUATION",
            "archived_code_executed_by_compile_verifier": False,
            "loaded_source_manifest_claimed": False,
            "source_archive_role": (
                "CALLER_SUPPLIED_SELF_CONSISTENT_COMPILE_FIXTURE"
            ),
            "source_archive_proves_live_current_issuer_source": False,
            "source_archive_proves_issuer_code_provenance": False,
            "source_archive_semantic_authority": False,
            "construction_only": True,
        }

    @property
    def attestation_id(self) -> str:
        document = self._payload()
        _require_live(self, "H1_CURRENT_BUILD_KERNEL_ATTESTATION", document)
        if content_id(BUILD_KERNEL_DOMAIN, document) != self._attestation_id:
            _fail("H1 current build/kernel attestation identity changed")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "build_kernel_attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class H1CurrentQueryAttestationV1:
    """Build-lane authenticated QuerySpec and policy/search profile projection."""

    _issuer: InitVar[object]
    current_source_proof_id: str
    current_source_verification_id: str
    query_profile_bytes: bytes = field(repr=False)
    threshold_profile_bytes: bytes = field(repr=False)
    reward_profile_bytes: bytes = field(repr=False)
    policy_class_profile_bytes: bytes = field(repr=False)
    complete_search_profile_bytes: bytes = field(repr=False)
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("H1 current query attestation is caller-minted")
        _cid(self.current_source_proof_id, "current-source proof")
        _cid(self.current_source_verification_id, "current-source verification")
        query = self.query_profile
        threshold = self.threshold_profile
        reward = self.reward_profile
        policy = self.policy_class_profile
        search = self.complete_search_profile
        if (
            query.get("horizon") != 1
            or query.get("goal") != "default"
            or type(query.get("initial_distribution")) is not list
            or len(query["initial_distribution"]) != 8
            or threshold.get("delta") != Fraction(1, 20)
            or reward.get("reward_weights")
            != [{"feature": "merge", "coefficient": Fraction(1)}]
            or reward.get("normalizer") != Fraction(1)
            or reward.get("normalizer_proof_id")
            != "g2048.canonical.merge_le_1_per_step.total_le_h.v1"
            or policy.get("policy_class")
            != "deterministic_finite_horizon_markov"
            or search.get("algorithm")
            != "complete_h1_deterministic_markov_enumeration"
            or search.get("search_complete") is not True
            or search.get("cap_exhausted") is not False
        ):
            _fail("H1 current query/search profile is not canonical")
        object.__setattr__(
            self,
            "_attestation_id",
            content_id(QUERY_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(_issuer, self, "H1_CURRENT_QUERY_ATTESTATION")

    @property
    def query_profile(self) -> dict[str, Any]:
        return _canonical_document(self.query_profile_bytes, "current query profile")

    @property
    def threshold_profile(self) -> dict[str, Any]:
        return _canonical_document(
            self.threshold_profile_bytes, "current threshold profile"
        )

    @property
    def reward_profile(self) -> dict[str, Any]:
        return _canonical_document(self.reward_profile_bytes, "current reward profile")

    @property
    def policy_class_profile(self) -> dict[str, Any]:
        return _canonical_document(
            self.policy_class_profile_bytes, "current policy-class profile"
        )

    @property
    def complete_search_profile(self) -> dict[str, Any]:
        return _canonical_document(
            self.complete_search_profile_bytes, "current complete-search profile"
        )

    @property
    def query_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN,
            self.query_profile_bytes,
            "current query profile",
        )

    @property
    def threshold_profile_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN,
            self.threshold_profile_bytes,
            "current threshold profile",
        )

    @property
    def reward_profile_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN,
            self.reward_profile_bytes,
            "current reward profile",
        )

    @property
    def policy_class_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN,
            self.policy_class_profile_bytes,
            "current policy-class profile",
        )

    @property
    def complete_search_profile_id(self) -> str:
        return _profile_id(
            PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN,
            self.complete_search_profile_bytes,
            "current complete-search profile",
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_query_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "current_source_proof_id": self.current_source_proof_id,
            "current_source_verification_id": self.current_source_verification_id,
            "query_profile": self.query_profile,
            "query_id": self.query_id,
            "threshold_profile": self.threshold_profile,
            "threshold_profile_id": self.threshold_profile_id,
            "reward_profile": self.reward_profile,
            "reward_profile_id": self.reward_profile_id,
            "policy_class_profile": self.policy_class_profile,
            "policy_class_id": self.policy_class_id,
            "complete_search_profile": self.complete_search_profile,
            "complete_search_profile_id": self.complete_search_profile_id,
            "authenticated_query_spec_complete": True,
            "claimant_query_fields_accepted": False,
            "semantic_replay_lane": "EVALUATION",
            "construction_only": True,
        }

    @property
    def attestation_id(self) -> str:
        document = self._payload()
        _require_live(self, "H1_CURRENT_QUERY_ATTESTATION", document)
        if content_id(QUERY_DOMAIN, document) != self._attestation_id:
            _fail("H1 current query attestation identity changed")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class H1CurrentSourceFixtureV1:
    """Preregistered-proof current candidate; never derived from claimant bytes."""

    _issuer: InitVar[object]
    build_kernel: H1CurrentBuildKernelAttestationV1
    query: H1CurrentQueryAttestationV1
    identity: DurableExactInfeasibilityIdentityV1
    _fixture_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CURRENT_SOURCE_ISSUER
            or type(self.build_kernel) is not H1CurrentBuildKernelAttestationV1
            or type(self.query) is not H1CurrentQueryAttestationV1
            or type(self.identity) is not DurableExactInfeasibilityIdentityV1
        ):
            _fail("H1 current-source fixture is caller-minted")
        _ = self.build_kernel.attestation_id
        _ = self.query.attestation_id
        expected = DurableExactInfeasibilityIdentityV1(
            self.build_kernel.structural_id,
            self.query.query_id,
            self.build_kernel.build_epoch_id,
            self.build_kernel.kernel_id,
            self.query.threshold_profile_id,
            self.query.reward_profile_id,
            self.query.policy_class_id,
            self.query.complete_search_profile_id,
        )
        if (
            self.identity != expected
            or self.build_kernel.current_source_proof_id
            != self.query.current_source_proof_id
            or self.build_kernel.current_source_verification_id
            != self.query.current_source_verification_id
        ):
            _fail("H1 current-source eight-coordinate identity crossed attestations")
        object.__setattr__(
            self,
            "_fixture_id",
            content_id(CURRENT_SOURCE_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(_issuer, self, "H1_CURRENT_SOURCE_FIXTURE")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_source_fixture.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "build_kernel_attestation_id": self.build_kernel.attestation_id,
            "query_attestation_id": self.query.attestation_id,
            "identity": self.identity.to_dict(),
            "current_source_proof_id": self.build_kernel.current_source_proof_id,
            "current_source_proof_sha256": (
                self.build_kernel.current_source_proof_sha256
            ),
            "current_source_proof_byte_count": (
                self.build_kernel.current_source_proof_byte_count
            ),
            "current_source_verification_id": (
                self.build_kernel.current_source_verification_id
            ),
            "source_archive_id": self.build_kernel.source_archive_id,
            "source_archive_sha256": self.build_kernel.source_archive_sha256,
            "source_archive_byte_count": self.build_kernel.source_archive_byte_count,
            "source_archive_role": (
                "CALLER_SUPPLIED_SELF_CONSISTENT_COMPILE_FIXTURE"
            ),
            "live_current_issuer_source_provenance_proven": False,
            "issuer_code_provenance_proven": False,
            "current_source_issued_before_claimant_comparison": True,
            "preregistered_current_identity_id": (
                EXPECTED_CURRENT_IDENTITY.exact_infeasibility_identity_id
            ),
            "selected_bundle_bytes_matched_before_semantic_verifier": True,
            "current_identity_derived_from_selected_bundle_output": False,
            "current_source_api_accepts_claimant_proof": False,
            "claimant_identity_used_as_current": False,
            "semantic_replay_lane": "EVALUATION",
            "charged_as_operational_route_work": False,
            "production_execution_authorized": False,
            "construction_only": True,
        }

    @property
    def fixture_id(self) -> str:
        document = self._payload()
        _require_live(self, "H1_CURRENT_SOURCE_FIXTURE", document)
        if content_id(CURRENT_SOURCE_DOMAIN, document) != self._fixture_id:
            _fail("H1 current-source fixture identity changed")
        return self._fixture_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "build_kernel_attestation": self.build_kernel.to_document(),
            "query_attestation": self.query.to_document(),
            "current_source_fixture_id": self.fixture_id,
        }


@dataclass(frozen=True, slots=True)
class H1DurableProofMatchAttestationV1:
    """Claimant match plus exact recipe-byte and retained-plan binding."""

    _issuer: InitVar[object]
    current_source_fixture_id: str
    claimant_proof_sha256: str
    claimant_proof_byte_count: int
    durable_proof_id: str
    recipe_id: str
    preexecution_candidate_sha256: str
    preexecution_candidate_byte_count: int
    preexecution_candidate_id: str
    recipe_chain: Mapping[str, str]
    verification_result: Mapping[str, Any]
    plan_binding: VerifiedDurableProofCacheConsumptionV1
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROOF_MATCH_ISSUER
            or type(self.recipe_chain) is not dict
            or type(self.verification_result) is not dict
            or type(self.plan_binding) is not VerifiedDurableProofCacheConsumptionV1
        ):
            _fail("H1 durable-proof match attestation is caller-minted")
        for value, label in (
            (self.current_source_fixture_id, "current-source fixture"),
            (self.claimant_proof_sha256, "claimant proof digest"),
            (self.durable_proof_id, "claimant durable proof"),
            (self.recipe_id, "preregistered H1 recipe"),
            (
                self.preexecution_candidate_sha256,
                "preexecution candidate digest",
            ),
            (self.preexecution_candidate_id, "preexecution candidate"),
            (self.plan_binding.cache_consumption_id, "proof plan binding"),
        ):
            _cid(value, label)
        result = self.verification_result
        if (
            type(self.claimant_proof_byte_count) is not int
            or self.claimant_proof_byte_count <= 0
            or type(self.preexecution_candidate_byte_count) is not int
            or self.preexecution_candidate_byte_count
            != EXPECTED_H1_PREEXECUTION_BYTE_COUNT
            or result.get("outcome") != DurableProofVerificationOutcomeV1.IDENTICAL_MATCH.value
            or result.get("submitted_bytes_sha256") != self.claimant_proof_sha256
            or result.get("durable_proof_id") != self.durable_proof_id
            or self.recipe_id != EXPECTED_H1_RECIPE_CHAIN["recipe_id"]
            or self.recipe_chain != dict(EXPECTED_H1_RECIPE_CHAIN)
            or self.preexecution_candidate_sha256
            != self.recipe_chain["preexecution_sha256"]
            or self.preexecution_candidate_id
            != self.recipe_chain["preexecution_candidate_id"]
            or result.get("proof_identity_id") != result.get("current_identity_id")
            or result.get("proof_semantically_valid") is not True
            or result.get("minimum_failure_probability") != Fraction(383, 410)
            or result.get("verification_id") != self.plan_binding.verification_id
            or self.plan_binding.durable_proof_id != self.durable_proof_id
            or self.plan_binding.selected_plan_id
            != EXPECTED_H1_RECIPE_CHAIN["selected_plan_id"]
            or self.plan_binding.exact_infeasibility_identity_id
            != result.get("current_identity_id")
        ):
            _fail("H1 durable-proof match lacks one exact retained IDENTICAL_MATCH")
        object.__setattr__(
            self,
            "_attestation_id",
            content_id(PROOF_MATCH_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(
            _issuer, self, "H1_DURABLE_PROOF_MATCH_ATTESTATION"
        )

    @property
    def selected_plan_id(self) -> str:
        return self.plan_binding.selected_plan_id

    @property
    def exact_identity_id(self) -> str:
        return self.plan_binding.exact_infeasibility_identity_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_durable_proof_match_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "current_source_fixture_id": self.current_source_fixture_id,
            "claimant_proof_sha256": self.claimant_proof_sha256,
            "claimant_proof_byte_count": self.claimant_proof_byte_count,
            "durable_proof_id": self.durable_proof_id,
            "h1_direct_fallback_two_role_recipe_id": self.recipe_id,
            "preexecution_candidate_sha256": self.preexecution_candidate_sha256,
            "preexecution_candidate_byte_count": (
                self.preexecution_candidate_byte_count
            ),
            "preexecution_candidate_id": self.preexecution_candidate_id,
            "preregistered_recipe_chain": dict(self.recipe_chain),
            "verification_result": dict(self.verification_result),
            "plan_binding": self.plan_binding.to_dict(),
            "selected_plan_id": self.selected_plan_id,
            "exact_infeasibility_identity_id": self.exact_identity_id,
            "current_identity_supplied_explicitly_to_durable_verifier": True,
            "durable_verifier_default_self_match_used": False,
            "retained_verifier_handle_validated_and_plan_bound": True,
            "retained_verifier_handle_one_shot_revocation": False,
            "retained_verifier_handle_consumed": False,
            "retained_handle_status": "VALIDATED_AND_PLAN_BOUND",
            "one_shot_revocation": False,
            "upstream_cache_consumption_schema_name_is_legacy": True,
            "complete_recipe_chain_observed_from_exact_preexecution_bytes": True,
            "recipe_chain_constants_used_to_fill_unobserved_fields": False,
            "semantic_replay_lane": "EVALUATION",
            "charged_as_operational_route_work": False,
            "construction_only": True,
        }

    @property
    def attestation_id(self) -> str:
        document = self._payload()
        _require_live(self, "H1_DURABLE_PROOF_MATCH_ATTESTATION", document)
        if content_id(PROOF_MATCH_DOMAIN, document) != self._attestation_id:
            _fail("H1 durable-proof match attestation identity changed")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_match_attestation_id": self.attestation_id}


_ROUTE_TIME_FORBIDDEN_API_DECLARATION = {
    "kind": "FORBIDDEN_API_DECLARATION_NOT_OBSERVED_COUNTERS",
    "forbidden_operations": [
        "DURABLE_PROOF_PRODUCER_OR_VERIFIER",
        "FALLBACK_SOLVER",
        "GROUND_OUTCOME_ENUMERATION",
        "J0_OR_OTHER_PLANNER",
        "KERNEL_STEP",
    ],
    "caller_supplied_zero_counters_accepted": False,
}

_UNOBSERVED_ROUTE_TIME_CALL_COUNTS = {
    "kind": "UNOBSERVED",
    "reason": "OBSERVED_ROUTE_TIME_ACCESS_LOG_PENDING",
}


@dataclass(frozen=True, slots=True)
class H1ProductionCurrentIdentityCandidateV1:
    """Route-time candidate crosswalk; observed access evidence is pending."""

    _issuer: InitVar[object]
    current_source: H1CurrentSourceFixtureV1 = field(repr=False)
    proof_match: H1DurableProofMatchAttestationV1 = field(repr=False)
    recipe: H1DirectFallbackTwoRoleRecipeV1 = field(repr=False)
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CURRENT_IDENTITY_ISSUER
            or type(self.current_source) is not H1CurrentSourceFixtureV1
            or type(self.proof_match) is not H1DurableProofMatchAttestationV1
            or type(self.recipe) is not H1DirectFallbackTwoRoleRecipeV1
        ):
            _fail("H1 production current identity is caller-minted")
        _ = self.current_source.fixture_id
        _ = self.proof_match.attestation_id
        _ = self.recipe.recipe_id
        visible_recipe = _visible_recipe_projection(self.recipe)
        identity = self.current_source.identity
        source = self.recipe.source
        if (
            self.proof_match.current_source_fixture_id
            != self.current_source.fixture_id
            or self.proof_match.recipe_id != self.recipe.recipe_id
            or any(
                self.proof_match.recipe_chain.get(key) != value
                for key, value in visible_recipe.items()
            )
            or self.proof_match.exact_identity_id
            != identity.exact_infeasibility_identity_id
            or self.proof_match.durable_proof_id != source.durable_proof_id
            or self.proof_match.selected_plan_id != source.selected_plan_id
            or source.exact_infeasibility_identity_id
            != identity.exact_infeasibility_identity_id
            or source.structural_id != identity.structural_id
            or source.query_id != identity.query_id
            or source.threshold_profile_id != identity.threshold_profile_id
            or source.build_epoch_id != identity.build_epoch_id
            or source.kernel_id != identity.kernel_id
        ):
            _fail("H1 recipe, current source and durable-proof match crossed identities")
        object.__setattr__(
            self,
            "_candidate_id",
            content_id(CURRENT_IDENTITY_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(
            _issuer, self, "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE"
        )

    @property
    def identity(self) -> DurableExactInfeasibilityIdentityV1:
        return self.current_source.identity

    def _identity_crosswalk(self) -> list[dict[str, Any]]:
        identity = self.identity
        recipe = self.recipe.source
        rows = (
            ("structural_id", identity.structural_id, recipe.structural_id),
            ("query_id", identity.query_id, recipe.query_id),
            ("BuildEpoch_id", identity.build_epoch_id, recipe.build_epoch_id),
            ("kernel_id", identity.kernel_id, recipe.kernel_id),
            (
                "threshold_profile_id",
                identity.threshold_profile_id,
                recipe.threshold_profile_id,
            ),
            ("reward_profile_id", identity.reward_profile_id, None),
            ("policy_class_id", identity.policy_class_id, None),
            (
                "complete_search_profile_id",
                identity.complete_search_profile_id,
                None,
            ),
        )
        return [
            {
                "coordinate": name,
                "current_value": value,
                "proof_match_value": value,
                "recipe_value": recipe_value,
                "recipe_coordinate_applicable": recipe_value is not None,
            }
            for name, value, recipe_value in rows
        ]

    def _payload(self) -> dict[str, Any]:
        source = self.recipe.source
        return {
            "schema": (
                "acfqp.construction_k7_h1_production_current_identity_candidate.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "current_source_fixture_id": self.current_source.fixture_id,
            "build_kernel_attestation_id": (
                self.current_source.build_kernel.attestation_id
            ),
            "query_attestation_id": self.current_source.query.attestation_id,
            "proof_match_attestation_id": self.proof_match.attestation_id,
            "proof_plan_binding_id": (
                self.proof_match.plan_binding.cache_consumption_id
            ),
            "h1_direct_fallback_two_role_recipe_id": self.recipe.recipe_id,
            "preregistered_recipe_chain": dict(self.proof_match.recipe_chain),
            "identity": self.identity.to_dict(),
            "exact_identity_crosswalk": self._identity_crosswalk(),
            "source_archive_id": self.current_source.build_kernel.source_archive_id,
            "source_archive_sha256": (
                self.current_source.build_kernel.source_archive_sha256
            ),
            "source_archive_byte_count": (
                self.current_source.build_kernel.source_archive_byte_count
            ),
            "durable_proof_id": self.proof_match.durable_proof_id,
            "durable_proof_verification_id": (
                self.proof_match.plan_binding.verification_id
            ),
            "selected_plan_id": source.selected_plan_id,
            "RouteDecisionContext_id": source.route_decision_context_id,
            "decision_point_id": source.decision_point_id,
            "logical_occurrence_id": source.logical_occurrence_id,
            "route_attempt_id": source.route_attempt_id,
            "route_time_forbidden_api_declaration": dict(
                _ROUTE_TIME_FORBIDDEN_API_DECLARATION
            ),
            "route_time_call_counts": dict(_UNOBSERVED_ROUTE_TIME_CALL_COUNTS),
            "route_time_observed_access_log_id": None,
            "route_time_access_evidence_status": (
                "PENDING_OBSERVED_ACCESS_LOG"
            ),
            "current_identity_derived_before_claimant_comparison": True,
            "claimant_fields_accepted_as_current": False,
            "legacy_current_identity_used_as_authority": False,
            "durable_proof_semantics_replayed_at_route_time": False,
            "source_archive_loaded_execution_claimed": False,
            "source_archive_is_live_current_issuer_provenance": False,
            "same_process_unforgeability_claimed": False,
            "private_module_state_adversary_resistance_claimed": False,
            "eligible_as_production_consumer_authority": False,
            "production_consumers_must_reject_candidate": True,
            "production_current_identity_candidate": True,
            "production_current_identity_authority": False,
            "formal_v7_route_authority_present": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
            "construction_only": True,
        }

    @property
    def candidate_id(self) -> str:
        document = self._payload()
        _require_live(
            self, "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE", document
        )
        if content_id(CURRENT_IDENTITY_DOMAIN, document) != self._candidate_id:
            _fail("H1 production current identity changed")
        return self._candidate_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_current_identity_candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class H1ProductionCurrentIdentityCandidateVerificationV1:
    """Structural bytes replay of an already-issued no-ground candidate."""

    _issuer: InitVar[object]
    candidate_id: str
    candidate_sha256: str
    candidate_byte_count: int
    current_source_fixture_id: str
    proof_match_attestation_id: str
    recipe_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("H1 current-identity verification is caller-minted")
        for value, label in (
            (self.candidate_id, "current identity candidate"),
            (self.candidate_sha256, "current identity candidate digest"),
            (self.current_source_fixture_id, "current-source fixture"),
            (self.proof_match_attestation_id, "proof-match attestation"),
            (self.recipe_id, "H1 recipe"),
        ):
            _cid(value, label)
        if type(self.candidate_byte_count) is not int or self.candidate_byte_count <= 0:
            _fail("H1 current-identity candidate verification extent is invalid")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )
        _mark_exact_issuance(
            _issuer,
            self,
            "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE_VERIFICATION",
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_h1_production_current_identity_candidate_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_current_identity_candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "candidate_byte_count": self.candidate_byte_count,
            "current_source_fixture_id": self.current_source_fixture_id,
            "proof_match_attestation_id": self.proof_match_attestation_id,
            "h1_direct_fallback_two_role_recipe_id": self.recipe_id,
            "structurally_invokes_durable_proof_verifier": False,
            "structurally_invokes_kernel_or_planner": False,
            "route_time_forbidden_api_declaration": dict(
                _ROUTE_TIME_FORBIDDEN_API_DECLARATION
            ),
            "route_time_call_counts": dict(_UNOBSERVED_ROUTE_TIME_CALL_COUNTS),
            "route_time_observed_access_log_id": None,
            "route_time_access_evidence_status": "PENDING_OBSERVED_ACCESS_LOG",
            "exact_structural_replay": True,
            "production_current_identity_candidate_verified": True,
            "production_current_identity_authority_verified": False,
            "same_process_unforgeability_verified": False,
            "eligible_as_production_consumer_authority": False,
            "production_consumers_must_reject_candidate": True,
            "production_execution_authorized": False,
            "construction_only": True,
        }

    @property
    def verification_id(self) -> str:
        document = self._payload()
        _require_live(
            self,
            "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE_VERIFICATION",
            document,
        )
        if content_id(VERIFICATION_DOMAIN, document) != self._verification_id:
            _fail("H1 current-identity verification changed")
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _validate_source_archive(
    *,
    closure: source_runtime_v2.ConstructionSourceClosureV2,
    archive: source_runtime_v2.ConstructionSourceArchiveV2,
    runtime_lock: source_runtime_v2.ConstructionRuntimeDependencyLockV2,
    compile_verification: (
        source_runtime_v2.ConstructionSealedArchiveCompileVerificationV2
    ),
) -> None:
    if (
        type(closure) is not source_runtime_v2.ConstructionSourceClosureV2
        or type(archive) is not source_runtime_v2.ConstructionSourceArchiveV2
        or type(runtime_lock)
        is not source_runtime_v2.ConstructionRuntimeDependencyLockV2
        or type(compile_verification)
        is not source_runtime_v2.ConstructionSealedArchiveCompileVerificationV2
        or closure.root_modules != SOURCE_ARCHIVE_ROOT_MODULES
        or archive.source_closure_id != closure.closure_id
        or archive.entries != closure.modules
        or _sha256(archive.archive_bytes) != archive.archive_sha256
        or len(archive.archive_bytes) != archive.archive_byte_count
        or compile_verification.source_closure_id != closure.closure_id
        or compile_verification.source_archive_id != archive.archive_id
        or compile_verification.runtime_lock_verification_id
        != runtime_lock.verification_id
        or compile_verification.archive_sha256 != archive.archive_sha256
        or compile_verification.archive_byte_count != archive.archive_byte_count
        or compile_verification.expected_module_names != closure.module_names
        or compile_verification.before_acfqp_modules != ()
        or compile_verification.after_acfqp_modules != ()
        or compile_verification.child_result_document.get(
            "tested_source_execution_allowed"
        )
        is not False
    ):
        _fail("H1 current-identity source archive/compile chain is foreign or stale")


def _verify_preregistered_current_proof_before_semantic_replay(
    raw: bytes,
) -> dict[str, Any]:
    """Match the selected bundle output to the frozen current source first."""

    if (
        type(raw) is not bytes
        or len(raw) != EXPECTED_CURRENT_PROOF_BYTE_COUNT
        or not hmac.compare_digest(_sha256(raw), EXPECTED_CURRENT_PROOF_SHA256)
    ):
        _fail("selected bundle output is not the preregistered current proof bytes")
    document = _canonical_document(raw, "preregistered current-source proof")
    try:
        observed = {
            "structural_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN,
                document["structural_profile"],
            ),
            "query_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN,
                document["query_profile"],
            ),
            "build_epoch_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN,
                document["build_epoch"],
            ),
            "kernel_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN,
                document["kernel_profile"],
            ),
            "threshold_profile_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN,
                document["threshold_profile"],
            ),
            "reward_profile_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN,
                document["reward_profile"],
            ),
            "policy_class_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN,
                document["policy_class_profile"],
            ),
            "complete_search_profile_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN,
                document["complete_search_profile"],
            ),
            "source_projection_id": content_id(
                PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN,
                document["source_projection"],
            ),
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "preregistered current proof profile projection is malformed"
        ) from error
    expected = {
        "structural_id": EXPECTED_CURRENT_IDENTITY.structural_id,
        "query_id": EXPECTED_CURRENT_IDENTITY.query_id,
        "build_epoch_id": EXPECTED_CURRENT_IDENTITY.build_epoch_id,
        "kernel_id": EXPECTED_CURRENT_IDENTITY.kernel_id,
        "threshold_profile_id": EXPECTED_CURRENT_IDENTITY.threshold_profile_id,
        "reward_profile_id": EXPECTED_CURRENT_IDENTITY.reward_profile_id,
        "policy_class_id": EXPECTED_CURRENT_IDENTITY.policy_class_id,
        "complete_search_profile_id": (
            EXPECTED_CURRENT_IDENTITY.complete_search_profile_id
        ),
        "source_projection_id": EXPECTED_CURRENT_SOURCE_PROJECTION_ID,
    }
    if (
        document.get("durable_exact_infeasibility_proof_id")
        != EXPECTED_CURRENT_PROOF_ID
        or document.get("identity") != EXPECTED_CURRENT_IDENTITY.to_dict()
        or observed != expected
    ):
        _fail("selected bundle output crossed the preregistered current identity")
    return document


def issue_h1_current_source_fixture_v1(
    phase05_bundle_root: str | Path,
    *,
    source_closure: source_runtime_v2.ConstructionSourceClosureV2,
    source_archive: source_runtime_v2.ConstructionSourceArchiveV2,
    runtime_lock: source_runtime_v2.ConstructionRuntimeDependencyLockV2,
    archive_compile_verification: (
        source_runtime_v2.ConstructionSealedArchiveCompileVerificationV2
    ),
) -> H1CurrentSourceFixtureV1:
    """Issue current build/kernel/query evidence without claimant proof input.

    This is explicitly build/evaluation work.  It may perform the complete
    durable semantic replay.  Its output is the independently issued input to
    the later zero-ground route-time freezer.
    """

    _validate_source_archive(
        closure=source_closure,
        archive=source_archive,
        runtime_lock=runtime_lock,
        compile_verification=archive_compile_verification,
    )
    try:
        current_raw = issue_phase3e_exact_infeasibility_durable_proof_v1(
            Path(phase05_bundle_root)
        )
        document = _verify_preregistered_current_proof_before_semantic_replay(
            current_raw
        )
        identity = EXPECTED_CURRENT_IDENTITY
        verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
            current_raw,
            current_identity=identity,
        )
    except ConstructionK7H1ProductionCurrentIdentityV1Error:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "independent current source failed build-lane issuance"
        ) from error
    if (
        verified.result.outcome
        is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
        or verified.result.proof_semantically_valid is not True
        or verified.proof_identity != identity
        or verified.current_identity != identity
        or verified.result.proof_identity_id
        != identity.exact_infeasibility_identity_id
        or verified.result.current_identity_id
        != identity.exact_infeasibility_identity_id
        or verified.result.durable_proof_id
        != document.get("durable_exact_infeasibility_proof_id")
        or verified.result.submitted_bytes_sha256 != _sha256(current_raw)
    ):
        _fail("independent current source did not issue one exact verified identity")

    build_kernel = H1CurrentBuildKernelAttestationV1(
        _BUILD_KERNEL_ISSUER,
        verified.result.durable_proof_id,  # type: ignore[arg-type]
        _sha256(current_raw),
        len(current_raw),
        verified.result.verification_id,
        _document_bytes(document["structural_profile"], "current structural profile"),
        _document_bytes(document["source_projection"], "current source projection"),
        _document_bytes(document["kernel_profile"], "current kernel profile"),
        _document_bytes(document["build_epoch"], "current BuildEpoch"),
        source_closure.closure_id,
        source_archive.archive_id,
        source_archive.archive_sha256,
        source_archive.archive_byte_count,
        runtime_lock.verification_id,
        archive_compile_verification.verification_id,
        tuple(item.module_id for item in source_closure.modules),
    )
    _retain(
        build_kernel,
        "H1_CURRENT_BUILD_KERNEL_ATTESTATION",
        build_kernel._payload(),  # noqa: SLF001 - issuer snapshot
    )
    query = H1CurrentQueryAttestationV1(
        _QUERY_ISSUER,
        verified.result.durable_proof_id,  # type: ignore[arg-type]
        verified.result.verification_id,
        _document_bytes(document["query_profile"], "current query profile"),
        _document_bytes(document["threshold_profile"], "current threshold profile"),
        _document_bytes(document["reward_profile"], "current reward profile"),
        _document_bytes(
            document["policy_class_profile"], "current policy-class profile"
        ),
        _document_bytes(
            document["complete_search_profile"], "current complete-search profile"
        ),
    )
    _retain(query, "H1_CURRENT_QUERY_ATTESTATION", query._payload())  # noqa: SLF001
    if (
        build_kernel.structural_id != identity.structural_id
        or build_kernel.kernel_id != identity.kernel_id
        or build_kernel.build_epoch_id != identity.build_epoch_id
        or query.query_id != identity.query_id
        or query.threshold_profile_id != identity.threshold_profile_id
        or query.reward_profile_id != identity.reward_profile_id
        or query.policy_class_id != identity.policy_class_id
        or query.complete_search_profile_id != identity.complete_search_profile_id
    ):
        _fail("independent current source differs from its eight-coordinate identity")
    fixture = H1CurrentSourceFixtureV1(
        _CURRENT_SOURCE_ISSUER,
        build_kernel,
        query,
        identity,
    )
    _retain(fixture, "H1_CURRENT_SOURCE_FIXTURE", fixture._payload())  # noqa: SLF001
    return fixture


def issue_h1_durable_proof_match_attestation_v1(
    claimant_proof_bytes: bytes,
    *,
    current_source: H1CurrentSourceFixtureV1,
    recipe: H1DirectFallbackTwoRoleRecipeV1,
    preexecution_candidate_bytes: bytes,
) -> H1DurableProofMatchAttestationV1:
    """Verify claimant bytes only after the independent current source exists."""

    if type(current_source) is not H1CurrentSourceFixtureV1:
        _fail("durable-proof match requires an issuer-owned current source")
    _ = current_source.fixture_id
    recipe_chain = _exact_preregistered_recipe_chain(
        recipe,
        preexecution_candidate_bytes=preexecution_candidate_bytes,
    )
    selected_plan = _cid(recipe_chain["selected_plan_id"], "selected plan")
    if type(claimant_proof_bytes) is not bytes or not claimant_proof_bytes:
        _fail("claimant durable-proof bytes are missing")
    verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        claimant_proof_bytes,
        current_identity=current_source.identity,
    )
    if (
        verified.result.outcome
        is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
        or verified.result.proof_semantically_valid is not True
        or verified.proof_identity != current_source.identity
        or verified.current_identity != current_source.identity
    ):
        _fail("claimant durable proof does not match the independent current source")
    try:
        plan_binding = bind_verified_durable_exact_infeasibility_to_plan_v1(
            verified,
            selected_plan_id=selected_plan,
        )
    except ValueError as error:
        raise ConstructionK7H1ProductionCurrentIdentityV1Error(
            "claimant durable-proof verifier handle was not retained"
        ) from error
    attestation = H1DurableProofMatchAttestationV1(
        _PROOF_MATCH_ISSUER,
        current_source.fixture_id,
        _sha256(claimant_proof_bytes),
        len(claimant_proof_bytes),
        verified.result.durable_proof_id,  # type: ignore[arg-type]
        recipe.recipe_id,
        _sha256(preexecution_candidate_bytes),
        len(preexecution_candidate_bytes),
        recipe_chain["preexecution_candidate_id"],
        recipe_chain,
        verified.result.to_dict(),
        plan_binding,
    )
    _retain(
        attestation,
        "H1_DURABLE_PROOF_MATCH_ATTESTATION",
        attestation._payload(),  # noqa: SLF001
    )
    return attestation


def freeze_h1_production_current_identity_candidate_v1(
    *,
    current_source: H1CurrentSourceFixtureV1,
    proof_match_attestation: H1DurableProofMatchAttestationV1,
    recipe: H1DirectFallbackTwoRoleRecipeV1,
) -> H1ProductionCurrentIdentityCandidateV1:
    """Freeze a route-time identity candidate from already-issued inputs."""

    result = H1ProductionCurrentIdentityCandidateV1(
        _CURRENT_IDENTITY_ISSUER,
        current_source,
        proof_match_attestation,
        recipe,
    )
    _retain(
        result,
        "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE",
        result._payload(),  # noqa: SLF001
    )
    return result


def verify_h1_production_current_identity_candidate_bytes_v1(
    *,
    raw: bytes,
    current_source: H1CurrentSourceFixtureV1,
    proof_match_attestation: H1DurableProofMatchAttestationV1,
    recipe: H1DirectFallbackTwoRoleRecipeV1,
) -> H1ProductionCurrentIdentityCandidateVerificationV1:
    """Verify candidate bytes by a second structural join without replay."""

    document = _canonical_document(raw, "H1 production current identity")
    expected = freeze_h1_production_current_identity_candidate_v1(
        current_source=current_source,
        proof_match_attestation=proof_match_attestation,
        recipe=recipe,
    )
    if document != expected.to_document():
        _fail("H1 production current-identity bytes differ from exact replay")
    verification = H1ProductionCurrentIdentityCandidateVerificationV1(
        _VERIFICATION_ISSUER,
        expected.candidate_id,
        _sha256(raw),
        len(raw),
        current_source.fixture_id,
        proof_match_attestation.attestation_id,
        recipe.recipe_id,
    )
    _retain(
        verification,
        "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE_VERIFICATION",
        verification._payload(),  # noqa: SLF001
    )
    return verification


def require_h1_production_current_identity_authority_v1(value: Any) -> NoReturn:
    """Reject every V1 construction candidate at a production boundary."""

    if type(value) is H1ProductionCurrentIdentityCandidateV1:
        _ = value.candidate_id
        _fail(
            "H1 current-identity V1 is a construction candidate, not a "
            "production authority"
        )
    _fail("H1 production current-identity authority is absent")


_FROZEN_PUBLIC_ISSUER_GLOBALS = globals()
_FROZEN_PUBLIC_ISSUER_CODES = MappingProxyType(
    {
        "CURRENT_SOURCE": issue_h1_current_source_fixture_v1.__code__,
        "PROOF_MATCH": issue_h1_durable_proof_match_attestation_v1.__code__,
        "CURRENT_IDENTITY_CANDIDATE": (
            freeze_h1_production_current_identity_candidate_v1.__code__
        ),
        "CANDIDATE_VERIFICATION": (
            verify_h1_production_current_identity_candidate_bytes_v1.__code__
        ),
    }
)


__all__ = (
    "CONSTRUCTION_ONLY",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1ProductionCurrentIdentityV1Error",
    "EXPECTED_CURRENT_IDENTITY",
    "EXPECTED_CURRENT_PROOF_BYTE_COUNT",
    "EXPECTED_CURRENT_PROOF_ID",
    "EXPECTED_CURRENT_PROOF_SHA256",
    "EXPECTED_CURRENT_SOURCE_PROJECTION_ID",
    "EXPECTED_H1_PREEXECUTION_BYTE_COUNT",
    "EXPECTED_H1_RECIPE_CHAIN",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1CurrentBuildKernelAttestationV1",
    "H1CurrentQueryAttestationV1",
    "H1CurrentSourceFixtureV1",
    "H1DurableProofMatchAttestationV1",
    "H1ProductionCurrentIdentityCandidateV1",
    "H1ProductionCurrentIdentityCandidateVerificationV1",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_CURRENT_IDENTITY_AUTHORITY_PRESENT",
    "PRODUCTION_CURRENT_IDENTITY_CANDIDATE_PRESENT",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SOURCE_ARCHIVE_ROOT_MODULES",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_h1_production_current_identity_candidate_v1",
    "issue_h1_current_source_fixture_v1",
    "issue_h1_durable_proof_match_attestation_v1",
    "require_h1_production_current_identity_authority_v1",
    "verify_h1_production_current_identity_candidate_bytes_v1",
)
