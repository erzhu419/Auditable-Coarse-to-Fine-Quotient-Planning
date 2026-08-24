from pathlib import Path

from acfqp import construction_k7_open_world_campaign_failure_verifier_v181r2 as verifier


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
FAILURE = BASE / "v181r2_open_world_campaign_failure.json"
PROGRESS = BASE / "v181r2_open_world_progress"
OUTPUT = BASE / "v181r2_open_world_campaign_failure_verification.json"


def main() -> None:
    checkpoint_raws = tuple(
        path.read_bytes() for path in sorted(PROGRESS.glob("checkpoint-*.json"))
    )
    value = verifier.freeze_open_world_campaign_failure_verification_v181r2(
        FAILURE.read_bytes(),
        checkpoint_raws,
    )
    if OUTPUT.exists() and OUTPUT.read_bytes().rstrip(b"\n") != value.canonical_bytes:
        raise RuntimeError("existing V181r2 failure verification changed")
    OUTPUT.write_bytes(value.canonical_bytes)


if __name__ == "__main__":
    main()
