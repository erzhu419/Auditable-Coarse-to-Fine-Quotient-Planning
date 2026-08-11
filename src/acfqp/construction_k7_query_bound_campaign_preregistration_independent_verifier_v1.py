"""Independent bytes verifier for query-bound campaign preregistration."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import io
import math
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any, NoReturn
import zipfile

from acfqp import _v075_construction_source_runtime_v2 as source_runtime
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.phase3e_sealed_executor_v1 import (
    OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    RuntimeManifestCapProfileV1,
    RuntimeTreeManifestV1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.100"
PROFILE_KEY = (
    "construction_k7_query_bound_campaign_preregistration_independent_verifier_v1"
)
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_campaign_preregistration_v1"
REGISTRATION_STAGE = "PRE_EXECUTION_INPUT_RUNTIME_AND_DENOMINATOR_FREEZE"
SCALAR_GATE_STATUS = "NOT_RUN"
MAX_EXPLICIT_PERMUTATIONS = 100_000
INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)
COMMON_INPUT_ROLES = ("SOURCE_TRACE", "BUILD_EPOCH_ENVELOPE")
OCCURRENCE_SPECIFIC_INPUT_ROLES = (
    "ROOT_QUERY_RESULT",
    "RECOVERY_OVERLAY",
    "RECOVERY_REQUEST",
)

INPUT_BLOB_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN
OCCURRENCE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN
)
WORKLOAD_SPEC_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN
PREREGISTRATION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
PREPARATION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_V1_DOMAIN
)

_V075_SOURCE_MODULE_DOMAIN = "acfqp:v075-construction-source-module:v2"
_V075_SOURCE_CLOSURE_DOMAIN = "acfqp:v075-construction-source-closure:v2"
_V075_SOURCE_ARCHIVE_DOMAIN = "acfqp:v075-construction-source-archive:v2"
_VERIFICATION_ISSUER = object()


class ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
    ValueError
):
    """The preregistration source, inputs, identities, or boundaries diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _exact(document: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} field set changed")
    return document


def _replay_id(document: dict[str, Any], field_name: str, domain: str, label: str) -> str:
    payload = dict(document)
    observed = payload.pop(field_name, None)
    if observed != content_id(domain, payload):
        _fail(f"{label} content ID changed")
    return _cid(observed, label)


def _canonical(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail("campaign preregistration bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
            "campaign preregistration bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("campaign preregistration bytes are not one canonical object")
    return document


MODULE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "module_name",
    "relative_path",
    "is_package",
    "source_sha256",
    "source_byte_count",
    "static_local_imports",
    "regular_file_verified",
    "symlink_free_verified",
    "module_id",
}
CLOSURE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "closure_rule",
    "root_modules",
    "modules",
    "module_ids",
    "module_count",
    "all_sources_regular_files",
    "all_source_paths_symlink_free",
    "caller_supplied_source_bytes_replayed",
    "construction_only",
    "closure_id",
}
ARCHIVE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "source_closure_id",
    "entry_ids",
    "entry_count",
    "archive_format",
    "archive_sha256",
    "archive_byte_count",
    "zip_compression",
    "canonical_member_timestamp",
    "canonical_member_mode",
    "construction_only",
    "archive_id",
}
PREPARATION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_closure",
    "runtime_manifest",
    "runtime_manifest_cap_profile",
    "runtime_entrypoint",
    "private_runtime_lease_required",
    "runtime_tree_build_charged_to_occurrence",
    "construction_only",
    "official_execution_allowed",
    "query_bound_runtime_preparation_id",
}
BLOB_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "canonical_json_bytes_hex",
    "byte_count",
    "sha256",
    "campaign_input_blob_id",
}
OCCURRENCE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_index",
    "logical_occurrence_id",
    "query_ordinal",
    "input_roles",
    "all_scientific_inputs_frozen_before_execution",
    "execution_result_present",
    "official_execution_allowed",
    "preregistered_occurrence_spec_id",
}
WORKLOAD_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "comparison_profile_id",
    "ordered_logical_occurrence_ids",
    "ordered_occurrence_spec_ids",
    "logical_occurrence_count",
    "permutation_cap",
    "registration_order_is_denominator_order",
    "posthoc_occurrence_deletion_allowed",
    "posthoc_occurrence_insertion_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "official_execution_allowed",
    "campaign_workload_spec_id",
}
PREREGISTRATION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "registration_stage",
    "runtime_preparation",
    "runtime_preparation_id",
    "runtime_tree_id",
    "source_closure_id",
    "source_archive",
    "source_archive_bytes_hex",
    "source_bytes_embedded",
    "input_blobs",
    "preregistered_occurrences",
    "campaign_workload_spec",
    "campaign_workload_spec_id",
    "ordered_logical_occurrence_ids",
    "logical_occurrence_count",
    "campaign_preregistration_present",
    "preregistration_contains_execution_result",
    "execution_started_by_this_api",
    "scientific_campaign_closure_issued",
    "certificate_coverage_gate_status",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "official_execution_allowed",
    "query_bound_campaign_preregistration_id",
}


def _source_archive(
    *,
    source_closure_document: Any,
    source_archive_document: Any,
    source_archive_bytes_hex: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    bytes,
    source_runtime.ConstructionSourceClosureV2,
]:
    closure_claim = _exact(
        source_closure_document,
        CLOSURE_FIELDS,
        "embedded source closure",
    )
    archive_claim = _exact(
        source_archive_document,
        ARCHIVE_FIELDS,
        "embedded source archive",
    )
    if type(source_archive_bytes_hex) is not str:
        _fail("embedded source archive hex is absent")
    try:
        archive_raw = bytes.fromhex(source_archive_bytes_hex)
    except ValueError as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
            "embedded source archive hex is invalid"
        ) from error
    if source_archive_bytes_hex != archive_raw.hex():
        _fail("embedded source archive hex is not canonical lowercase hex")
    modules = closure_claim["modules"]
    roots = closure_claim["root_modules"]
    if type(modules) is not list or type(roots) is not list or not modules:
        _fail("embedded source closure inventory is malformed")
    module_claims = tuple(
        _exact(row, MODULE_FIELDS, "embedded source module") for row in modules
    )
    relative_paths: list[str] = []
    for row in module_claims:
        path = PurePosixPath(row["relative_path"])
        if path.is_absolute() or ".." in path.parts or not path.parts:
            _fail("embedded source module path escaped its archive")
        relative_paths.append(row["relative_path"])
    try:
        with zipfile.ZipFile(io.BytesIO(archive_raw), mode="r") as archive:
            infos = archive.infolist()
            if [row.filename for row in infos] != sorted(relative_paths):
                _fail("embedded source archive member order or set changed")
            source_by_name = {
                row["module_name"]: archive.read(row["relative_path"])
                for row in module_claims
            }
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as error:
        if type(error) is ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error:
            raise
        raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
            "embedded source archive could not be replayed"
        ) from error
    with tempfile.TemporaryDirectory(prefix="acfqp-query-bound-prereg-source-") as temporary:
        root = Path(temporary)
        module_paths: dict[str, str] = {}
        for row in module_claims:
            target = root / row["relative_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source_by_name[row["module_name"]])
            target.chmod(0o444)
            module_paths[row["module_name"]] = str(target)
        try:
            closure = source_runtime.build_construction_source_closure_v2(
                root_modules=tuple(roots),
                module_sources=source_by_name,
                module_paths=module_paths,
            )
            archive = source_runtime.build_deterministic_source_archive_v2(
                closure=closure,
                module_sources=source_by_name,
            )
        except Exception as error:
            raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
                "embedded source closure or deterministic archive failed replay"
            ) from error
    if (
        closure.to_document() != closure_claim
        or archive.to_document() != archive_claim
        or archive.archive_bytes != archive_raw
    ):
        _fail("embedded source closure or archive differs from exact replay")
    return closure.to_document(), archive.to_document(), archive_raw, closure


def _runtime_preparation(
    document: Any,
    *,
    expected_source_closure: dict[str, Any],
) -> tuple[dict[str, Any], str, str]:
    preparation = _exact(document, PREPARATION_FIELDS, "runtime preparation")
    try:
        manifest = RuntimeTreeManifestV1.from_dict(preparation["runtime_manifest"])
        cap = RuntimeManifestCapProfileV1.from_dict(
            preparation["runtime_manifest_cap_profile"]
        )
    except Exception as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
            "runtime manifest or cap profile failed replay"
        ) from error
    closure_modules = expected_source_closure["modules"]
    expected_manifest_rows = [
        {
            "relative_path": row["relative_path"],
            "size_bytes": row["source_byte_count"],
            "sha256": row["source_sha256"],
        }
        for row in closure_modules
    ]
    if (
        preparation["schema"]
        != "acfqp.construction_k7_query_bound_runtime_preparation.v1"
        or preparation["schema_version"] != SCHEMA_VERSION
        or preparation["proposed_contract_version"] != "2.0.97"
        or preparation["profile_key"]
        != "construction_k7_query_bound_supervised_executor_v1"
        or preparation["source_closure"] != expected_source_closure
        or preparation["runtime_manifest"]["entries"] != expected_manifest_rows
        or cap != OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
        or preparation["runtime_entrypoint"]
        != "acfqp/construction_k7_query_bound_accounted_runtime_v1.py"
        or preparation["private_runtime_lease_required"] is not True
        or preparation["runtime_tree_build_charged_to_occurrence"] is not False
        or preparation["construction_only"] is not True
        or preparation["official_execution_allowed"] is not False
    ):
        _fail("runtime preparation semantics changed")
    preparation_id = _replay_id(
        preparation,
        "query_bound_runtime_preparation_id",
        PREPARATION_DOMAIN,
        "runtime preparation",
    )
    return preparation, preparation_id, manifest.runtime_tree_id


def _input_blobs(documents: Any) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    if type(documents) is not list or not documents:
        _fail("campaign input blob inventory is absent")
    by_id: dict[str, bytes] = {}
    expected_documents: list[dict[str, Any]] = []
    for candidate in documents:
        row = _exact(candidate, BLOB_FIELDS, "campaign input blob")
        if type(row["canonical_json_bytes_hex"]) is not str:
            _fail("campaign input blob hex is absent")
        try:
            raw = bytes.fromhex(row["canonical_json_bytes_hex"])
        except ValueError as error:
            raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
                "campaign input blob hex is invalid"
            ) from error
        try:
            decoded = loads_canonical_json(raw)
        except (TypeError, ValueError) as error:
            raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
                "campaign input blob is not canonical JSON"
            ) from error
        payload = {
            "schema": "acfqp.construction_k7_query_bound_campaign_input_blob.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PRODUCER_PROFILE_KEY,
            "canonical_json_bytes_hex": raw.hex(),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        blob_id = content_id(INPUT_BLOB_DOMAIN, payload)
        expected = {**payload, "campaign_input_blob_id": blob_id}
        if (
            type(decoded) is not dict
            or canonical_json_bytes(decoded) != raw
            or row != expected
            or blob_id in by_id
        ):
            _fail("campaign input blob bytes, ID, or uniqueness changed")
        by_id[blob_id] = raw
        expected_documents.append(expected)
    if tuple(by_id) != tuple(sorted(by_id)):
        _fail("campaign input blob inventory order changed")
    return by_id, expected_documents


def _occurrences(
    documents: Any,
    *,
    blobs_by_id: dict[str, bytes],
) -> tuple[
    list[dict[str, Any]],
    tuple[str, ...],
    tuple[str, ...],
    frozenset[str],
]:
    if type(documents) is not list or len(documents) < 2:
        _fail("preregistered occurrence inventory is absent")
    expected_documents: list[dict[str, Any]] = []
    occurrence_ids: list[str] = []
    occurrence_spec_ids: list[str] = []
    role_blob_ids_by_occurrence: list[dict[str, str]] = []
    for index, candidate in enumerate(documents, start=1):
        row = _exact(candidate, OCCURRENCE_FIELDS, "preregistered occurrence")
        input_roles = row["input_roles"]
        if type(input_roles) is not list or len(input_roles) != len(INPUT_ROLES):
            _fail("preregistered occurrence input role inventory changed")
        role_bytes: dict[str, bytes] = {}
        role_blob_ids: dict[str, str] = {}
        expected_input_rows: list[dict[str, Any]] = []
        for expected_role, expected_filename in INPUT_ROLES:
            source = _exact(
                input_roles[len(expected_input_rows)],
                {
                    "role",
                    "filename",
                    "campaign_input_blob_id",
                    "sha256",
                    "byte_count",
                },
                "preregistered input role",
            )
            blob_id = _cid(source["campaign_input_blob_id"], "campaign input blob")
            raw = blobs_by_id.get(blob_id)
            if raw is None:
                _fail("preregistered occurrence references an unknown input blob")
            expected_input = {
                "role": expected_role,
                "filename": expected_filename,
                "campaign_input_blob_id": blob_id,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
            }
            if source != expected_input:
                _fail("preregistered occurrence input role changed")
            role_bytes[expected_role] = raw
            role_blob_ids[expected_role] = blob_id
            expected_input_rows.append(expected_input)
        try:
            root = query_v1.verify_reusable_abstract_query_result_bytes_v1(
                source_trace_bytes=role_bytes["SOURCE_TRACE"],
                build_epoch_envelope_bytes=role_bytes["BUILD_EPOCH_ENVELOPE"],
                result_bytes=role_bytes["ROOT_QUERY_RESULT"],
            )
            request = request_v1.verify_query_bound_recovery_request_bytes_v1(
                source_trace_bytes=role_bytes["SOURCE_TRACE"],
                build_epoch_envelope_bytes=role_bytes["BUILD_EPOCH_ENVELOPE"],
                root_query_result_bytes=role_bytes["ROOT_QUERY_RESULT"],
                overlay_bytes=role_bytes["RECOVERY_OVERLAY"],
                request_bytes=role_bytes["RECOVERY_REQUEST"],
            )
        except Exception as error:
            raise ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error(
                "preregistered occurrence scientific inputs failed exact replay"
            ) from error
        if request.logical_occurrence_id != root.query.logical_occurrence_id:
            _fail("preregistered root query and recovery request crossed")
        payload = {
            "schema": (
                "acfqp.construction_k7_query_bound_campaign_"
                "preregistered_occurrence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PRODUCER_PROFILE_KEY,
            "occurrence_index": index,
            "logical_occurrence_id": root.query.logical_occurrence_id,
            "query_ordinal": root.query.query_ordinal,
            "input_roles": expected_input_rows,
            "all_scientific_inputs_frozen_before_execution": True,
            "execution_result_present": False,
            "official_execution_allowed": False,
        }
        occurrence_spec_id = content_id(OCCURRENCE_DOMAIN, payload)
        expected = {
            **payload,
            "preregistered_occurrence_spec_id": occurrence_spec_id,
        }
        if row != expected:
            _fail("preregistered occurrence differs from scientific replay")
        expected_documents.append(expected)
        occurrence_ids.append(root.query.logical_occurrence_id)
        occurrence_spec_ids.append(occurrence_spec_id)
        role_blob_ids_by_occurrence.append(role_blob_ids)
    if (
        len(set(occurrence_ids)) != len(occurrence_ids)
        or len(set(occurrence_spec_ids)) != len(occurrence_spec_ids)
    ):
        _fail("preregistered occurrence identity is duplicated")
    for role in COMMON_INPUT_ROLES:
        if len({row[role] for row in role_blob_ids_by_occurrence}) != 1:
            _fail(f"preregistered campaign does not share one {role}")
    for role in OCCURRENCE_SPECIFIC_INPUT_ROLES:
        if len({row[role] for row in role_blob_ids_by_occurrence}) != len(documents):
            _fail(f"preregistered campaign duplicates {role}")
    return (
        expected_documents,
        tuple(occurrence_ids),
        tuple(occurrence_spec_ids),
        frozenset(
            blob_id
            for role_ids in role_blob_ids_by_occurrence
            for blob_id in role_ids.values()
        ),
    )


def _workload(
    document: Any,
    *,
    occurrence_ids: tuple[str, ...],
    occurrence_spec_ids: tuple[str, ...],
) -> tuple[dict[str, Any], str]:
    row = _exact(document, WORKLOAD_FIELDS, "campaign workload spec")
    comparison = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    count = len(occurrence_ids)
    cap = row["permutation_cap"]
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_workload_spec.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "comparison_profile_id": comparison.comparison_profile_id,
        "ordered_logical_occurrence_ids": list(occurrence_ids),
        "ordered_occurrence_spec_ids": list(occurrence_spec_ids),
        "logical_occurrence_count": count,
        "permutation_cap": cap,
        "registration_order_is_denominator_order": True,
        "posthoc_occurrence_deletion_allowed": False,
        "posthoc_occurrence_insertion_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": SCALAR_GATE_STATUS,
        "official_execution_allowed": False,
    }
    workload_id = content_id(WORKLOAD_SPEC_DOMAIN, payload)
    expected = {**payload, "campaign_workload_spec_id": workload_id}
    if (
        type(cap) is not int
        or not (math.factorial(count) <= cap <= MAX_EXPLICIT_PERMUTATIONS)
        or row != expected
    ):
        _fail("campaign workload spec changed")
    return expected, workload_id


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignPreregistrationVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    preregistration_id: str
    workload_spec_id: str
    runtime_preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    source_archive_id: str
    occurrence_ids: tuple[str, ...]
    occurrence_spec_ids: tuple[str, ...]
    input_blob_ids: tuple[str, ...]
    preregistration_bytes_sha256: str
    preregistration_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or len(self.occurrence_ids) < 2
            or len(self.occurrence_ids) != len(self.occurrence_spec_ids)
            or len(set(self.occurrence_ids)) != len(self.occurrence_ids)
            or type(self.preregistration_byte_count) is not int
            or self.preregistration_byte_count <= 0
        ):
            _fail("preregistration verification is caller-minted or malformed")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.preregistration_id, "campaign preregistration"),
            (self.workload_spec_id, "campaign workload spec"),
            (self.runtime_preparation_id, "runtime preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.source_closure_id, "source closure"),
            (self.source_archive_id, "source archive"),
            (self.preregistration_bytes_sha256, "preregistration bytes"),
            *((value, "occurrence") for value in self.occurrence_ids),
            *((value, "occurrence spec") for value in self.occurrence_spec_ids),
            *((value, "input blob") for value in self.input_blob_ids),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_query_bound_campaign_"
                "preregistration_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "source_archive_id": self.source_archive_id,
            "ordered_logical_occurrence_ids": list(self.occurrence_ids),
            "ordered_occurrence_spec_ids": list(self.occurrence_spec_ids),
            "campaign_input_blob_ids": list(self.input_blob_ids),
            "preregistration_bytes_sha256": self.preregistration_bytes_sha256,
            "preregistration_byte_count": self.preregistration_byte_count,
            "producer_module_imported": False,
            "embedded_source_archive_replayed": True,
            "all_scientific_input_chains_replayed": True,
            "ordered_denominator_replayed": True,
            "execution_result_present": False,
            "scientific_campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("preregistration verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_preregistration_verification_id": self.verification_id,
        }


def verify_query_bound_campaign_preregistration_bytes_v1(
    preregistration_bytes: bytes,
) -> QueryBoundCampaignPreregistrationVerificationV1:
    """Replay embedded source, every input chain, denominator, and all IDs."""

    claimed = _exact(
        _canonical(preregistration_bytes),
        PREREGISTRATION_FIELDS,
        "campaign preregistration",
    )
    closure_doc, archive_doc, _archive_raw, _closure = _source_archive(
        source_closure_document=claimed["runtime_preparation"].get("source_closure")
        if type(claimed["runtime_preparation"]) is dict
        else None,
        source_archive_document=claimed["source_archive"],
        source_archive_bytes_hex=claimed["source_archive_bytes_hex"],
    )
    preparation_doc, preparation_id, runtime_tree_id = _runtime_preparation(
        claimed["runtime_preparation"],
        expected_source_closure=closure_doc,
    )
    blobs_by_id, blob_documents = _input_blobs(claimed["input_blobs"])
    (
        occurrence_documents,
        occurrence_ids,
        occurrence_spec_ids,
        referenced_blob_ids,
    ) = _occurrences(
        claimed["preregistered_occurrences"],
        blobs_by_id=blobs_by_id,
    )
    if referenced_blob_ids != frozenset(blobs_by_id):
        _fail("campaign input blob inventory contains an unreferenced blob")
    workload_document, workload_id = _workload(
        claimed["campaign_workload_spec"],
        occurrence_ids=occurrence_ids,
        occurrence_spec_ids=occurrence_spec_ids,
    )
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "registration_stage": REGISTRATION_STAGE,
        "runtime_preparation": preparation_doc,
        "runtime_preparation_id": preparation_id,
        "runtime_tree_id": runtime_tree_id,
        "source_closure_id": closure_doc["closure_id"],
        "source_archive": archive_doc,
        "source_archive_bytes_hex": claimed["source_archive_bytes_hex"],
        "source_bytes_embedded": True,
        "input_blobs": blob_documents,
        "preregistered_occurrences": occurrence_documents,
        "campaign_workload_spec": workload_document,
        "campaign_workload_spec_id": workload_id,
        "ordered_logical_occurrence_ids": list(occurrence_ids),
        "logical_occurrence_count": len(occurrence_ids),
        "campaign_preregistration_present": True,
        "preregistration_contains_execution_result": False,
        "execution_started_by_this_api": False,
        "scientific_campaign_closure_issued": False,
        "certificate_coverage_gate_status": "NOT_RUN",
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": SCALAR_GATE_STATUS,
        "official_execution_allowed": False,
    }
    preregistration_id = content_id(PREREGISTRATION_DOMAIN, payload)
    expected = {
        **payload,
        "query_bound_campaign_preregistration_id": preregistration_id,
    }
    if claimed != expected:
        _fail("campaign preregistration differs from complete bytes replay")
    verification_profile_payload = {
        "schema": (
            "acfqp.construction_k7_query_bound_campaign_"
            "preregistration_verification_profile.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "embedded_source_archive_required": True,
        "scientific_input_replay_required": True,
        "minimum_occurrence_count": 2,
        "execution_result_forbidden": True,
        "official_execution_allowed": False,
    }
    verification_profile_id = content_id(
        VERIFICATION_PROFILE_DOMAIN,
        verification_profile_payload,
    )
    return QueryBoundCampaignPreregistrationVerificationV1(
        _VERIFICATION_ISSUER,
        verification_profile_id,
        preregistration_id,
        workload_id,
        preparation_id,
        runtime_tree_id,
        closure_doc["closure_id"],
        archive_doc["archive_id"],
        occurrence_ids,
        occurrence_spec_ids,
        tuple(blobs_by_id),
        hashlib.sha256(preregistration_bytes).hexdigest(),
        len(preregistration_bytes),
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error",
    "QueryBoundCampaignPreregistrationVerificationV1",
    "verify_query_bound_campaign_preregistration_bytes_v1",
)
