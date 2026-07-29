#!/usr/bin/env python3
"""Compile the immutable public source boundary for V0-075.

This command consumes only the three completed source-only replay outputs.
It first verifies them through the law-free public source-work authority,
then compiles the frozen proposal archive and source-prior adapter.  It never
opens a target observer or reads a private target environment.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp import v075_frozen_source_proposal_archive_v1 as source_archive
from acfqp import v075_public_source_work_authority_v1 as public_source_work
from acfqp import v075_source_offline_work_materializer_v1 as source_work
from acfqp import v075_source_prior_adapter_v1 as source_prior


INPUT_FILENAMES = {
    "materialization": "v075_source_offline_work_materialization_v1.json",
    "verification": (
        "v075_source_offline_work_materialization_verification_v1.json"
    ),
    "status": "v075_source_replay_materialization_status_v1.json",
}

OUTPUT_FILENAMES = {
    "archive": "V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE.json",
    "archive_verification": (
        "V075_FROZEN_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION.json"
    ),
    "materialization": "V075_SOURCE_OFFLINE_WORK_MATERIALIZATION.json",
    "materialization_verification": (
        "V075_SOURCE_OFFLINE_WORK_MATERIALIZATION_VERIFICATION.json"
    ),
    "source_replay_status": "V075_SOURCE_REPLAY_MATERIALIZATION_STATUS.json",
    "public_source_work_bundle": "V075_VERIFIED_PUBLIC_SOURCE_WORK_BUNDLE.json",
    "source_prior": "V075_SOURCE_PRIOR_ADAPTER.json",
    "source_prior_verification": (
        "V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json"
    ),
}


class V075PublicSourceArtifactCompilationViolation(ValueError):
    """The input directory, source identity graph, or output path is invalid."""


def _fail(message: str) -> None:
    raise V075PublicSourceArtifactCompilationViolation(message)


def _real_directory(value: str, field_name: str) -> Path:
    path = Path(value)
    if (
        not path.is_absolute()
        or not path.is_dir()
        or path.is_symlink()
        or path.resolve(strict=True) != path
    ):
        _fail(f"{field_name} must be one absolute real directory")
    return path


def _read_regular(path: Path, cap: int) -> bytes:
    try:
        info = path.lstat()
    except OSError as error:
        raise V075PublicSourceArtifactCompilationViolation(
            f"required source artifact is absent: {path.name}"
        ) from error
    if (
        not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_size <= 0
        or info.st_size > cap
    ):
        _fail(f"source artifact is not one bounded regular file: {path.name}")
    raw = path.read_bytes()
    if len(raw) != info.st_size:
        _fail(f"source artifact changed during read: {path.name}")
    return raw


def _write_exclusive(path: Path, raw: bytes) -> None:
    if (
        type(raw) is not bytes
        or not raw
        or not path.is_absolute()
        or path.exists()
        or path.is_symlink()
    ):
        _fail(f"output path is not one new canonical artifact: {path.name}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise V075PublicSourceArtifactCompilationViolation(
            f"cannot create public source artifact: {path.name}"
        ) from error
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_materializer_verification(
    raw: bytes,
) -> source_work.V075SourceOfflineWorkMaterializationVerificationV1:
    value = loads_canonical_json(raw)
    if type(value) is not dict:
        _fail("source-work verification is not one object")
    try:
        result = (
            source_work.V075SourceOfflineWorkMaterializationVerificationV1(
                value["source_recipe_id"],
                value["source_campaign_id"],
                value["campaign_counters_id"],
                value["materialization_id"],
                value["recomputed_materialization_id"],
                value["materialization_bytes_sha256"],
            )
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V075PublicSourceArtifactCompilationViolation(
            "source-work verification cannot be reconstructed"
        ) from error
    if canonical_json_bytes(result.to_document()) != raw:
        _fail("source-work verification differs from its typed reconstruction")
    return result


def compile_public_source_artifacts(
    *,
    repository_root: Path,
    source_output_dir: Path,
    output_dir: Path,
) -> dict[str, str]:
    materialization_raw = _read_regular(
        source_output_dir / INPUT_FILENAMES["materialization"],
        public_source_work.MAX_MATERIALIZATION_BYTES,
    )
    verification_raw = _read_regular(
        source_output_dir / INPUT_FILENAMES["verification"],
        public_source_work.MAX_VERIFICATION_BYTES,
    )
    status_raw = _read_regular(
        source_output_dir / INPUT_FILENAMES["status"],
        public_source_work.MAX_STATUS_BYTES,
    )
    public_bundle = (
        public_source_work.verify_v075_public_source_work_artifacts_v1(
            materialization_raw=materialization_raw,
            verification_raw=verification_raw,
            controller_status_raw=status_raw,
        )
    )

    archive = source_archive.compile_v075_frozen_source_proposal_archive_v1(
        repository_root
    )
    archive_verification = (
        source_archive
        .verify_v075_frozen_source_proposal_archive_independently_v1(
            repository_root=repository_root,
            claimed=archive,
        )
    )
    materialization = (
        source_work.load_v075_source_offline_work_materialization_v1(
            materialization_raw,
            expected_materialization_id=public_bundle.materialization_id,
            expected_source_recipe_id=public_bundle.source_recipe_id,
            expected_source_campaign_id=public_bundle.source_campaign_id,
            expected_campaign_counters_id=public_bundle.campaign_counters_id,
        )
    )
    materialization_verification = _load_materializer_verification(
        verification_raw
    )
    prior = source_prior.bind_v075_source_prior_adapter_v1(
        archive,
        archive_verification,
        materialization,
        materialization_verification,
    )
    prior_verification = (
        source_prior.verify_v075_source_prior_adapter_independently_v1(
            source_archive=archive,
            archive_verification=archive_verification,
            source_work=materialization,
            work_verification=materialization_verification,
            claimed=prior,
        )
    )

    documents: dict[str, bytes] = {
        "archive": archive.canonical_bytes,
        "archive_verification": canonical_json_bytes(
            archive_verification.to_document()
        ),
        "materialization": materialization_raw,
        "materialization_verification": verification_raw,
        "source_replay_status": status_raw,
        "public_source_work_bundle": public_bundle.canonical_bytes,
        "source_prior": prior.canonical_bytes,
        "source_prior_verification": canonical_json_bytes(
            prior_verification.to_document()
        ),
    }
    for role, raw in documents.items():
        _write_exclusive(output_dir / OUTPUT_FILENAMES[role], raw)
    return {
        "source_archive_id": archive.archive_id,
        "source_archive_verification_id": (
            archive_verification.verification_id
        ),
        "source_work_materialization_id": materialization.materialization_id,
        "source_work_verification_id": (
            materialization_verification.verification_id
        ),
        "source_replay_controller_status_id": (
            public_bundle.controller_status_id
        ),
        "public_source_work_bundle_id": public_bundle.bundle_id,
        "source_prior_adapter_id": prior.adapter_id,
        "source_prior_verification_id": prior_verification.verification_id,
    }


def _parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--repository-root", required=True)
    value.add_argument("--source-output-dir", required=True)
    value.add_argument("--output-dir", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repository_root = _real_directory(
        arguments.repository_root,
        "repository root",
    )
    source_output_dir = _real_directory(
        arguments.source_output_dir,
        "source output directory",
    )
    output_candidate = Path(arguments.output_dir)
    if (
        not output_candidate.is_absolute()
        or output_candidate.exists()
        or output_candidate.is_symlink()
        or not output_candidate.parent.is_dir()
        or output_candidate.parent.is_symlink()
        or output_candidate.parent.resolve(strict=True)
        != output_candidate.parent
    ):
        _fail("output directory must be one new absolute path")
    os.mkdir(output_candidate, 0o700)
    identities = compile_public_source_artifacts(
        repository_root=repository_root,
        source_output_dir=source_output_dir,
        output_dir=output_candidate,
    )
    print(canonical_json_bytes(identities).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
