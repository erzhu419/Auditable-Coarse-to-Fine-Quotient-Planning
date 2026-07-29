"""Canonical record for the second anchored V0-072 attempt failure.

The ignored durable journal remains the byte-level provenance source.  This
tracked record freezes its independently replayed closure without turning a
partial attempt into a campaign result, endpoint, certificate, or zero-work
observation.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import v072_registered_campaign_attempt_journal_v1 as journal


SCHEMA = "acfqp.v072_anchored_campaign_attempt_failure.v1"
SCHEMA_VERSION = "1.0.0"
RECORD_DOMAIN = V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN
RECORD_REPOSITORY_PATH = "specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json"

ANCHOR_COMMIT_ID = "63cc0f5f78f64b7845319d1c1a5856212e3b8097"
ANCHOR_TREE_ID = "8c88ef5e2747267a309834d155136c40ba926b61"
ANCHOR_PARENT_COMMIT_ID = "b6a8092eee66026e880e4621aee2b3b0e8b93237"
SOURCE_RECIPE_ID = (
    "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1"
)
MANIFEST_ID = (
    "2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865"
)
FINAL_PREREGISTRATION_ID = (
    "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26"
)
REMOTE_MAIN_ANCHOR_CLAIM_ID = (
    "022ced158d19aea8293a8c8c75e70aa93f93e1913380a76ad11f729f54057076"
)
REMOTE_MAIN_ANCHOR_ID = (
    "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474"
)
REMOTE_MAIN_ANCHOR_ATTESTATION_ID = (
    "408e76d3350bc4fc7a6e2a625d7a42b7949672e98615d51870b156aafc8924c0"
)
AUTHORITY_CHAIN_ID = (
    "10921e80f0f529c972351eb55c2d6912df9cb76ef1045401996606b0ddca2c42"
)
ENVIRONMENT_MANIFEST_ID = (
    "f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da"
)
EXECUTION_PLAN_ID = (
    "32f53516c83c75017284eb3f371a097c6fb216b0b0bed0197aacdb7924b7733d"
)
PREDECESSOR_FAILURE_RECORD_ID = (
    "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f"
)

ATTEMPT_ID = (
    "a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a"
)
ATTEMPT_MANIFEST_OBJECT_ID = (
    "f6dc1c958f5b1d3cefae0f51775730d53a8fa085ffa2f09b2cb129b35cb791e4"
)
LAST_DURABLE_EVENT_ID = (
    "672b4cecf093e970ab3cdca4da7f345c455d97cee3155d7e91a590e221d2321b"
)
TERMINAL_EVENT_ID = (
    "3464c9c36c8aa6e9a1555757597855ef83da59a1ae2c24a178d5a062d030be12"
)
CAUGHT_FAILURE_DIAGNOSTIC_OBJECT_ID = (
    "5685c13c4a5fab7681c862a9cdffe7ba095432ba78050ce8dce89a37bd1a203c"
)
TRACEBACK_SHA256 = (
    "88d80eaa916094c166d15c29549397540611e33d8570cca80827d203172f2a3c"
)
ACTIVE_CONTEXT_ID = (
    "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a"
)
ACTIVE_OCCURRENCE_ID = (
    "e34222b33e065429a0fa188882e178c14458680b07bdc384ce25f5f470a41f06"
)

OCCURRENCE_IDS = (
    "0b73f1b2a48136bd82411b1b5d0dfc010d8169aad4941552013b777ea92dae05",
    "6eeeeea2840fb433a9ecf8aca92fcc0849a7a882bbcc7cc7814b32fd3ad3e850",
    "197343d15d03cb25849cfe80bfa6422bf118735117e44c6141755da5d164212a",
    "7f9ac7bcaf0d1a3b77b2f856d7c41dfb377a8cc9cf085084a10aed83f7601e8e",
    ACTIVE_OCCURRENCE_ID,
    "6bd38ba6f95fcc7d51facb5677049da34348523e378114a5f11e0db19a7ad5a5",
    "059360b09982ad5b75718b612b6df3c95ed4224d6fae2b28cc770a819a69543b",
    "4b33ea324c378e403a1bdbb3f60457fc12780a0b16708d1b5e92df152dd11d05",
    "f968a43bc3e613b9df2936410083d46a52699c1abcd57bfb38405186fef22691",
    "73e235276545a06e5a6c92283ae1f55b3fedd166cb8df68866278a6f8bf133ca",
    "a0bbe4d9d5e9c3c7dd107d4aa5a78579af60992e87792951e983900e91b0a677",
    "6401453c7b9dd3dae04c123d53cd5e8a464e0272f489417d4f3c1b674086b760",
    "bfa1ef7d7e61b687622fe416eaa7b857ad2bcd38fe14f9fcddb3f0efd78fc2ca",
    "4f656210e468833375cae9435d1030379045ea5640aac67e79920efa6b51029d",
    "48403daad430e7298a7d61bd6b46cf438aab898ac702d106b46a7cf09c7bbd11",
)

EVENT_IDS = (
    "0b4b854a51009b861e7dace655617d7be33cdd7970ff42f42a00833d07aca268",
    "f16fff4fc1acc6420e5221279eb1043217d27a0c5b768807bd9ef184bec11b91",
    "6a25822bc1835b0fd8cf4f1890a6003d4d566f74e318befd7da014c3ccad53a6",
    "8403173d4235b3b2e18023c8a19d432e423e37b8bcefe22fb7026da491c68b83",
    "2df3f1d6d88484e9fef6a01bc7da2ff8351f036f1f92dd7d091986b77831941d",
    "29ec5173c4fa6da595cfde43304b26afac44143476decf35f73da9ef2ce28dc6",
    "ba50edb1cfdd2b0e193f62a750e32bac45c39fd880cd48b1b9faf64726e144fa",
    "a13c5e2f7c4cda3e325ff367c1b429d6f24185aaabdd2b2194083f9f6d5c5a71",
    "4da205170746e620c284ac9b342214d61f1e99d13fe4079ad342f8b05032e6e6",
    "c454a6cef9c961528ee58e9406b36a06f075848876723b4fa97ff605a60bfcdd",
    "0f4c91f6f9e8eaedf0e15a0bc53f608f80a5a575c98e227a23394fce91c68e75",
    "d906ff923a52f755201598a220c11215391a0b2dc088e352bc9b66087dd25bd5",
    "3267d0734dc05c13624af3cf36a8f26650d97df7046381e891a73f1014e9d88e",
    "c86bbd245dd55cb2a97e9e42e574325feeb48e7857552e4da911c0a10247647c",
    LAST_DURABLE_EVENT_ID,
    TERMINAL_EVENT_ID,
)

OBJECT_IDS = (
    "0894f7d3439b55d21adc9ffcd21d27f38c53d1c1d0f84c882d844494155d9ab4",
    "0d43bfa4bf8f3a58e93e56916f93477141cc7a73a4451b26c4f7f649dedf0bda",
    "1ea510388bdac6d5694a730c5bf46dd49d9e87a37eb0f14faf6ea12e84b3c841",
    "2590b01ea8d9da86c6b05dac94c91d83de9bfe6d92c13cd02ecc4434160fb286",
    "4ef04559861d76036f064dc979dc87257fea141a052660f5c5fb571124ede376",
    CAUGHT_FAILURE_DIAGNOSTIC_OBJECT_ID,
    "6b4bec00d998e9eaca036d1121095edcbb6e01c4da6e9e2bd6e66fafff032ba4",
    "6f14e49b73a819b4c4bd6fb4e0479762e20067ac1bbec3fc8390d3abf7a768ec",
    "74a754e6274921a3b38630cba1df26e63fef0bfe45709dca03f2cfe4c9ee9aba",
    "74d389ac74349f53e84af4c6eb80f1fa41bcdae2bf850bd9c10e09625787636a",
    "8af356317e7cdd12b081c04e506737746497aee6efddf9292aa986ce1dd10cab",
    "a47818431936d6ab656698513652475fc1816c8d98e9b2a4051f86ebc9afd11f",
    "a50941e4fe05a807ef037d17c3754878da049faf24815386393195c9497046b7",
    "aacdcf85e9d8c94db024c1a319985fea342a8a11ee9b56b4424ba3bd05abeef1",
    "c26b24b4786e6ec6e754574155b77d85ba778a9ed87fd0e4e1eee34fd44ef29e",
    "c8dbd80903fd427674d581fe3b43f6de6c9bc0d2bbfd1dd0b821b4e60b8810aa",
    "e88b56bcce602ce1685ac63d87bef457c80463de6d82b4df3988354158b2adea",
    "e88e43dd3b4d0673cf89455f9afde25b88f5c13feb1f480758df1db40099bcb3",
    "e9b954f7647b71f5a0ee3063daf07983e6950f59594ddc679dbfb650f9b944b7",
    ATTEMPT_MANIFEST_OBJECT_ID,
    "f818748cbd4abdceb10aaa3368a545bbf5b0d87663dd94b8c4eb72c1d63a25e9",
)


class V072AnchoredAttempt2FailureInvariantViolation(ValueError):
    """Raised when attempt-2 historical evidence is missing or altered."""


def _unknown_tail() -> dict[str, Any]:
    return {
        "kind": "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY",
        "must_not_be_interpreted_as_zero": True,
    }


def _payload_v1() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "record_kind": "HISTORICAL_PROTOCOL_FAILURE_NOT_CAMPAIGN_RESULT",
        "attempt_ordinal": 2,
        "predecessor_failure_record_id": PREDECESSOR_FAILURE_RECORD_ID,
        "authority": {
            "anchor_commit_id": ANCHOR_COMMIT_ID,
            "anchor_tree_id": ANCHOR_TREE_ID,
            "anchor_parent_commit_id": ANCHOR_PARENT_COMMIT_ID,
            "source_reconstruction_recipe_id": SOURCE_RECIPE_ID,
            "confirmatory_execution_manifest_id": MANIFEST_ID,
            "final_preregistration_id": FINAL_PREREGISTRATION_ID,
            "remote_main_anchor_claim_id": REMOTE_MAIN_ANCHOR_CLAIM_ID,
            "remote_main_anchor_id": REMOTE_MAIN_ANCHOR_ID,
            "remote_main_anchor_attestation_id": (
                REMOTE_MAIN_ANCHOR_ATTESTATION_ID
            ),
            "authority_chain_id": AUTHORITY_CHAIN_ID,
            "environment_manifest_id": ENVIRONMENT_MANIFEST_ID,
            "execution_plan_id": EXECUTION_PLAN_ID,
        },
        "journal_evidence": {
            "profile_key": journal.PROFILE_KEY,
            "attempt_id": ATTEMPT_ID,
            "attempt_manifest_object_id": ATTEMPT_MANIFEST_OBJECT_ID,
            "journal_repository_path": (
                f"{journal.JOURNAL_ROOT_RELATIVE_PATH}/{ATTEMPT_ID}"
            ),
            "event_ids_in_sequence": list(EVENT_IDS),
            "object_ids_lexicographic": list(OBJECT_IDS),
            "event_count": len(EVENT_IDS),
            "last_durable_event_id": LAST_DURABLE_EVENT_ID,
            "terminal_event_id": TERMINAL_EVENT_ID,
            "caught_failure_diagnostic_object_id": (
                CAUGHT_FAILURE_DIAGNOSTIC_OBJECT_ID
            ),
            "traceback_sha256": TRACEBACK_SHA256,
            "hash_chain_verified": True,
            "closure": "CAUGHT_FAILURE",
            "journal_is_scientific_input": False,
            "journal_work_lane": "PROVENANCE_NOT_ROUTE_WORK",
        },
        "execution": {
            "command_argv": [
                "python3",
                "scripts/run_v072_registered_campaign.py",
            ],
            "output_repository_path": (
                "artifacts/v072_registered_campaign_result_v1.json"
            ),
            "source_reconstruction_observed_complete": True,
            "target_execution_started": True,
            "campaign_computation_completed": False,
            "output_published": False,
            "result_artifact_written": False,
            "result_artifact_id": None,
            "endpoint_evaluated": False,
            "registered_endpoint_outcome": None,
            "all_registered_occurrences_closed": False,
            "registered_occurrence_denominator": 15,
            "completed_occurrence_count": 4,
            "active_occurrence_ordinal_zero_based": 4,
            "active_occurrence_number_one_based": 5,
            "active_occurrence_id": ACTIVE_OCCURRENCE_ID,
            "active_context_id": ACTIVE_CONTEXT_ID,
            "active_arm": "MATCHED_DIRECT_GROUND",
            "last_completed_direct_checkpoint": 16384,
            "unknown_tail_work": _unknown_tail(),
            "durable_prefix_work_may_not_be_reported_as_zero": True,
        },
        "failure": {
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            "runner_phase": "CAMPAIGN_EXECUTION",
            "exception_type": (
                "acfqp.v072_independent_exact_ground_evaluator_v1."
                "V072IndependentExactGroundEvaluationViolation"
            ),
            "exception_message": (
                "fixed-kappa selected policy does not cover the union of "
                "child states reachable under every root realization"
            ),
            "module": (
                "acfqp.v072_independent_exact_ground_evaluator_v1"
            ),
            "function": "_evaluate_registered_exact_ground",
            "cause_classification": (
                "FIXED_KAPPA_POLICY_LIFT_NOT_TOTAL_ON_REACHABLE_CHILD_UNION"
            ),
            "plan_or_infeasibility_credit_allowed": False,
            "scientific_endpoint_read_allowed": False,
        },
        "disposition": {
            "same_authority_chain_attempt_budget": 1,
            "same_authority_chain_attempts_consumed": 1,
            "same_authority_chain_attempts_remaining": 0,
            "same_authority_chain_retry_allowed": False,
            "resume_allowed": False,
            "journal_artifact_reuse_allowed": False,
            "old_target_tape_is_heldout_evidence": False,
            "old_target_tape_regression_use_only": True,
            "repair_requires_total_policy_lift": True,
            "unmapped_reachable_child_semantics": (
                "ABSORBING_POLICY_ABORT_FAILURE"
            ),
            "new_confirmatory_validation_requires_fresh_heldout_identities": (
                True
            ),
            "sample_efficiency_gate_status": "NOT_RUN",
        },
        "claim_boundary": {
            "campaign_result_claimed": False,
            "sample_efficiency_claimed": False,
            "broad_generalization_claimed": False,
            "total_objective_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        },
    }


def anchored_attempt_2_failure_document_v1() -> dict[str, Any]:
    """Return the one canonical attempt-2 failure document."""

    payload = _payload_v1()
    return {**payload, "record_id": content_id(RECORD_DOMAIN, payload)}


def verify_anchored_attempt_2_failure_document_v1(
    document: Mapping[str, Any],
) -> str:
    """Require exact semantic and content equality with the frozen record."""

    try:
        candidate = dict(document)
        record_id = parse_content_id(candidate.pop("record_id"))
        expected = anchored_attempt_2_failure_document_v1()
        expected_id = expected.pop("record_id")
        if candidate != expected:
            raise V072AnchoredAttempt2FailureInvariantViolation(
                "anchored attempt-2 failure semantics changed"
            )
        if (
            record_id != expected_id
            or record_id != content_id(RECORD_DOMAIN, candidate)
        ):
            raise V072AnchoredAttempt2FailureInvariantViolation(
                "anchored attempt-2 failure content identity changed"
            )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(
            error,
            V072AnchoredAttempt2FailureInvariantViolation,
        ):
            raise
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "anchored attempt-2 failure document is malformed"
        ) from error
    return record_id


def load_anchored_attempt_2_failure_record_v1(
    repository_root: Path,
) -> dict[str, Any]:
    """Load canonical tracked bytes and verify the attempt-2 record."""

    root = repository_root.resolve(strict=True)
    path = root / RECORD_REPOSITORY_PATH
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "anchored attempt-2 failure record cannot be loaded"
        ) from error
    if (
        type(document) is not dict
        or raw
        not in (
            canonical_json_bytes(document),
            canonical_json_bytes(document) + b"\n",
        )
    ):
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "anchored attempt-2 failure record is not canonical JSON"
        )
    verify_anchored_attempt_2_failure_document_v1(document)
    return document


def expected_attempt_2_journal_identity_v1(
) -> journal.AttemptJournalIdentityV1:
    """Return the exact external identity required to replay the journal."""

    return journal.AttemptJournalIdentityV1(
        authority_chain_id=AUTHORITY_CHAIN_ID,
        anchor_id=REMOTE_MAIN_ANCHOR_ID,
        anchor_commit_id=ANCHOR_COMMIT_ID,
        anchor_tree_id=ANCHOR_TREE_ID,
        source_reconstruction_recipe_id=SOURCE_RECIPE_ID,
        manifest_id=MANIFEST_ID,
        final_preregistration_id=FINAL_PREREGISTRATION_ID,
        environment_manifest_id=ENVIRONMENT_MANIFEST_ID,
        execution_plan_id=EXECUTION_PLAN_ID,
        occurrence_ids=OCCURRENCE_IDS,
        output_repository_path=(
            "artifacts/v072_registered_campaign_result_v1.json"
        ),
    )


def verify_anchored_attempt_2_journal_evidence_v1(
    repository_root: Path,
) -> journal.AttemptJournalVerificationV1:
    """Replay the ignored journal against the tracked exact identity."""

    try:
        root = repository_root.resolve(strict=True)
        attempt_directory = (
            root / journal.JOURNAL_ROOT_RELATIVE_PATH / ATTEMPT_ID
        ).resolve(strict=True)
        verification = journal.verify_attempt_journal_v1(
            attempt_directory,
            expected_identity=expected_attempt_2_journal_identity_v1(),
        )
    except (OSError, journal.V072AttemptJournalInvariantViolation) as error:
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "anchored attempt-2 journal replay failed"
        ) from error
    if (
        verification.attempt_id != ATTEMPT_ID
        or verification.event_ids != EVENT_IDS
        or verification.object_ids != OBJECT_IDS
        or verification.completed_occurrence_count != 4
        or verification.closure
        is not journal.AttemptJournalClosureV1.CAUGHT_FAILURE
        or verification.valid_hash_chain is not True
        or verification.resume_allowed is not False
        or verification.artifact_reuse_allowed is not False
        or verification.scientific_input is not False
        or verification.lossless_execution_transport_claimed is not False
    ):
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "anchored attempt-2 journal closure differs from tracked evidence"
        )
    return verification


def verify_anchored_attempt_2_git_authority_v1(
    repository_root: Path,
) -> tuple[str, str, str]:
    """Replay the anchor commit's frozen identity triple without network I/O."""

    root = repository_root.resolve(strict=True)
    try:
        ancestry = subprocess.run(
            (
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                ANCHOR_COMMIT_ID,
                "HEAD",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        if ancestry.returncode != 0:
            raise V072AnchoredAttempt2FailureInvariantViolation(
                "attempt-2 anchor commit is not current-history provenance"
            )
        tree = subprocess.run(
            (
                "git",
                "-C",
                str(root),
                "rev-parse",
                f"{ANCHOR_COMMIT_ID}^{{tree}}",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        parent = subprocess.run(
            (
                "git",
                "-C",
                str(root),
                "rev-parse",
                f"{ANCHOR_COMMIT_ID}^",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        if (
            tree.returncode != 0
            or parent.returncode != 0
            or tree.stdout.decode("ascii", errors="strict").strip()
            != ANCHOR_TREE_ID
            or parent.stdout.decode("ascii", errors="strict").strip()
            != ANCHOR_PARENT_COMMIT_ID
        ):
            raise V072AnchoredAttempt2FailureInvariantViolation(
                "attempt-2 Git anchor objects changed"
            )
        documents: list[dict[str, Any]] = []
        for relative in (
            "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json",
            "specs/V072_CONFIRMATORY_EXECUTION_MANIFEST.json",
            "specs/V072_FINAL_PREREGISTRATION.json",
        ):
            completed = subprocess.run(
                (
                    "git",
                    "-C",
                    str(root),
                    "show",
                    f"{ANCHOR_COMMIT_ID}:{relative}",
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            if completed.returncode != 0:
                raise V072AnchoredAttempt2FailureInvariantViolation(
                    "attempt-2 anchor lacks its frozen identity chain"
                )
            parsed = json.loads(
                completed.stdout.decode("utf-8", errors="strict")
            )
            if type(parsed) is not dict:
                raise V072AnchoredAttempt2FailureInvariantViolation(
                    "attempt-2 frozen identity document is malformed"
                )
            documents.append(parsed)
    except (
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "attempt-2 Git provenance replay failed"
        ) from error
    recipe, manifest, preregistration = documents
    identities = (
        recipe.get("recipe_id"),
        manifest.get("manifest_id"),
        preregistration.get("preregistration_id"),
    )
    if identities != (
        SOURCE_RECIPE_ID,
        MANIFEST_ID,
        FINAL_PREREGISTRATION_ID,
    ):
        raise V072AnchoredAttempt2FailureInvariantViolation(
            "attempt-2 frozen Git identities differ from the failure record"
        )
    return identities


__all__ = [
    "ANCHOR_COMMIT_ID",
    "ATTEMPT_ID",
    "EVENT_IDS",
    "FINAL_PREREGISTRATION_ID",
    "MANIFEST_ID",
    "OBJECT_IDS",
    "RECORD_REPOSITORY_PATH",
    "REMOTE_MAIN_ANCHOR_ID",
    "SCHEMA",
    "SCHEMA_VERSION",
    "SOURCE_RECIPE_ID",
    "TERMINAL_EVENT_ID",
    "V072AnchoredAttempt2FailureInvariantViolation",
    "anchored_attempt_2_failure_document_v1",
    "expected_attempt_2_journal_identity_v1",
    "load_anchored_attempt_2_failure_record_v1",
    "verify_anchored_attempt_2_failure_document_v1",
    "verify_anchored_attempt_2_git_authority_v1",
    "verify_anchored_attempt_2_journal_evidence_v1",
]
