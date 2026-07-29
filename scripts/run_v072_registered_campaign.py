#!/usr/bin/env python3
"""Run the exact preregistered V0-072 campaign from repository authority."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer


DEFAULT_OUTPUT_RELATIVE_PATH = Path(
    "artifacts/v072_registered_campaign_result_v1.json"
)


def _repository_root_v1() -> Path:
    root = Path(__file__).resolve().parents[1]
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise SystemExit("repository root is not one absolute real directory")
    return root


def _output_path_v1(root: Path, supplied: str | None) -> Path:
    artifacts = root / "artifacts"
    if (
        not artifacts.is_dir()
        or artifacts.is_symlink()
        or artifacts.resolve(strict=True) != artifacts
    ):
        raise SystemExit("artifacts root is not one real repository directory")

    requested = (
        root / DEFAULT_OUTPUT_RELATIVE_PATH
        if supplied is None
        else Path(supplied)
    )
    if not requested.is_absolute():
        requested = root / requested
    candidate = Path(os.path.abspath(os.fspath(requested)))
    if candidate == artifacts or artifacts not in candidate.parents:
        raise SystemExit("output must be a new file under repository artifacts/")

    current = artifacts
    for part in candidate.relative_to(artifacts).parts[:-1]:
        current = current / part
        if (
            not current.is_dir()
            or current.is_symlink()
            or current.resolve(strict=True) != current
        ):
            raise SystemExit(
                "output parent must already be one real directory under "
                "artifacts/"
            )
    if candidate.exists() or candidate.is_symlink():
        raise SystemExit("refusing to overwrite or follow the output path")
    return candidate


def _atomic_write_new_v1(path: Path, document: Any) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("refusing to overwrite or follow the output path")
    data = canonical_json_bytes(document)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(
                temporary,
                path,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise SystemExit(
                "refusing to overwrite or follow the output path"
            ) from error
        directory_descriptor = os.open(
            path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _authority_chain_v1(root: Path) -> tuple[Any, tuple[str, ...]]:
    final = final_authority.finalize_v072_final_preregistration_v1(root)
    derived_claim = (
        final_authority.derive_v072_remote_main_anchor_claim_v1(root)
    )
    anchor = final_authority.mint_v072_remote_main_anchor_v1(
        repository_root=root
    )
    if anchor.claim != derived_claim:
        raise SystemExit(
            "independently minted anchor changed the derived production claim"
        )
    chain = consumer.RegisteredCampaignAuthorityChainV1(
        manifest=final.manifest,
        final_preregistration=final,
        remote_main_anchor=anchor,
        remote_main_anchor_attestation=(
            anchor.independent_semantic_attestation
        ),
        repository_root=os.fspath(root),
    )
    verified_ids = consumer.verify_registered_campaign_authority_chain_v1(
        chain
    )
    return chain, tuple(verified_ids)


def _remote_main_authority_v1(root: Path) -> Any:
    """Verify only the committed remote-main authority triple.

    This deliberately does not finalize a manifest or construct the campaign
    authority chain, because finalization replays the paid source campaign.
    """

    derived_claim = (
        final_authority.derive_v072_remote_main_anchor_claim_v1(root)
    )
    anchor = final_authority.mint_v072_remote_main_anchor_v1(
        repository_root=root
    )
    if anchor.claim != derived_claim:
        raise SystemExit(
            "independently minted anchor changed the derived production claim"
        )
    return anchor


def _authority_report_v1(anchor: Any) -> dict[str, Any]:
    claim = anchor.claim
    attestation = anchor.independent_semantic_attestation
    return {
        "schema": "acfqp.v072_registered_campaign_authority_check.v1",
        "schema_version": "1.0.0",
        "source_reconstruction_recipe_id": (
            claim.source_reconstruction_recipe_id
        ),
        "manifest_id": claim.manifest_id,
        "final_preregistration_id": claim.final_preregistration_id,
        "remote_main_anchor_claim_id": claim.claim_id,
        "remote_main_anchor_id": anchor.anchor_id,
        "remote_main_anchor_attestation_id": (
            attestation.verification_id
        ),
        "remote_main_authority_verified": True,
        "authority_chain_constructed": False,
        "campaign_executed": False,
        "source_reconstruction_executed": False,
        "target_execution_started": False,
    }


def _print_canonical_v1(document: Any) -> None:
    print(canonical_json_bytes(document).decode("utf-8", errors="strict"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "run the repository-derived preregistered V0-072 campaign"
        )
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help=(
            "new result path under artifacts/ "
            f"(default: {DEFAULT_OUTPUT_RELATIVE_PATH.as_posix()})"
        ),
    )
    parser.add_argument(
        "--check-authority-only",
        action="store_true",
        help=(
            "verify the committed remote-main authority triple without "
            "source reconstruction, chain construction, or target execution"
        ),
    )
    args = parser.parse_args(argv)
    if args.check_authority_only and args.output is not None:
        parser.error("--output is not used with --check-authority-only")

    root = _repository_root_v1()
    output_path = (
        None
        if args.check_authority_only
        else _output_path_v1(root, args.output)
    )
    if args.check_authority_only:
        anchor = _remote_main_authority_v1(root)
        _print_canonical_v1(_authority_report_v1(anchor))
        return 0

    authority_chain, _ = _authority_chain_v1(root)
    execution_result = consumer.run_registered_v072_campaign_v1(
        authority_chain=authority_chain
    )
    assert output_path is not None
    _atomic_write_new_v1(output_path, execution_result.to_document())
    _print_canonical_v1(
        {
            "schema": "acfqp.v072_registered_campaign_cli_result.v1",
            "schema_version": "1.0.0",
            "authority_chain_id": authority_chain.chain_id,
            "execution_result_id": execution_result.execution_result_id,
            "output_path": output_path.relative_to(root).as_posix(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
