"""Pure authority for the V42 activation evidence successor.

The V42r1 activation transport completed before the trusted bootstrap exec,
but its collector looked for the bootstrap materialization terminal at the
fixed-root top level.  The bootstrap authority publishes that terminal below
``fixed_root/source``.  This module defines a new, read-only evidence protocol
for observing the real nested path.  It deliberately does not manufacture a
V42r1 collector snapshot or final index.

There is no I/O in this module.  Callers must pin paths, prove stable nofollow
reads, and publish the returned documents with append-only storage semantics.
"""

from __future__ import annotations

import hashlib
import re
import shlex
from typing import Any, Mapping, Sequence

from acfqp import (
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.2.0"
DOMAIN_PREFIX = "acfqp:v42-remote-ordinal2:activation-successor:"

SOURCE_MANIFEST_SCHEMA = "acfqp.v42_activation_successor_source_manifest.v42r2"
READ_ONLY_PLAN_SCHEMA = "acfqp.v42_activation_successor_read_only_plan.v42r2"
OBSERVATION_SCHEMA = (
    "acfqp.v42_activation_successor_source_terminal_observation.v42r2"
)
RECEIVER_OBSERVATION_SCHEMA = (
    "acfqp.v42_activation_successor_read_only_observation.v42r2"
)
PATH_PROVENANCE_RECEIPT_SCHEMA = (
    "acfqp.v42_activation_successor_path_provenance_receipt.v42r2"
)
CLASSIFICATION_SCHEMA = "acfqp.v42_activation_successor_classification.v42r2"
SNAPSHOT_SCHEMA = "acfqp.v42_activation_successor_read_only_snapshot.v42r2"
FINAL_INDEX_SCHEMA = (
    "acfqp.v42_activation_successor_final_evidence_index.v42r2"
)
LEGACY_CORE_ANCHOR_SCHEMA = (
    "acfqp.v42_activation_successor_legacy_core_anchor.v42r2"
)

CLASS_SUCCESS = "COMPLETE_NESTED_MATERIALIZATION_SUCCESS"
CLASS_INCOMPLETE = "INCOMPLETE_READ_ONLY_WAIT"

REMOTE_ATTEMPT_RELATIVE_PATH = authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
SOURCE_TERMINAL_RELATIVE_PATH = (
    authority.REMOTE_SOURCE_ROOT.name + "/" + authority.MATERIALIZATION_TERMINAL_NAME
)
REQUIRED_JSON_RELATIVE_PATHS = (
    authority.SOURCE_MANIFEST_NAME,
    authority.TRANSPORT_MANIFEST_NAME,
    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
    REMOTE_ATTEMPT_RELATIVE_PATH,
    SOURCE_TERMINAL_RELATIVE_PATH,
)

SUCCESSOR_LOADER_RELATIVE = "scripts/v42_activation_successor_loader.py"
SUCCESSOR_RECEIVER_RELATIVE = "scripts/v42_activation_successor_receiver.py"

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_FACT_FIELDS = {
    "relative_path",
    "git_mode",
    "git_object_type",
    "git_blob_oid",
    "byte_count",
    "sha256",
}
_RECEIVER_OBSERVATION_DOMAIN = (
    b"acfqp:v42r2:activation-successor-read-only-observation"
)


class V42ActivationSuccessorError(ValueError):
    """A successor authority input or join is not exact."""


def _fail(message: str) -> None:
    raise V42ActivationSuccessorError(message)


def _hex64(value: Any, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail(label + " is not lowercase 64-hex")
    return value


def _canonical_document(raw_or_document: bytes | Mapping[str, Any], label: str) -> dict[str, Any]:
    if type(raw_or_document) is bytes:
        try:
            value = loads_canonical_json(raw_or_document)
        except Exception as error:  # pragma: no cover - normalized below
            raise V42ActivationSuccessorError(label + " is not canonical JSON") from error
        if type(value) is not dict or canonical_json_bytes(value) != raw_or_document:
            _fail(label + " is not one canonical JSON object")
        return dict(value)
    if type(raw_or_document) is not dict:
        _fail(label + " changed type")
    try:
        raw = canonical_json_bytes(raw_or_document)
        value = loads_canonical_json(raw)
    except Exception as error:  # pragma: no cover - normalized below
        raise V42ActivationSuccessorError(label + " is not canonical") from error
    if type(value) is not dict:
        _fail(label + " changed type")
    return dict(value)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (DOMAIN_PREFIX + domain).encode("ascii") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_content_id(
    document: Mapping[str, Any], *, field: str, domain: str, label: str
) -> dict[str, Any]:
    value = _canonical_document(document, label)
    payload = dict(value)
    claimed = payload.pop(field, None)
    if type(claimed) is not str or claimed != _content_id(domain, payload):
        _fail(label + " content identity changed")
    return value


def _legacy_content_id(
    document: Mapping[str, Any], *, field: str, domain: bytes, label: str
) -> dict[str, Any]:
    value = _canonical_document(document, label)
    payload = dict(value)
    claimed = payload.pop(field, None)
    if (
        type(claimed) is not str
        or claimed
        != hashlib.sha256(domain + b"\0" + canonical_json_bytes(payload)).hexdigest()
    ):
        _fail(label + " content identity changed")
    return value


def _artifact(raw: bytes, relative_path: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not 0 < len(raw) <= 8 * 1024**2
        or type(relative_path) is not str
        or not relative_path
        or relative_path.startswith("/")
        or ".." in relative_path.split("/")
    ):
        _fail("successor artifact changed")
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - required Git identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
        "git_mode": "100644",
        "git_object_type": "blob",
    }


def _verify_source_fact(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FACT_FIELDS:
        _fail("successor source fact schema changed")
    relative = value.get("relative_path")
    if (
        type(relative) is not str
        or not relative
        or relative.startswith("/")
        or ".." in relative.split("/")
        or value.get("git_mode") != "100644"
        or value.get("git_object_type") != "blob"
        or type(value.get("git_blob_oid")) is not str
        or _HEX40.fullmatch(value["git_blob_oid"]) is None
        or type(value.get("byte_count")) is not int
        or not 0 < value["byte_count"] <= 8 * 1024**2
        or type(value.get("sha256")) is not str
        or _HEX64.fullmatch(value["sha256"]) is None
    ):
        _fail("successor source fact changed")
    return dict(value)


def build_activation_successor_source_manifest_v42r2(
    *, source_commit: str, source_tree: str,
    source_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        type(source_commit) is not str
        or _HEX40.fullmatch(source_commit) is None
        or type(source_tree) is not str
        or _HEX40.fullmatch(source_tree) is None
        or type(source_facts) not in (list, tuple)
    ):
        _fail("successor source identity changed")
    facts = [_verify_source_fact(dict(item)) for item in source_facts]
    if (
        not facts
        or facts != sorted(facts, key=lambda row: row["relative_path"])
        or len({row["relative_path"] for row in facts}) != len(facts)
        or SUCCESSOR_LOADER_RELATIVE not in {row["relative_path"] for row in facts}
        or SUCCESSOR_RECEIVER_RELATIVE not in {row["relative_path"] for row in facts}
    ):
        _fail("successor source fact inventory changed")
    payload = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "source_facts": facts,
        "all_effectful_successor_python_bound_to_same_committed_tree": True,
        "same_uid_coordinated_replacement_of_repository_and_persistent_anchors_excluded_from_claim": True,
    }
    return {
        **payload,
        "activation_successor_source_manifest_id": _content_id(
            "source-manifest", payload
        ),
    }


def verify_activation_successor_source_manifest_v42r2(
    raw_or_document: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    document = _verify_content_id(
        _canonical_document(raw_or_document, "successor source manifest"),
        field="activation_successor_source_manifest_id",
        domain="source-manifest",
        label="successor source manifest",
    )
    expected = build_activation_successor_source_manifest_v42r2(
        source_commit=document.get("source_commit"),
        source_tree=document.get("source_tree"),
        source_facts=document.get("source_facts"),
    )
    if document != expected:
        _fail("successor source manifest changed")
    return document


def _verify_legacy_activation_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    document = _legacy_content_id(
        value,
        field="materialization_activation_plan_id",
        domain=b"acfqp:v42-remote-ordinal2:materialization-activation-plan",
        label="legacy activation plan",
    )
    if (
        document.get("schema") != activation.MATERIALIZATION_ACTIVATION_PLAN_SCHEMA
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != authority.GLOBAL_EXECUTION_ORDINAL
        or document.get("fixed_remote_root") != str(authority.REMOTE_ROOT)
        or document.get("remote_target_alias") != authority.REMOTE_HOST_ALIAS
        or document.get("expected_remote_hostname") != authority.REMOTE_HOSTNAME
        or document.get("same_activation_identity_retry_forbidden") is not True
    ):
        _fail("legacy activation plan boundary changed")
    ssh = document.get("authorized_read_only_classifier_ssh_argv_template")
    if type(ssh) is not list or len(ssh) != 45 or any(type(item) is not str for item in ssh):
        _fail("legacy activation SSH template changed")
    return document


def _verify_legacy_snapshot_tail(value: Mapping[str, Any], plan_id: str) -> dict[str, Any]:
    document = _legacy_content_id(
        value,
        field="activation_read_only_snapshot_id",
        domain=b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot",
        label="legacy activation snapshot tail",
    )
    classification = document.get("classification")
    if (
        document.get("schema")
        != "acfqp.v42_materialization_activation_read_only_snapshot.v42r1"
        or document.get("materialization_activation_plan_id") != plan_id
        or document.get("remote_observation_only") is not True
        or document.get("activation_effect_replay_authorized") is not False
        or type(classification) is not dict
        or classification.get("classification") != activation.CLASSIFICATION_SUCCESS
        or classification.get("activation_retry_authorized") is not False
        or classification.get("remote_mutation_performed_by_classifier") is not False
    ):
        _fail("legacy activation snapshot tail is not a successful read-only cut")
    _legacy_content_id(
        classification,
        field="materialization_activation_classification_id",
        domain=b"acfqp:v42-remote-ordinal2:materialization-activation-classification",
        label="legacy activation classification",
    )
    return document


def _remote_python_template(
    *, loader_raw: bytes, receiver_artifact: Mapping[str, Any],
) -> list[str]:
    loader = _artifact(loader_raw, SUCCESSOR_LOADER_RELATIVE)
    return [
        authority.REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        "-c",
        loader_raw.decode("utf-8", errors="strict"),
        "--activation-successor-read-only",
        loader["sha256"],
        str(loader["byte_count"]),
        str(receiver_artifact["sha256"]),
        str(receiver_artifact["byte_count"]),
        "{acfqp_v42_activation_successor_plan_id}",
        "{acfqp_v42_legacy_activation_plan_id}",
    ]


def build_activation_successor_read_only_plan_v42r2(
    *, legacy_activation_plan: Mapping[str, Any],
    legacy_snapshot_tail: Mapping[str, Any],
    successor_source_manifest: Mapping[str, Any],
    successor_evidence_root: str,
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
) -> dict[str, Any]:
    old_plan = _verify_legacy_activation_plan(legacy_activation_plan)
    old_plan_id = old_plan["materialization_activation_plan_id"]
    old_snapshot = _verify_legacy_snapshot_tail(legacy_snapshot_tail, old_plan_id)
    source = verify_activation_successor_source_manifest_v42r2(
        successor_source_manifest
    )
    if (
        type(successor_evidence_root) is not str
        or not successor_evidence_root.startswith("/")
        or ".." in successor_evidence_root.split("/")
        or successor_evidence_root == str(authority.REMOTE_ROOT)
    ):
        _fail("successor evidence root changed")
    loader = _artifact(loader_source_raw, SUCCESSOR_LOADER_RELATIVE)
    receiver = _artifact(receiver_source_raw, SUCCESSOR_RECEIVER_RELATIVE)
    fact_by_path = {row["relative_path"]: row for row in source["source_facts"]}
    for artifact in (loader, receiver):
        if fact_by_path.get(artifact["relative_path"]) != artifact:
            _fail("successor executable artifact is not in its source manifest")
    remote_python = _remote_python_template(
        loader_raw=loader_source_raw, receiver_artifact=receiver
    )
    ssh_prefix = old_plan["authorized_read_only_classifier_ssh_argv_template"][:44]
    ssh_template = [
        *ssh_prefix,
        "builtin exec -c " + " ".join(shlex.quote(item) for item in remote_python),
    ]
    classification = old_snapshot["classification"]
    payload = {
        "schema": READ_ONLY_PLAN_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "legacy_materialization_activation_plan_id": old_plan_id,
        "legacy_activation_read_only_snapshot_tail_id": old_snapshot[
            "activation_read_only_snapshot_id"
        ],
        "legacy_activation_classification_id": classification[
            "materialization_activation_classification_id"
        ],
        "legacy_remote_materialization_transport_terminal_id": classification[
            "remote_materialization_transport_terminal_id"
        ],
        "preactivation_resource_result_id": old_plan[
            "preactivation_resource_result_id"
        ],
        "source_commit": old_plan["source_commit"],
        "source_tree": old_plan["source_tree"],
        "source_manifest_id": old_plan["source_manifest_id"],
        "transport_manifest_id": old_plan["transport_manifest_id"],
        "local_materialization_attempt_id": old_plan[
            "local_materialization_attempt_id"
        ],
        "activation_successor_source_manifest_id": source[
            "activation_successor_source_manifest_id"
        ],
        "successor_evidence_root": successor_evidence_root,
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "remote_source_root": str(authority.REMOTE_SOURCE_ROOT),
        "remote_attempt_relative_path": REMOTE_ATTEMPT_RELATIVE_PATH,
        "source_terminal_relative_path": SOURCE_TERMINAL_RELATIVE_PATH,
        "required_json_relative_paths": list(REQUIRED_JSON_RELATIVE_PATHS),
        "remote_target_alias": authority.REMOTE_HOST_ALIAS,
        "expected_remote_hostname": authority.REMOTE_HOSTNAME,
        "ssh_client_contract": old_plan["ssh_client_contract"],
        "remote_startup_tcb_contract": old_plan["remote_startup_tcb_contract"],
        "activation_successor_loader_artifact": loader,
        "activation_successor_receiver_artifact": receiver,
        "authorized_remote_python_argv_template": remote_python,
        "authorized_ssh_argv_template": ssh_template,
        "ssh_prefix_copied_byte_for_byte_from_legacy_classifier": True,
        "remote_observation_only": True,
        "remote_mutation_authorized": False,
        "activation_effect_replay_authorized": False,
        "systemd_queries_or_effects_authorized": False,
        "legacy_activation_evidence_root_must_remain_read_only": True,
        "native_successor_evidence_must_use_distinct_append_only_root": True,
        "same_uid_coordinated_replacement_of_named_roots_and_all_persistent_anchors_excluded_from_claim": True,
    }
    return {
        **payload,
        "activation_successor_read_only_plan_id": _content_id("read-only-plan", payload),
    }


def verify_activation_successor_read_only_plan_v42r2(
    raw_or_document: bytes | Mapping[str, Any], **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor read-only plan")
    expected = build_activation_successor_read_only_plan_v42r2(**build_arguments)
    if document != expected:
        _fail("successor read-only plan changed")
    return document


def materialize_activation_successor_remote_python_argv_v42r2(
    plan: Mapping[str, Any], *, loader_source_raw: bytes,
) -> list[str]:
    document = _verify_content_id(
        plan,
        field="activation_successor_read_only_plan_id",
        domain="read-only-plan",
        label="successor read-only plan",
    )
    template = document.get("authorized_remote_python_argv_template")
    if type(template) is not list or len(template) != 13:
        _fail("successor remote Python template changed")
    expected = _remote_python_template(
        loader_raw=loader_source_raw,
        receiver_artifact=document["activation_successor_receiver_artifact"],
    )
    if template != expected:
        _fail("successor remote Python template changed")
    result = list(template)
    result[11] = document["activation_successor_read_only_plan_id"]
    result[12] = document["legacy_materialization_activation_plan_id"]
    return result


def materialize_activation_successor_ssh_argv_v42r2(
    plan: Mapping[str, Any], *, loader_source_raw: bytes,
) -> list[str]:
    document = _verify_content_id(
        plan,
        field="activation_successor_read_only_plan_id",
        domain="read-only-plan",
        label="successor read-only plan",
    )
    remote = materialize_activation_successor_remote_python_argv_v42r2(
        document, loader_source_raw=loader_source_raw
    )
    template = document.get("authorized_ssh_argv_template")
    if type(template) is not list or len(template) != 45:
        _fail("successor SSH template changed")
    expected_tail = "builtin exec -c " + " ".join(
        shlex.quote(item) for item in document["authorized_remote_python_argv_template"]
    )
    if template[44] != expected_tail:
        _fail("successor SSH template tail changed")
    return [
        *template[:44],
        "builtin exec -c " + " ".join(shlex.quote(item) for item in remote),
    ]


def _receiver_identity(value: Any, label: str, *, node_type: str) -> dict[str, Any]:
    fields = {
        "path", "node_type", "mode", "uid", "gid", "st_dev", "st_ino",
        "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns",
    }
    if type(value) is not dict or set(value) != fields:
        _fail(label + " receiver identity schema changed")
    path = value.get("path")
    if (
        type(path) is not str
        or not path.startswith("/")
        or ".." in path.split("/")
        or value.get("node_type") != node_type
        or type(value.get("mode")) is not int
        or type(value.get("uid")) is not int
        or type(value.get("gid")) is not int
        or any(
            type(value.get(key)) is not int or value[key] < 0
            for key in fields
            - {"path", "node_type", "mode", "uid", "gid"}
        )
        or value["uid"] != authority.REMOTE_UID
        or value["gid"] != authority.REMOTE_GID
    ):
        _fail(label + " receiver identity changed")
    if node_type == "REGULAR_FILE":
        if value["mode"] != 0o400 or value["st_nlink"] != 1 or value["st_size"] <= 0:
            _fail(label + " receiver file storage changed")
    elif value["mode"] != 0o700 or value["st_nlink"] < 1:
        _fail(label + " receiver directory storage changed")
    return dict(value)


def _strip_receiver_path(identity: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in identity.items() if key != "path"}


def verify_activation_successor_receiver_observation_v42r2(
    raw_or_document: bytes | Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the stdlib-only receiver's raw, path-bearing observation."""

    document = _canonical_document(raw_or_document, "successor receiver observation")
    payload = dict(document)
    claimed = payload.pop("activation_successor_read_only_observation_id", None)
    if (
        type(claimed) is not str
        or claimed
        != hashlib.sha256(
            _RECEIVER_OBSERVATION_DOMAIN + b"\0" + canonical_json_bytes(payload)
        ).hexdigest()
    ):
        _fail("successor receiver observation identity changed")
    required = {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "observed_hostname", "observed_user", "observed_uid", "observed_gid",
        "fixed_root_lexical_chain_before", "fixed_root_lexical_chain_after",
        "fixed_root", "source_root", "documents",
        "single_pinned_before_after_window", "all_document_reads_nofollow_and_stable",
        "collected_subset_only_not_whole_tree", "large_binary_content_read",
        "observed_document_count", "remote_mutation_performed",
        "only_fixed_small_json_documents_read",
        "activation_successor_read_only_observation_id",
    }
    if (
        set(document) != required
        or document.get("schema") != RECEIVER_OBSERVATION_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != authority.GLOBAL_EXECUTION_ORDINAL
        or document.get("observed_hostname") != authority.REMOTE_HOSTNAME
        or document.get("observed_user") != authority.REMOTE_USER
        or document.get("observed_uid") != authority.REMOTE_UID
        or document.get("observed_gid") != authority.REMOTE_GID
        or document.get("fixed_root_lexical_chain_before")
        != document.get("fixed_root_lexical_chain_after")
        or document.get("single_pinned_before_after_window") is not True
        or document.get("all_document_reads_nofollow_and_stable") is not True
        or document.get("collected_subset_only_not_whole_tree") is not True
        or document.get("large_binary_content_read") is not False
        or document.get("observed_document_count") != len(REQUIRED_JSON_RELATIVE_PATHS)
        or document.get("remote_mutation_performed") is not False
        or document.get("only_fixed_small_json_documents_read") is not True
    ):
        _fail("successor receiver observation contract changed")
    fixed = document.get("fixed_root")
    source = document.get("source_root")
    for row, path, label in (
        (fixed, str(authority.REMOTE_ROOT), "fixed root"),
        (source, str(authority.REMOTE_SOURCE_ROOT), "source root"),
    ):
        if (
            type(row) is not dict
            or set(row)
            != {
                "path", "identity_before", "identity_opened", "identity_after",
                "inventory_before", "inventory_after",
            }
            or row.get("path") != path
            or row.get("inventory_before") != row.get("inventory_after")
            or type(row.get("inventory_before")) is not list
            or row["inventory_before"] != sorted(set(row["inventory_before"]))
        ):
            _fail(label + " receiver row changed")
        identities = [
            _receiver_identity(row[key], label, node_type="DIRECTORY")
            for key in ("identity_before", "identity_opened", "identity_after")
        ]
        if identities[0] != identities[1] or identities[0] != identities[2]:
            _fail(label + " receiver identity changed across observation")
    documents = document.get("documents")
    role_map = {
        "source_manifest": ("fixed_root", authority.SOURCE_MANIFEST_NAME),
        "transport_manifest": ("fixed_root", authority.TRANSPORT_MANIFEST_NAME),
        "local_materialization_attempt": (
            "fixed_root", authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        ),
        "remote_materialization_attempt": (
            "fixed_root", REMOTE_ATTEMPT_RELATIVE_PATH,
        ),
        "materialization_terminal": (
            "source_root", authority.MATERIALIZATION_TERMINAL_NAME,
        ),
    }
    if type(documents) is not dict or set(documents) != set(role_map):
        _fail("successor receiver document inventory changed")
    for role, (parent, name) in role_map.items():
        row = documents[role]
        parent_path = (
            str(authority.REMOTE_ROOT)
            if parent == "fixed_root"
            else str(authority.REMOTE_SOURCE_ROOT)
        )
        if (
            type(row) is not dict
            or set(row)
            != {
                "absolute_path", "relative_name", "identity_before",
                "identity_opened", "identity_after", "byte_count", "sha256",
                "document", "parent",
            }
            or row.get("parent") != parent
            or row.get("relative_name") != name
            or row.get("absolute_path") != parent_path + "/" + name
            or type(row.get("document")) is not dict
        ):
            _fail("successor receiver document row changed: " + role)
        identities = [
            _receiver_identity(row[key], role, node_type="REGULAR_FILE")
            for key in ("identity_before", "identity_opened", "identity_after")
        ]
        raw = canonical_json_bytes(row["document"])
        if (
            identities[0] != identities[1]
            or identities[0] != identities[2]
            or row.get("byte_count") != len(raw)
            or identities[0]["st_size"] != len(raw)
            or row.get("sha256") != hashlib.sha256(raw).hexdigest()
        ):
            _fail("successor receiver document bytes changed: " + role)
    return document


def build_activation_successor_path_provenance_receipt_v42r2(
    *, plan: Mapping[str, Any], receiver_observation: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan, field="activation_successor_read_only_plan_id",
        domain="read-only-plan", label="successor read-only plan",
    )
    receiver = verify_activation_successor_receiver_observation_v42r2(
        receiver_observation
    )
    role_to_relative = {
        "source_manifest": authority.SOURCE_MANIFEST_NAME,
        "transport_manifest": authority.TRANSPORT_MANIFEST_NAME,
        "local_materialization_attempt": authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        "remote_materialization_attempt": REMOTE_ATTEMPT_RELATIVE_PATH,
        "materialization_terminal": SOURCE_TERMINAL_RELATIVE_PATH,
    }
    documents: dict[str, dict[str, Any]] = {}
    identities: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for role, relative in role_to_relative.items():
        row = receiver["documents"][role]
        documents[relative] = row["document"]
        identities[relative] = _strip_receiver_path(row["identity_before"])
        hashes[relative] = row["sha256"]
    payload = {
        "schema": PATH_PROVENANCE_RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_read_only_plan_id": selected_plan[
            "activation_successor_read_only_plan_id"
        ],
        "receiver_observation_id": receiver[
            "activation_successor_read_only_observation_id"
        ],
        "observed_hostname": receiver["observed_hostname"],
        "observed_user": receiver["observed_user"],
        "observed_uid": receiver["observed_uid"],
        "observed_gid": receiver["observed_gid"],
        "fixed_remote_root": str(authority.REMOTE_ROOT),
        "remote_source_root": str(authority.REMOTE_SOURCE_ROOT),
        "nested_terminal_relative_path": SOURCE_TERMINAL_RELATIVE_PATH,
        "root_identity": _strip_receiver_path(
            receiver["fixed_root"]["identity_before"]
        ),
        "source_identity": _strip_receiver_path(
            receiver["source_root"]["identity_before"]
        ),
        "root_inventory": receiver["fixed_root"]["inventory_before"],
        "source_inventory": receiver["source_root"]["inventory_before"],
        "file_identities": identities,
        "document_sha256": hashes,
        "documents": documents,
        "single_pinned_before_after_window": True,
        "all_paths_opened_nofollow": True,
        "all_reads_and_inventories_stable": True,
        "large_binary_content_read": False,
        "remote_mutation_performed": False,
        "systemd_query_or_effect_performed": False,
        "activation_effect_replay_performed": False,
    }
    return {
        **payload,
        "activation_successor_path_provenance_receipt_id": _content_id(
            "path-provenance-receipt", payload
        ),
    }


def verify_activation_successor_path_provenance_receipt_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
    receiver_observation: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor path receipt")
    expected = build_activation_successor_path_provenance_receipt_v42r2(
        plan=plan, receiver_observation=receiver_observation
    )
    if document != expected:
        _fail("successor path provenance receipt changed")
    return document


def build_activation_successor_observation_v42r2(
    *, plan: Mapping[str, Any], path_provenance_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan, field="activation_successor_read_only_plan_id",
        domain="read-only-plan", label="successor read-only plan",
    )
    receipt = _verify_content_id(
        path_provenance_receipt,
        field="activation_successor_path_provenance_receipt_id",
        domain="path-provenance-receipt",
        label="successor path provenance receipt",
    )
    if receipt.get("activation_successor_read_only_plan_id") != selected_plan[
        "activation_successor_read_only_plan_id"
    ]:
        _fail("successor path receipt lost its plan join")
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_read_only_plan_id": selected_plan[
            "activation_successor_read_only_plan_id"
        ],
        "legacy_materialization_activation_plan_id": selected_plan[
            "legacy_materialization_activation_plan_id"
        ],
        "activation_successor_path_provenance_receipt_id": receipt[
            "activation_successor_path_provenance_receipt_id"
        ],
        "observed_hostname": receipt["observed_hostname"],
        "observed_user": receipt["observed_user"],
        "observed_uid": receipt["observed_uid"],
        "observed_gid": receipt["observed_gid"],
        "fixed_remote_root": receipt["fixed_remote_root"],
        "remote_source_root": receipt["remote_source_root"],
        "root_identity_before": receipt["root_identity"],
        "root_identity_after": receipt["root_identity"],
        "source_identity_before": receipt["source_identity"],
        "source_identity_after": receipt["source_identity"],
        "root_inventory_before": receipt["root_inventory"],
        "root_inventory_after": receipt["root_inventory"],
        "source_inventory_before": receipt["source_inventory"],
        "source_inventory_after": receipt["source_inventory"],
        "file_identities_before": receipt["file_identities"],
        "file_identities_after": receipt["file_identities"],
        "document_sha256": receipt["document_sha256"],
        "documents": receipt["documents"],
        "all_paths_opened_nofollow": True,
        "all_reads_stable": True,
        "all_inventories_and_identities_equal_before_after": True,
        "remote_mutation_performed": False,
        "systemd_query_or_effect_performed": False,
        "activation_effect_replay_performed": False,
    }
    return {
        **payload,
        "activation_successor_observation_id": _content_id(
            "source-terminal-observation", payload
        ),
    }


def _verify_identity(value: Any, label: str, *, node_type: str) -> dict[str, Any]:
    fields = {
        "node_type", "mode", "uid", "gid", "st_dev", "st_ino", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    }
    if type(value) is not dict or set(value) != fields:
        _fail(label + " identity schema changed")
    if (
        value.get("node_type") != node_type
        or type(value.get("mode")) is not int
        or type(value.get("uid")) is not int
        or type(value.get("gid")) is not int
        or any(type(value.get(key)) is not int or value[key] < 0 for key in fields - {"node_type", "mode", "uid", "gid"})
        or value["uid"] != authority.REMOTE_UID
        or value["gid"] != authority.REMOTE_GID
    ):
        _fail(label + " identity changed")
    if node_type == "REGULAR_FILE":
        if value["mode"] != 0o400 or value["st_nlink"] != 1 or value["st_size"] <= 0:
            _fail(label + " file storage changed")
    elif value["mode"] != 0o700 or value["st_nlink"] < 1:
        _fail(label + " directory storage changed")
    return dict(value)


def verify_activation_successor_observation_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan,
        field="activation_successor_read_only_plan_id",
        domain="read-only-plan",
        label="successor read-only plan",
    )
    document = _verify_content_id(
        _canonical_document(raw_or_document, "successor observation"),
        field="activation_successor_observation_id",
        domain="source-terminal-observation",
        label="successor observation",
    )
    required = {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "activation_successor_read_only_plan_id",
        "legacy_materialization_activation_plan_id",
        "activation_successor_path_provenance_receipt_id", "observed_hostname",
        "observed_user", "observed_uid", "observed_gid", "fixed_remote_root",
        "remote_source_root", "root_identity_before", "root_identity_after",
        "source_identity_before", "source_identity_after", "root_inventory_before",
        "root_inventory_after", "source_inventory_before", "source_inventory_after",
        "file_identities_before", "file_identities_after", "document_sha256",
        "documents", "all_paths_opened_nofollow", "all_reads_stable",
        "all_inventories_and_identities_equal_before_after", "remote_mutation_performed",
        "systemd_query_or_effect_performed", "activation_effect_replay_performed",
        "activation_successor_observation_id",
    }
    documents = document.get("documents")
    file_before = document.get("file_identities_before")
    file_after = document.get("file_identities_after")
    hashes = document.get("document_sha256")
    if (
        set(document) != required
        or document.get("schema") != OBSERVATION_SCHEMA
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal") != authority.GLOBAL_EXECUTION_ORDINAL
        or document.get("activation_successor_read_only_plan_id")
        != selected_plan["activation_successor_read_only_plan_id"]
        or document.get("legacy_materialization_activation_plan_id")
        != selected_plan["legacy_materialization_activation_plan_id"]
        or type(document.get("activation_successor_path_provenance_receipt_id"))
        is not str
        or _HEX64.fullmatch(
            document["activation_successor_path_provenance_receipt_id"]
        )
        is None
        or document.get("observed_hostname") != authority.REMOTE_HOSTNAME
        or document.get("observed_user") != authority.REMOTE_USER
        or document.get("observed_uid") != authority.REMOTE_UID
        or document.get("observed_gid") != authority.REMOTE_GID
        or document.get("fixed_remote_root") != str(authority.REMOTE_ROOT)
        or document.get("remote_source_root") != str(authority.REMOTE_SOURCE_ROOT)
        or document.get("root_inventory_before") != document.get("root_inventory_after")
        or document.get("source_inventory_before") != document.get("source_inventory_after")
        or file_before != file_after
        or type(documents) is not dict
        or set(documents) != set(REQUIRED_JSON_RELATIVE_PATHS)
        or type(file_before) is not dict
        or set(file_before) != set(REQUIRED_JSON_RELATIVE_PATHS)
        or type(hashes) is not dict
        or set(hashes) != set(REQUIRED_JSON_RELATIVE_PATHS)
        or document.get("all_paths_opened_nofollow") is not True
        or document.get("all_reads_stable") is not True
        or document.get("all_inventories_and_identities_equal_before_after") is not True
        or document.get("remote_mutation_performed") is not False
        or document.get("systemd_query_or_effect_performed") is not False
        or document.get("activation_effect_replay_performed") is not False
    ):
        _fail("successor observation contract changed")
    root_before = _verify_identity(document["root_identity_before"], "fixed root", node_type="DIRECTORY")
    root_after = _verify_identity(document["root_identity_after"], "fixed root", node_type="DIRECTORY")
    source_before = _verify_identity(document["source_identity_before"], "source root", node_type="DIRECTORY")
    source_after = _verify_identity(document["source_identity_after"], "source root", node_type="DIRECTORY")
    if root_before != root_after or source_before != source_after:
        _fail("successor directory identity changed")
    for relative in REQUIRED_JSON_RELATIVE_PATHS:
        identity = _verify_identity(file_before[relative], relative, node_type="REGULAR_FILE")
        if identity != file_after[relative]:
            _fail("successor file identity changed")
        value = documents[relative]
        if type(value) is not dict:
            _fail("successor observed document changed type")
        raw = canonical_json_bytes(value)
        if len(raw) != identity["st_size"] or hashes[relative] != hashlib.sha256(raw).hexdigest():
            _fail("successor observed document bytes changed")
    return document


def build_activation_successor_classification_v42r2(
    *, plan: Mapping[str, Any], observation: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan,
        field="activation_successor_read_only_plan_id",
        domain="read-only-plan",
        label="successor read-only plan",
    )
    observed = verify_activation_successor_observation_v42r2(
        observation, plan=selected_plan
    )
    docs = observed["documents"]
    source = authority.verify_source_manifest_v42r1(
        docs[authority.SOURCE_MANIFEST_NAME]
    )
    transport = authority.verify_transport_manifest_v42r1(
        docs[authority.TRANSPORT_MANIFEST_NAME], source_manifest=source
    )
    local = authority.verify_local_materialization_attempt_v42r1(
        docs[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        source_manifest=source, transport_manifest=transport,
    )
    remote = authority.verify_remote_materialization_attempt_v42r1(
        docs[REMOTE_ATTEMPT_RELATIVE_PATH],
        local_materialization_attempt=local, source_manifest=source,
        transport_manifest=transport,
    )
    terminal = authority.verify_materialization_terminal_v42r1(
        docs[SOURCE_TERMINAL_RELATIVE_PATH],
        local_materialization_attempt=local,
        remote_materialization_attempt=remote,
        source_manifest=source, transport_manifest=transport,
    )
    if (
        source["source_commit"] != selected_plan["source_commit"]
        or source["source_tree"] != selected_plan["source_tree"]
        or source["source_manifest_id"] != selected_plan["source_manifest_id"]
        or transport["transport_manifest_id"]
        != selected_plan["transport_manifest_id"]
        or local["local_materialization_attempt_id"]
        != selected_plan["local_materialization_attempt_id"]
    ):
        _fail("successor materialization controls differ from plan")
    payload = {
        "schema": CLASSIFICATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_read_only_plan_id": selected_plan[
            "activation_successor_read_only_plan_id"
        ],
        "activation_successor_observation_id": observed[
            "activation_successor_observation_id"
        ],
        "activation_successor_path_provenance_receipt_id": observed[
            "activation_successor_path_provenance_receipt_id"
        ],
        "classification": CLASS_SUCCESS,
        "source_manifest_id": source["source_manifest_id"],
        "transport_manifest_id": transport["transport_manifest_id"],
        "local_materialization_attempt_id": local["local_materialization_attempt_id"],
        "remote_materialization_attempt_id": remote["remote_materialization_attempt_id"],
        "materialization_terminal_id": terminal["materialization_terminal_id"],
        "nested_terminal_relative_path": SOURCE_TERMINAL_RELATIVE_PATH,
        "nested_terminal_path_provenance_verified": True,
        "read_only_remote_observation_only": True,
        "remote_mutation_performed": False,
        "activation_effect_replay_authorized": False,
        "formal_effect_authorized_by_classification_alone": False,
    }
    return {
        **payload,
        "activation_successor_classification_id": _content_id("classification", payload),
    }


def verify_activation_successor_classification_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor classification")
    expected = build_activation_successor_classification_v42r2(
        plan=plan, observation=observation
    )
    if document != expected:
        _fail("successor classification changed")
    return document


def build_activation_successor_snapshot_v42r2(
    *, plan: Mapping[str, Any], observation: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan, field="activation_successor_read_only_plan_id",
        domain="read-only-plan", label="successor read-only plan",
    )
    observed = verify_activation_successor_observation_v42r2(
        observation, plan=selected_plan
    )
    classified = verify_activation_successor_classification_v42r2(
        classification, plan=selected_plan, observation=observed
    )
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_read_only_plan_id": selected_plan[
            "activation_successor_read_only_plan_id"
        ],
        "legacy_activation_read_only_snapshot_tail_id": selected_plan[
            "legacy_activation_read_only_snapshot_tail_id"
        ],
        "activation_successor_observation_id": observed[
            "activation_successor_observation_id"
        ],
        "activation_successor_classification_id": classified[
            "activation_successor_classification_id"
        ],
        "activation_successor_path_provenance_receipt_id": classified[
            "activation_successor_path_provenance_receipt_id"
        ],
        "remote_observation_only": True,
        "legacy_activation_evidence_mutated": False,
        "activation_effect_replay_authorized": False,
    }
    return {
        **payload,
        "activation_successor_read_only_snapshot_id": _content_id("snapshot", payload),
    }


def verify_activation_successor_snapshot_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
    observation: Mapping[str, Any], classification: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor snapshot")
    expected = build_activation_successor_snapshot_v42r2(
        plan=plan, observation=observation, classification=classification
    )
    if document != expected:
        _fail("successor snapshot changed")
    return document


def build_activation_successor_final_evidence_index_v42r2(
    *, plan: Mapping[str, Any], snapshot: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    selected_plan = _verify_content_id(
        plan, field="activation_successor_read_only_plan_id",
        domain="read-only-plan", label="successor read-only plan",
    )
    classified = _verify_content_id(
        classification, field="activation_successor_classification_id",
        domain="classification", label="successor classification",
    )
    selected_snapshot = _verify_content_id(
        snapshot, field="activation_successor_read_only_snapshot_id",
        domain="snapshot", label="successor snapshot",
    )
    if (
        classified.get("classification") != CLASS_SUCCESS
        or selected_snapshot.get("activation_successor_read_only_plan_id")
        != selected_plan["activation_successor_read_only_plan_id"]
        or selected_snapshot.get("activation_successor_classification_id")
        != classified["activation_successor_classification_id"]
    ):
        _fail("successor final inputs changed")
    payload = {
        "schema": FINAL_INDEX_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_source_manifest_id": selected_plan[
            "activation_successor_source_manifest_id"
        ],
        "activation_successor_read_only_plan_id": selected_plan[
            "activation_successor_read_only_plan_id"
        ],
        "activation_successor_read_only_snapshot_id": selected_snapshot[
            "activation_successor_read_only_snapshot_id"
        ],
        "activation_successor_classification_id": classified[
            "activation_successor_classification_id"
        ],
        "activation_successor_path_provenance_receipt_id": classified[
            "activation_successor_path_provenance_receipt_id"
        ],
        "legacy_materialization_activation_plan_id": selected_plan[
            "legacy_materialization_activation_plan_id"
        ],
        "legacy_activation_read_only_snapshot_tail_id": selected_plan[
            "legacy_activation_read_only_snapshot_tail_id"
        ],
        "legacy_activation_classification_id": selected_plan[
            "legacy_activation_classification_id"
        ],
        "legacy_remote_materialization_transport_terminal_id": selected_plan[
            "legacy_remote_materialization_transport_terminal_id"
        ],
        "preactivation_resource_result_id": selected_plan[
            "preactivation_resource_result_id"
        ],
        "source_manifest_id": classified["source_manifest_id"],
        "transport_manifest_id": classified["transport_manifest_id"],
        "local_materialization_attempt_id": classified[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": classified[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": classified["materialization_terminal_id"],
        "nested_terminal_relative_path": SOURCE_TERMINAL_RELATIVE_PATH,
        "native_nested_path_evidence_complete": True,
        "legacy_activation_final_evidence_index_claimed": False,
        "formal_evidence_bundle_complete_under_successor_claim": True,
        "activation_effect_replay_authorized": False,
        "same_uid_coordinated_replacement_of_named_roots_and_all_persistent_anchors_excluded_from_claim": True,
    }
    return {
        **payload,
        "activation_successor_final_evidence_index_id": _content_id(
            "final-evidence-index", payload
        ),
    }


def verify_activation_successor_final_evidence_index_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *, plan: Mapping[str, Any],
    snapshot: Mapping[str, Any], classification: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor final evidence index")
    expected = build_activation_successor_final_evidence_index_v42r2(
        plan=plan, snapshot=snapshot, classification=classification
    )
    if document != expected:
        _fail("successor final evidence index changed")
    return document


def build_activation_successor_legacy_core_anchor_v42r2(
    *, final_evidence_index: Mapping[str, Any],
    preactivation_resource_result_id: str,
) -> dict[str, Any]:
    final = _verify_content_id(
        final_evidence_index,
        field="activation_successor_final_evidence_index_id",
        domain="final-evidence-index",
        label="successor final evidence index",
    )
    _hex64(preactivation_resource_result_id, "preactivation resource result ID")
    if (
        final.get("formal_evidence_bundle_complete_under_successor_claim") is not True
        or final.get("legacy_activation_final_evidence_index_claimed") is not False
        or final.get("preactivation_resource_result_id")
        != preactivation_resource_result_id
    ):
        _fail("successor final evidence is not bridge eligible")
    payload = {
        "schema": LEGACY_CORE_ANCHOR_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "activation_successor_final_evidence_index_id": final[
            "activation_successor_final_evidence_index_id"
        ],
        "legacy_materialization_activation_plan_id": final[
            "legacy_materialization_activation_plan_id"
        ],
        "legacy_remote_materialization_transport_terminal_id": final[
            "legacy_remote_materialization_transport_terminal_id"
        ],
        "preactivation_resource_result_id": preactivation_resource_result_id,
        "source_manifest_id": final["source_manifest_id"],
        "transport_manifest_id": final["transport_manifest_id"],
        "local_materialization_attempt_id": final[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": final[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": final["materialization_terminal_id"],
        "opaque_v42r1_core_anchor_only_not_a_legacy_final_index": True,
        "native_successor_final_verified_before_legacy_core_construction": True,
        "nested_terminal_path_provenance_verified": True,
        "activation_effect_replay_authorized": False,
    }
    return {
        **payload,
        "activation_successor_legacy_core_anchor_id": _content_id(
            "legacy-core-anchor", payload
        ),
    }


def verify_activation_successor_legacy_core_anchor_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *,
    final_evidence_index: Mapping[str, Any],
    preactivation_resource_result_id: str,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor legacy core anchor")
    expected = build_activation_successor_legacy_core_anchor_v42r2(
        final_evidence_index=final_evidence_index,
        preactivation_resource_result_id=preactivation_resource_result_id,
    )
    if document != expected:
        _fail("successor legacy core anchor changed")
    return document


__all__ = [
    "CLASS_INCOMPLETE",
    "CLASS_SUCCESS",
    "FINAL_INDEX_SCHEMA",
    "LEGACY_CORE_ANCHOR_SCHEMA",
    "OBSERVATION_SCHEMA",
    "PATH_PROVENANCE_RECEIPT_SCHEMA",
    "READ_ONLY_PLAN_SCHEMA",
    "RECEIVER_OBSERVATION_SCHEMA",
    "REQUIRED_JSON_RELATIVE_PATHS",
    "SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA",
    "SOURCE_MANIFEST_SCHEMA",
    "SOURCE_TERMINAL_RELATIVE_PATH",
    "SUCCESSOR_LOADER_RELATIVE",
    "SUCCESSOR_RECEIVER_RELATIVE",
    "V42ActivationSuccessorError",
    "build_activation_successor_classification_v42r2",
    "build_activation_successor_final_evidence_index_v42r2",
    "build_activation_successor_legacy_core_anchor_v42r2",
    "build_activation_successor_observation_v42r2",
    "build_activation_successor_path_provenance_receipt_v42r2",
    "build_activation_successor_read_only_plan_v42r2",
    "build_activation_successor_snapshot_v42r2",
    "build_activation_successor_source_manifest_v42r2",
    "materialize_activation_successor_remote_python_argv_v42r2",
    "materialize_activation_successor_ssh_argv_v42r2",
    "verify_activation_successor_classification_v42r2",
    "verify_activation_successor_final_evidence_index_v42r2",
    "verify_activation_successor_legacy_core_anchor_v42r2",
    "verify_activation_successor_observation_v42r2",
    "verify_activation_successor_path_provenance_receipt_v42r2",
    "verify_activation_successor_read_only_plan_v42r2",
    "verify_activation_successor_receiver_observation_v42r2",
    "verify_activation_successor_snapshot_v42r2",
    "verify_activation_successor_source_manifest_v42r2",
]
