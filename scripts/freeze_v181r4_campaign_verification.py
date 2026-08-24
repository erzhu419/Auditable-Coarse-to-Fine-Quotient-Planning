from pathlib import Path

from acfqp import construction_k7_open_world_campaign_independent_verifier_v181r4 as verifier


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
CAMPAIGN = BASE / "v181r4_open_world_campaign.json"
PROGRESS = BASE / "v181r4_open_world_progress"
OUTPUT = BASE / "v181r4_open_world_campaign_verification.json"


def main() -> None:
    checkpoint_raws = tuple(
        path.read_bytes() for path in sorted(PROGRESS.glob("checkpoint-*.json"))
    )
    value = verifier.freeze_open_world_campaign_verification_v181r4(
        CAMPAIGN.read_bytes(),
        checkpoint_raws,
    )
    with OUTPUT.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r4 verification short write")


if __name__ == "__main__":
    main()
