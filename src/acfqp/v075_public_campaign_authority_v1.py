"""Law-free public authority for a production V0-075 campaign.

This module contains only public structural context and typed identity
bindings.  It deliberately contains no production transition law, law ID,
environment manifest, reveal salt, or observer capability.

Production environments are represented before closure by a salted opaque
commitment.  The commitment helper consumes secret material in memory and
returns an object whose document contains neither the material nor the salt.
The corresponding reveal verifier likewise returns only a verification
attestation.  A production caller must obtain secret material outside the
repository and must never serialize it into a public campaign artifact.

RSA claims in this module establish provenance relative to a supplied signer
registry; they do not make that registry a trust root.  The namespace produced
here is therefore always a nonauthorizing candidate.  A later independent
final-preregistration/remote-main verifier must reconstruct the registry ID
and exact key bytes from tracked Git objects before observer access can open.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import hmac
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_law_free_public_campaign_authority_v1"
TARGET_FAMILY_GENERATION_KEY = "v075_production_family_generation_1"

HORIZON = 2
RANK_CAP = 6
ROOT_RANKS = (1, 1, 2, 0, 0, 0, 0)
RISK_TOLERANCE = Fraction(1, 20)
REWARD_CEILING = Fraction(3, 64)
NORMALIZED_REGRET_TOLERANCE = Fraction(1, 20)
MINIMUM_SECRET_SALT_BYTES = 32
INDEPENDENT_FINAL_AUTHORITY_VERIFIER_IMPLEMENTED = False
PRODUCTION_OBSERVER_OPEN_ALLOWED = False

ARM_ORDER = (
    "SOURCE_CONSENSUS_PRIOR",
    "NO_PRIOR",
    "WRONG_CONSENSUS_PRIOR",
    "OOD_ABSTENTION",
    "MATCHED_DIRECT_GROUND",
)

DOMAIN_TAGS = {
    "family_seed": "acfqp:v075-public-family-generation-seed:v1",
    "replicate_context": "acfqp:v075-public-replicate-context:v1",
    "family_generation": "acfqp:v075-public-family-generation:v1",
    "rsa_public_key": "acfqp:v075-rsa-public-verification-key:v1",
    "signer_registry": "acfqp:v075-trusted-signer-registry:v1",
    "signed_external_authority": (
        "acfqp:v075-signed-external-authority-claim:v1"
    ),
    "opaque_environment_commitment": (
        "acfqp:v075-salted-opaque-environment-commitment:v1"
    ),
    "environment_reveal_verification": (
        "acfqp:v075-private-environment-reveal-verification:v1"
    ),
    "target_tape_namespace": (
        "acfqp:v075-law-free-target-tape-namespace:v1"
    ),
}

_SECRET_COMMITMENT_DOMAIN = (
    b"acfqp:v075-private-hidden-environment-reveal:v1"
)

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 public authority domains must be unique")


class V075PublicCampaignAuthorityInvariantViolation(ValueError):
    """A law-free V0-075 public authority invariant failed."""


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PublicCampaignAuthorityInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PublicCampaignAuthorityInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V075PublicCampaignAuthorityInvariantViolation(
            "registered arithmetic must use exact Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


# Frozen offline extraction from the two tracked V0-072 failure records.  The
# public runtime never reads those records: doing so would reintroduce an old
# target-data channel into the planner dependency graph.
FROZEN_V072_FAILURE_RECORD_CONTENT_IDS = (
    "022ced158d19aea8293a8c8c75e70aa93f93e1913380a76ad11f729f54057076",
    "0894f7d3439b55d21adc9ffcd21d27f38c53d1c1d0f84c882d844494155d9ab4",
    "0b4b854a51009b861e7dace655617d7be33cdd7970ff42f42a00833d07aca268",
    "0d43bfa4bf8f3a58e93e56916f93477141cc7a73a4451b26c4f7f649dedf0bda",
    "0f4c91f6f9e8eaedf0e15a0bc53f608f80a5a575c98e227a23394fce91c68e75",
    "10921e80f0f529c972351eb55c2d6912df9cb76ef1045401996606b0ddca2c42",
    "157f6c512b912d4e100e76a30fdb4ae43c051cef6ac073778a303dd523e6d88e",
    "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474",
    "1ea510388bdac6d5694a730c5bf46dd49d9e87a37eb0f14faf6ea12e84b3c841",
    "2590b01ea8d9da86c6b05dac94c91d83de9bfe6d92c13cd02ecc4434160fb286",
    "29ec5173c4fa6da595cfde43304b26afac44143476decf35f73da9ef2ce28dc6",
    "2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865",
    "2df3f1d6d88484e9fef6a01bc7da2ff8351f036f1f92dd7d091986b77831941d",
    "3267d0734dc05c13624af3cf36a8f26650d97df7046381e891a73f1014e9d88e",
    "32f53516c83c75017284eb3f371a097c6fb216b0b0bed0197aacdb7924b7733d",
    "3464c9c36c8aa6e9a1555757597855ef83da59a1ae2c24a178d5a062d030be12",
    "408e76d3350bc4fc7a6e2a625d7a42b7949672e98615d51870b156aafc8924c0",
    "41c9aa9509717915777ba91a7d6015071ddb1f55187505f8ab376be2fd122d4f",
    "4316c8a441db0eee80847c9060b25d9eae454d14895c4e137e1e9c092ff0fe6f",
    "4da205170746e620c284ac9b342214d61f1e99d13fe4079ad342f8b05032e6e6",
    "4ef04559861d76036f064dc979dc87257fea141a052660f5c5fb571124ede376",
    "5685c13c4a5fab7681c862a9cdffe7ba095432ba78050ce8dce89a37bd1a203c",
    "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a",
    "672b4cecf093e970ab3cdca4da7f345c455d97cee3155d7e91a590e221d2321b",
    "6a25822bc1835b0fd8cf4f1890a6003d4d566f74e318befd7da014c3ccad53a6",
    "6b4bec00d998e9eaca036d1121095edcbb6e01c4da6e9e2bd6e66fafff032ba4",
    "6f14e49b73a819b4c4bd6fb4e0479762e20067ac1bbec3fc8390d3abf7a768ec",
    "74a754e6274921a3b38630cba1df26e63fef0bfe45709dca03f2cfe4c9ee9aba",
    "74d389ac74349f53e84af4c6eb80f1fa41bcdae2bf850bd9c10e09625787636a",
    "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1",
    "8403173d4235b3b2e18023c8a19d432e423e37b8bcefe22fb7026da491c68b83",
    "88d80eaa916094c166d15c29549397540611e33d8570cca80827d203172f2a3c",
    "8af356317e7cdd12b081c04e506737746497aee6efddf9292aa986ce1dd10cab",
    "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26",
    "a13c5e2f7c4cda3e325ff367c1b429d6f24185aaabdd2b2194083f9f6d5c5a71",
    "a47818431936d6ab656698513652475fc1816c8d98e9b2a4051f86ebc9afd11f",
    "a50941e4fe05a807ef037d17c3754878da049faf24815386393195c9497046b7",
    "a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a",
    "aacdcf85e9d8c94db024c1a319985fea342a8a11ee9b56b4424ba3bd05abeef1",
    "acbec3e259e9df0e5b56c172ae2261f6d072f29b3a669b1eaafbcbdcae28b1c6",
    "b6a543a0e30214338214bf025bbf543994f6afc3251608f522d11f5c20e236f2",
    "ba50edb1cfdd2b0e193f62a750e32bac45c39fd880cd48b1b9faf64726e144fa",
    "c26b24b4786e6ec6e754574155b77d85ba778a9ed87fd0e4e1eee34fd44ef29e",
    "c454a6cef9c961528ee58e9406b36a06f075848876723b4fa97ff605a60bfcdd",
    "c86bbd245dd55cb2a97e9e42e574325feeb48e7857552e4da911c0a10247647c",
    "c8dbd80903fd427674d581fe3b43f6de6c9bc0d2bbfd1dd0b821b4e60b8810aa",
    "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f",
    "cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e",
    "d836f0b0c7f3b302541ce81dc5372c077d336add5f28a973ebd6ae611ccbd8b9",
    "d906ff923a52f755201598a220c11215391a0b2dc088e352bc9b66087dd25bd5",
    "e34222b33e065429a0fa188882e178c14458680b07bdc384ce25f5f470a41f06",
    "e88b56bcce602ce1685ac63d87bef457c80463de6d82b4df3988354158b2adea",
    "e88e43dd3b4d0673cf89455f9afde25b88f5c13feb1f480758df1db40099bcb3",
    "e9b954f7647b71f5a0ee3063daf07983e6950f59594ddc679dbfb650f9b944b7",
    "f16fff4fc1acc6420e5221279eb1043217d27a0c5b768807bd9ef184bec11b91",
    "f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da",
    "f6dc1c958f5b1d3cefae0f51775730d53a8fa085ffa2f09b2cb129b35cb791e4",
    "f818748cbd4abdceb10aaa3368a545bbf5b0d87663dd94b8c4eb72c1d63a25e9",
)
FROZEN_V072_FAILURE_RECORD_CONTENT_ID_COUNT = 58
FROZEN_V072_ATTEMPT_1_CONTENT_ID_COUNT = 8
FROZEN_V072_ATTEMPT_2_CONTENT_ID_COUNT = 52
FROZEN_V072_ATTEMPT_CONTENT_ID_OVERLAP_COUNT = 2
FROZEN_V072_ATTEMPT_1_CONTENT_ID_MERKLE_ROOT = (
    "f11932e6b53e9e5249c56b77758a66c9fe15ef4263a3bd634552f107cb137160"
)
FROZEN_V072_ATTEMPT_2_CONTENT_ID_MERKLE_ROOT = (
    "ff7cb8247029afbdefc26f41edff9e4c855be2da2bad1e405e115d96002306b0"
)
FROZEN_V072_FAILURE_RECORD_CONTENT_ID_MERKLE_ROOT = (
    "4dac0585a2f8231336f1a05e4003da2223f7ee518d1b7f9c96bbdf0007ceb47d"
)


def _failure_record_id_merkle_root(ids: tuple[str, ...]) -> str:
    level = [
        hashlib.sha256(
            b"acfqp:v075-v072-failure-record-id-leaf:v1"
            + b"\x00"
            + bytes.fromhex(value)
        ).digest()
        for value in ids
    ]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(
                b"acfqp:v075-v072-failure-record-id-node:v1"
                + b"\x00"
                + level[index]
                + level[index + 1]
            ).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


if (
    len(FROZEN_V072_FAILURE_RECORD_CONTENT_IDS)
    != FROZEN_V072_FAILURE_RECORD_CONTENT_ID_COUNT
    or FROZEN_V072_FAILURE_RECORD_CONTENT_IDS
    != tuple(sorted(set(FROZEN_V072_FAILURE_RECORD_CONTENT_IDS)))
    or _failure_record_id_merkle_root(
        FROZEN_V072_FAILURE_RECORD_CONTENT_IDS
    )
    != FROZEN_V072_FAILURE_RECORD_CONTENT_ID_MERKLE_ROOT
):
    raise RuntimeError("frozen V0-072 failure-record denylist drifted")


# The denylist is public provenance, not hidden environment material.  A typed
# V0-075 external target role may not launder any frozen record identity.
FORBIDDEN_HISTORICAL_TARGET_IDS = frozenset(
    set(FROZEN_V072_FAILURE_RECORD_CONTENT_IDS)
    | {
        "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a",
        "48a6f36af9ef5ff1ba9920d783d2435cedd9458c8383f48ccf40412ff55f0dda",
        "52363b3d6e6508e6734418103be98da18cd7aafe6657d24de16c2547c630ba7a",
        "434f67074a8be498fd8cc532fe780f4227f6f8233bc90a62fab6e8cb595a5f71",
        "801683343ef1973337e534f2d36ac6c8493717d240ef05677abd3a2abb72559c",
        "b0803f306f3d5ac79abd6e87fc713caedcceae3411f3172f88d103cb7b540347",
        "f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da",
        "7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2",
        "8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29",
        "e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4",
        "0f8061ac58630cced8f01bce01191ab0d02aff5cf64b4cc106f579ad53d02312",
        "1f240bb0305012a9144b4039d9f2f9b13a0be18b23c0cc7c70dc2909f09ccc29",
        "a5775190ea336702a7f4e1f06bdd93ec0bd0609f03f69ad7a72c2262e6645976",
        "ad7dca2b9db96d98d0c8bd6608315264995d3dcb0b6457a4b2b5d073db494ab0",
        "571d4cb2a7b2b55fc85012b2b417f397b57226df7ae4b00c47d0bb5f35639441",
        "e8cb7a070c7d6bbdb93683367a8026f422a8ef397877b87d07a3c6c549820cde",
        "f0d8db6165c3d0a125945b43b4b0d8e221b13ea7870021e96f18b91e218ed00e",
        "495927b2c72c847086008b2b2c6e8f65ea4a2b5a45ce409c8c7ec3d4be915500",
        "acbec3e259e9df0e5b56c172ae2261f6d072f29b3a669b1eaafbcbdcae28b1c6",
        "b6a543a0e30214338214bf025bbf543994f6afc3251608f522d11f5c20e236f2",
        "41c9aa9509717915777ba91a7d6015071ddb1f55187505f8ab376be2fd122d4f",
        "4316c8a441db0eee80847c9060b25d9eae454d14895c4e137e1e9c092ff0fe6f",
        "157f6c512b912d4e100e76a30fdb4ae43c051cef6ac073778a303dd523e6d88e",
        "d836f0b0c7f3b302541ce81dc5372c077d336add5f28a973ebd6ae611ccbd8b9",
        "2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865",
        "966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26",
        "022ced158d19aea8293a8c8c75e70aa93f93e1913380a76ad11f729f54057076",
        "408e76d3350bc4fc7a6e2a625d7a42b7949672e98615d51870b156aafc8924c0",
        "1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474",
        "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1",
        "10921e80f0f529c972351eb55c2d6912df9cb76ef1045401996606b0ddca2c42",
        "32f53516c83c75017284eb3f371a097c6fb216b0b0bed0197aacdb7924b7733d",
        "e34222b33e065429a0fa188882e178c14458680b07bdc384ce25f5f470a41f06",
        "a925bb7104727ccce81b4da5361fab9610638f5e6a35e46177faa3dfced4174a",
        "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f",
        "cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e",
        "16b383ff8fd9ce3ec52737c9e68c079f2e908be4f9abd07ac4c4b41c16a9c7be",
        "f1892c934776d5601146b4b1fddbdcebb9dd4bb146f164ad3538c704633a6c34",
    }
)


def _fresh_external_id(value: Any, field: str) -> str:
    result = _cid(value, field)
    if result in FORBIDDEN_HISTORICAL_TARGET_IDS:
        raise V075PublicCampaignAuthorityInvariantViolation(
            f"{field} reuses a historical or source-only V0-072 identity"
        )
    return result


def _canonical_edges(
    edges: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({tuple(sorted(edge)) for edge in edges}))


K7_TOPOLOGY = GraphTopologyV1(7, tuple(combinations(range(7), 2)))
W7_TOPOLOGY = GraphTopologyV1(
    7,
    _canonical_edges(
        tuple((index, (index + 1) % 6) for index in range(6))
        + tuple((6, index) for index in range(6))
    ),
)
K7_MINUS_TWO_TOPOLOGY = GraphTopologyV1(
    7,
    tuple(
        edge
        for edge in combinations(range(7), 2)
        if edge not in {(4, 6), (5, 6)}
    ),
)

_CONTEXT_SPECS = (
    (
        "heldout_graph_k7_production_replication_v075_1",
        K7_TOPOLOGY,
        96,
    ),
    (
        "heldout_graph_w7_production_replication_v075_1",
        W7_TOPOLOGY,
        48,
    ),
    (
        "heldout_graph_k7_minus_two_production_replication_v075_1",
        K7_MINUS_TWO_TOPOLOGY,
        96,
    ),
)


def _family_seed_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_public_family_generation_seed.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "generation_key": TARGET_FAMILY_GENERATION_KEY,
        "public_structure_only": True,
        "production_law_serialized": False,
        "target_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class V075PublicReplicateContextV1:
    replicate_ordinal: int

    def __post_init__(self) -> None:
        if (
            type(self.replicate_ordinal) is not int
            or self.replicate_ordinal not in range(len(_CONTEXT_SPECS))
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "public replicate ordinal is invalid"
            )

    @property
    def context_key(self) -> str:
        return _CONTEXT_SPECS[self.replicate_ordinal][0]

    @property
    def topology(self) -> GraphTopologyV1:
        return _CONTEXT_SPECS[self.replicate_ordinal][1]

    @property
    def maximum_physical_rows_per_confidence_epoch(self) -> int:
        return _CONTEXT_SPECS[self.replicate_ordinal][2]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_public_replicate_context.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "generation_seed_id": _hash(
                "family_seed",
                _family_seed_payload(),
            ),
            "replicate_ordinal": self.replicate_ordinal,
            "context_key": self.context_key,
            "base_topology": self.topology.to_document(),
            "base_topology_id": self.topology.topology_id,
            "root_ranks": list(ROOT_RANKS),
            "horizon": HORIZON,
            "risk_tolerance": _fdoc(RISK_TOLERANCE),
            "rank_cap": RANK_CAP,
            "reward_ceiling": _fdoc(REWARD_CEILING),
            "normalized_regret_tolerance": _fdoc(
                NORMALIZED_REGRET_TOLERANCE
            ),
            "maximum_physical_rows_per_confidence_epoch": (
                self.maximum_physical_rows_per_confidence_epoch
            ),
            "public_structure_only": True,
            "production_law_serialized": False,
            "target_execution_allowed": False,
        }

    @property
    def context_id(self) -> str:
        return _hash("replicate_context", self._payload())

    @property
    def root_ranks(self) -> tuple[int, ...]:
        return ROOT_RANKS

    @property
    def horizon(self) -> int:
        return HORIZON

    @property
    def rank_cap(self) -> int:
        return RANK_CAP

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class V075PublicFamilyGenerationV1:
    generation_key: str = TARGET_FAMILY_GENERATION_KEY

    def __post_init__(self) -> None:
        if self.generation_key != TARGET_FAMILY_GENERATION_KEY:
            raise V075PublicCampaignAuthorityInvariantViolation(
                "public family generation changed"
            )

    @property
    def generation_seed_id(self) -> str:
        return _hash("family_seed", _family_seed_payload())

    @property
    def replicate_contexts(self) -> tuple[V075PublicReplicateContextV1, ...]:
        return tuple(
            V075PublicReplicateContextV1(index)
            for index in range(len(_CONTEXT_SPECS))
        )

    def _payload(self) -> dict[str, Any]:
        return {
            **_family_seed_payload(),
            "schema": "acfqp.v075_public_family_generation.v1",
            "generation_seed_id": self.generation_seed_id,
            "replicate_contexts": [
                context.to_document()
                for context in self.replicate_contexts
            ],
            "replicate_context_ids": [
                context.context_id
                for context in self.replicate_contexts
            ],
            "public_structure_only": True,
            "production_law_serialized": False,
        }

    @property
    def generation_id(self) -> str:
        return _hash("family_generation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "generation_id": self.generation_id}


def freeze_v075_public_family_generation_v1(
) -> V075PublicFamilyGenerationV1:
    return V075PublicFamilyGenerationV1()


def registered_public_context_v1(
    value: Any,
) -> V075PublicReplicateContextV1:
    contexts = freeze_v075_public_family_generation_v1().replicate_contexts
    if (
        type(value) is not V075PublicReplicateContextV1
        or value not in contexts
    ):
        raise V075PublicCampaignAuthorityInvariantViolation(
            "value is not one exact registered public V0-075 context"
        )
    return value


class V075ExternalAuthorityRoleV1(str, Enum):
    REMOTE_MAIN_ANCHOR = "REMOTE_MAIN_ANCHOR"
    FINAL_PREREGISTRATION = "FINAL_PREREGISTRATION"
    OBSERVER_PROFILE = "OBSERVER_PROFILE"


@dataclass(frozen=True, slots=True)
class V075RSAPublicVerificationKeyV1:
    key_role: str
    modulus: int
    public_exponent: int = 65_537

    def __post_init__(self) -> None:
        if (
            self.key_role
            not in {"CAMPAIGN_AUTHORITY", "OBSERVER_EVIDENCE"}
            or type(self.modulus) is not int
            or self.modulus.bit_length() < 2_048
            or type(self.public_exponent) is not int
            or self.public_exponent < 3
            or self.public_exponent % 2 == 0
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "RSA public verification key is malformed or undersized"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_rsa_public_verification_key.v1",
            "schema_version": SCHEMA_VERSION,
            "key_role": self.key_role,
            "algorithm": "RSASSA-PKCS1-v1_5-SHA256",
            "modulus_hex": format(self.modulus, "x"),
            "public_exponent": self.public_exponent,
            "minimum_modulus_bits": 2_048,
            "private_key_serialized": False,
        }

    @property
    def key_id(self) -> str:
        return _hash("rsa_public_key", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "key_id": self.key_id}


@dataclass(frozen=True, slots=True)
class V075TrustedSignerRegistryV1:
    campaign_authority_key: V075RSAPublicVerificationKeyV1
    observer_evidence_key: V075RSAPublicVerificationKeyV1

    def __post_init__(self) -> None:
        if (
            type(self.campaign_authority_key)
            is not V075RSAPublicVerificationKeyV1
            or self.campaign_authority_key.key_role
            != "CAMPAIGN_AUTHORITY"
            or type(self.observer_evidence_key)
            is not V075RSAPublicVerificationKeyV1
            or self.observer_evidence_key.key_role
            != "OBSERVER_EVIDENCE"
            or self.campaign_authority_key.key_id
            == self.observer_evidence_key.key_id
            or (
                self.campaign_authority_key.modulus,
                self.campaign_authority_key.public_exponent,
            )
            == (
                self.observer_evidence_key.modulus,
                self.observer_evidence_key.public_exponent,
            )
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "trusted signer registry roles are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_trusted_signer_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_authority_key_id": (
                self.campaign_authority_key.key_id
            ),
            "observer_evidence_key_id": self.observer_evidence_key.key_id,
            "private_keys_serialized": False,
            "registry_precedes_final_preregistration": True,
            "final_preregistration_must_bind_registry_id": True,
            "registry_contains_final_preregistration_id": False,
        }

    @property
    def registry_id(self) -> str:
        return _hash("signer_registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_authority_key": (
                self.campaign_authority_key.to_document()
            ),
            "observer_evidence_key": (
                self.observer_evidence_key.to_document()
            ),
            "registry_id": self.registry_id,
        }


_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


def verify_rsa_pkcs1_v1_5_sha256_signature_v1(
    *,
    public_key: V075RSAPublicVerificationKeyV1,
    message: bytes,
    signature_hex: str,
) -> bool:
    """Verify one deterministic RSA/SHA-256 signature using stdlib only."""

    if (
        type(public_key) is not V075RSAPublicVerificationKeyV1
        or type(message) is not bytes
        or type(signature_hex) is not str
        or not signature_hex
        or len(signature_hex) % 2
    ):
        return False
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    width = (public_key.modulus.bit_length() + 7) // 8
    if len(signature) != width:
        return False
    signature_integer = int.from_bytes(signature, "big")
    if signature_integer >= public_key.modulus:
        return False
    encoded = pow(
        signature_integer,
        public_key.public_exponent,
        public_key.modulus,
    ).to_bytes(width, "big")
    digest_info = (
        _SHA256_DIGEST_INFO_PREFIX
        + hashlib.sha256(message).digest()
    )
    padding_size = width - len(digest_info) - 3
    if padding_size < 8:
        return False
    expected = (
        b"\x00\x01"
        + b"\xff" * padding_size
        + b"\x00"
        + digest_info
    )
    return hmac.compare_digest(encoded, expected)


def external_authority_claim_signing_bytes_v1(
    *,
    signer_registry: V075TrustedSignerRegistryV1,
    role: V075ExternalAuthorityRoleV1,
    external_id: str,
) -> bytes:
    if (
        type(signer_registry) is not V075TrustedSignerRegistryV1
        or type(role) is not V075ExternalAuthorityRoleV1
    ):
        raise V075PublicCampaignAuthorityInvariantViolation(
            "external authority signing request is not typed"
        )
    subject = _fresh_external_id(external_id, role.value)
    return (
        b"acfqp:v075-signed-external-authority-claim:v1"
        + b"\x00"
        + canonical_json_bytes(
            {
                "schema": (
                    "acfqp.v075_signed_external_authority_claim.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "signer_registry_id": signer_registry.registry_id,
                "signer_key_id": (
                    signer_registry.campaign_authority_key.key_id
                ),
                "role": role.value,
                "external_id": subject,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class V075SignedExternalAuthorityClaimV1:
    signer_registry: V075TrustedSignerRegistryV1
    role: V075ExternalAuthorityRoleV1
    external_id: str
    signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.signer_registry)
            is not V075TrustedSignerRegistryV1
            or type(self.role) is not V075ExternalAuthorityRoleV1
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "signed external authority claim is not typed"
            )
        _fresh_external_id(self.external_id, self.role.value)
        message = external_authority_claim_signing_bytes_v1(
            signer_registry=self.signer_registry,
            role=self.role,
            external_id=self.external_id,
        )
        if not verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=self.signer_registry.campaign_authority_key,
            message=message,
            signature_hex=self.signature_hex,
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "external authority signature is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_signed_external_authority_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "signer_registry_id": self.signer_registry.registry_id,
            "signer_key_id": (
                self.signer_registry.campaign_authority_key.key_id
            ),
            "role": self.role.value,
            "external_id": self.external_id,
            "signature_hex": self.signature_hex,
            "signature_verified": True,
        }

    @property
    def claim_id(self) -> str:
        return _hash("signed_external_authority", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "claim_id": self.claim_id}


def _canonical_secret_environment(
    family: V075PublicFamilyGenerationV1,
    secret_laws: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    if (
        type(family) is not V075PublicFamilyGenerationV1
        or family != freeze_v075_public_family_generation_v1()
    ):
        raise V075PublicCampaignAuthorityInvariantViolation(
            "secret environment targets a stale public family"
        )
    try:
        laws = tuple(tuple(law) for law in secret_laws)
    except TypeError as error:
        raise V075PublicCampaignAuthorityInvariantViolation(
            "secret environment must be one concrete exact sequence"
        ) from error
    if len(laws) != len(family.replicate_contexts):
        raise V075PublicCampaignAuthorityInvariantViolation(
            "secret environment must contain one law per context"
        )
    for context, law in zip(family.replicate_contexts, laws, strict=True):
        if (
            not law
            or tuple(rank for rank, _ in law)
            != tuple(sorted({rank for rank, _ in law}))
            or any(
                type(rank) is not int
                or rank <= 0
                or rank > context.rank_cap
                or type(probability) is not Fraction
                or probability <= 0
                for rank, probability in law
            )
            or sum(
                (probability for _, probability in law),
                Fraction(0),
            )
            != 1
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "secret law is not sorted, exact, positive, and normalized"
            )
    return laws


def _validated_secret_salt(value: Any) -> bytes:
    if (
        type(value) is not bytes
        or len(value) < MINIMUM_SECRET_SALT_BYTES
        or len(set(value)) < 16
    ):
        raise V075PublicCampaignAuthorityInvariantViolation(
            "private environment salt must contain at least 32 bytes "
            "and pass the preregistered diversity floor"
        )
    return value


def _secret_environment_bytes(
    family: V075PublicFamilyGenerationV1,
    secret_laws: tuple[tuple[tuple[int, Fraction], ...], ...],
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.v075_private_environment_reveal.v1",
            "schema_version": SCHEMA_VERSION,
            "family_generation_id": family.generation_id,
            "contexts": [
                {
                    "context_id": context.context_id,
                    "law": [
                        {
                            "rank": rank,
                            "probability": _fdoc(probability),
                        }
                        for rank, probability in law
                    ],
                }
                for context, law in zip(
                    family.replicate_contexts,
                    secret_laws,
                    strict=True,
                )
            ],
        }
    )


def _commitment_digest(
    *,
    family: V075PublicFamilyGenerationV1,
    secret_salt: bytes,
    secret_laws: tuple[tuple[tuple[int, Fraction], ...], ...],
) -> str:
    return hashlib.sha256(
        _SECRET_COMMITMENT_DOMAIN
        + b"\x00"
        + secret_salt
        + b"\x00"
        + _secret_environment_bytes(family, secret_laws)
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class V075OpaqueEnvironmentCommitmentV1:
    family: V075PublicFamilyGenerationV1
    commitment_digest: str

    def __post_init__(self) -> None:
        if (
            type(self.family) is not V075PublicFamilyGenerationV1
            or self.family != freeze_v075_public_family_generation_v1()
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "opaque commitment targets a stale public family"
            )
        _cid(self.commitment_digest, "opaque environment commitment digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_salted_opaque_environment_commitment.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "family_generation_id": self.family.generation_id,
            "context_ids": [
                context.context_id
                for context in self.family.replicate_contexts
            ],
            "commitment_digest": self.commitment_digest,
            "commitment_scheme": (
                "SHA256(domain || NUL || secret_salt || NUL || "
                "canonical_private_reveal)"
            ),
            "minimum_secret_salt_bytes": MINIMUM_SECRET_SALT_BYTES,
            "secret_salt_serialized": False,
            "secret_environment_serialized": False,
            "production_law_serialized": False,
        }

    @property
    def commitment_id(self) -> str:
        return _hash("opaque_environment_commitment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}


def seal_opaque_environment_commitment_v1(
    *,
    family: V075PublicFamilyGenerationV1,
    secret_salt: bytes,
    secret_laws: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075OpaqueEnvironmentCommitmentV1:
    canonical_salt = _validated_secret_salt(secret_salt)
    canonical_laws = _canonical_secret_environment(family, secret_laws)
    return V075OpaqueEnvironmentCommitmentV1(
        family,
        _commitment_digest(
            family=family,
            secret_salt=canonical_salt,
            secret_laws=canonical_laws,
        ),
    )


@dataclass(frozen=True, slots=True)
class V075EnvironmentRevealVerificationV1:
    commitment: V075OpaqueEnvironmentCommitmentV1
    matched: bool

    def __post_init__(self) -> None:
        if (
            type(self.commitment) is not V075OpaqueEnvironmentCommitmentV1
            or type(self.matched) is not bool
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "environment reveal verification is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_environment_reveal_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "commitment_id": self.commitment.commitment_id,
            "family_generation_id": self.commitment.family.generation_id,
            "verification_result": "MATCH" if self.matched else "MISMATCH",
            "secret_salt_serialized": False,
            "secret_environment_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return _hash("environment_reveal_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_opaque_environment_reveal_v1(
    *,
    commitment: V075OpaqueEnvironmentCommitmentV1,
    secret_salt: bytes,
    secret_laws: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075EnvironmentRevealVerificationV1:
    if type(commitment) is not V075OpaqueEnvironmentCommitmentV1:
        raise V075PublicCampaignAuthorityInvariantViolation(
            "reveal verifier requires one typed opaque commitment"
        )
    canonical_salt = _validated_secret_salt(secret_salt)
    canonical_laws = _canonical_secret_environment(
        commitment.family,
        secret_laws,
    )
    candidate = _commitment_digest(
        family=commitment.family,
        secret_salt=canonical_salt,
        secret_laws=canonical_laws,
    )
    return V075EnvironmentRevealVerificationV1(
        commitment,
        hmac.compare_digest(candidate, commitment.commitment_digest),
    )


@dataclass(frozen=True, slots=True)
class V075PublicTargetTapeNamespaceV1:
    family: V075PublicFamilyGenerationV1
    environment_commitment: V075OpaqueEnvironmentCommitmentV1
    signer_registry: V075TrustedSignerRegistryV1
    claimed_final_preregistration_registry_id: str
    remote_main_anchor: V075SignedExternalAuthorityClaimV1
    final_preregistration: V075SignedExternalAuthorityClaimV1
    observer_profile: V075SignedExternalAuthorityClaimV1

    def __post_init__(self) -> None:
        expected_roles = (
            (
                self.remote_main_anchor,
                V075ExternalAuthorityRoleV1.REMOTE_MAIN_ANCHOR,
            ),
            (
                self.final_preregistration,
                V075ExternalAuthorityRoleV1.FINAL_PREREGISTRATION,
            ),
            (
                self.observer_profile,
                V075ExternalAuthorityRoleV1.OBSERVER_PROFILE,
            ),
        )
        if (
            type(self.family) is not V075PublicFamilyGenerationV1
            or self.family != freeze_v075_public_family_generation_v1()
            or type(self.environment_commitment)
            is not V075OpaqueEnvironmentCommitmentV1
            or self.environment_commitment.family != self.family
            or type(self.signer_registry)
            is not V075TrustedSignerRegistryV1
            or _cid(
                self.claimed_final_preregistration_registry_id,
                "claimed final-preregistration signer registry",
            )
            != self.signer_registry.registry_id
            or any(
                type(claim) is not V075SignedExternalAuthorityClaimV1
                or claim.signer_registry != self.signer_registry
                or claim.role is not role
                for claim, role in expected_roles
            )
            or len(
                {
                    claim.claim_id
                    for claim, _ in expected_roles
                }
            )
            != 3
            or len(
                {
                    claim.external_id
                    for claim, _ in expected_roles
                }
            )
            != 3
        ):
            raise V075PublicCampaignAuthorityInvariantViolation(
                "target-tape namespace typed authority graph is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_law_free_target_tape_namespace.v1",
            "schema_version": SCHEMA_VERSION,
            "family_generation_id": self.family.generation_id,
            "environment_commitment_id": (
                self.environment_commitment.commitment_id
            ),
            "signer_registry_id": self.signer_registry.registry_id,
            "claimed_final_preregistration_registry_id": (
                self.claimed_final_preregistration_registry_id
            ),
            # Scientific tape identity is bound to the exact external
            # authorities, not to registry-relative signature envelopes.
            # Claim IDs remain separate provenance below.
            "remote_main_anchor_id": self.remote_main_anchor.external_id,
            "final_preregistration_id": (
                self.final_preregistration.external_id
            ),
            "observer_profile_id": self.observer_profile.external_id,
            "remote_main_anchor_claim_id": (
                self.remote_main_anchor.claim_id
            ),
            "final_preregistration_claim_id": (
                self.final_preregistration.claim_id
            ),
            "observer_profile_claim_id": self.observer_profile.claim_id,
            "external_authorities_signature_verified": True,
            "signature_scope": "REGISTRY_RELATIVE_PROVENANCE_ONLY",
            "caller_registry_is_trust_root": False,
            "independent_final_preregistration_verification": False,
            "tracked_git_registry_recomputation_verified": False,
            "production_authority_status": (
                "NONAUTHORIZING_REGISTRY_RELATIVE_CANDIDATE"
            ),
            "production_open_requires": (
                "independent tracked-Git final-preregistration and "
                "remote-main verifier"
            ),
            "production_law_serialized": False,
            "secret_salt_serialized": False,
            "worker_metadata_serialized": False,
            "observer_open_authority": False,
            "target_execution_allowed": False,
        }

    @property
    def target_tape_namespace_id(self) -> str:
        return _hash("target_tape_namespace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "family": self.family.to_document(),
            "environment_commitment": (
                self.environment_commitment.to_document()
            ),
            "signer_registry": self.signer_registry.to_document(),
            "remote_main_anchor": self.remote_main_anchor.to_document(),
            "final_preregistration": (
                self.final_preregistration.to_document()
            ),
            "observer_profile": self.observer_profile.to_document(),
            "target_tape_namespace_id": self.target_tape_namespace_id,
        }


def derive_public_target_tape_namespace_v1(
    *,
    family: V075PublicFamilyGenerationV1,
    environment_commitment: V075OpaqueEnvironmentCommitmentV1,
    signer_registry: V075TrustedSignerRegistryV1,
    claimed_final_preregistration_registry_id: str,
    remote_main_anchor: V075SignedExternalAuthorityClaimV1,
    final_preregistration: V075SignedExternalAuthorityClaimV1,
    observer_profile: V075SignedExternalAuthorityClaimV1,
) -> V075PublicTargetTapeNamespaceV1:
    """Build a nonauthorizing, registry-relative namespace candidate.

    ``claimed_final_preregistration_registry_id`` is only checked for internal
    consistency.  It is never treated as caller-supplied proof that the
    registry is the independently frozen production trust root.
    """

    return V075PublicTargetTapeNamespaceV1(
        family,
        environment_commitment,
        signer_registry,
        claimed_final_preregistration_registry_id,
        remote_main_anchor,
        final_preregistration,
        observer_profile,
    )


__all__ = [
    "ARM_ORDER",
    "DOMAIN_TAGS",
    "FORBIDDEN_HISTORICAL_TARGET_IDS",
    "FROZEN_V072_ATTEMPT_1_CONTENT_ID_COUNT",
    "FROZEN_V072_ATTEMPT_1_CONTENT_ID_MERKLE_ROOT",
    "FROZEN_V072_ATTEMPT_2_CONTENT_ID_COUNT",
    "FROZEN_V072_ATTEMPT_2_CONTENT_ID_MERKLE_ROOT",
    "FROZEN_V072_ATTEMPT_CONTENT_ID_OVERLAP_COUNT",
    "FROZEN_V072_FAILURE_RECORD_CONTENT_IDS",
    "FROZEN_V072_FAILURE_RECORD_CONTENT_ID_COUNT",
    "FROZEN_V072_FAILURE_RECORD_CONTENT_ID_MERKLE_ROOT",
    "HORIZON",
    "INDEPENDENT_FINAL_AUTHORITY_VERIFIER_IMPLEMENTED",
    "K7_MINUS_TWO_TOPOLOGY",
    "K7_TOPOLOGY",
    "MINIMUM_SECRET_SALT_BYTES",
    "PROFILE_KEY",
    "PRODUCTION_OBSERVER_OPEN_ALLOWED",
    "RANK_CAP",
    "ROOT_RANKS",
    "SCHEMA_VERSION",
    "V075EnvironmentRevealVerificationV1",
    "V075ExternalAuthorityRoleV1",
    "V075OpaqueEnvironmentCommitmentV1",
    "V075PublicCampaignAuthorityInvariantViolation",
    "V075PublicFamilyGenerationV1",
    "V075PublicReplicateContextV1",
    "V075PublicTargetTapeNamespaceV1",
    "V075RSAPublicVerificationKeyV1",
    "V075SignedExternalAuthorityClaimV1",
    "V075TrustedSignerRegistryV1",
    "W7_TOPOLOGY",
    "derive_public_target_tape_namespace_v1",
    "external_authority_claim_signing_bytes_v1",
    "freeze_v075_public_family_generation_v1",
    "registered_public_context_v1",
    "seal_opaque_environment_commitment_v1",
    "verify_rsa_pkcs1_v1_5_sha256_signature_v1",
    "verify_opaque_environment_reveal_v1",
]
