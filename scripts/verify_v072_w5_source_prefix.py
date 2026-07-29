"""Focused real V0-068 W5 prefix check for the V0-072 source archive."""

from acfqp import observation_support_campaign_v1 as campaign
from acfqp import transition_tuple_observer_v1 as observer
from acfqp import verified_source_acquisition_archive_v2 as archive


def main() -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    result = campaign.run_observation_support_context_v1(
        context,
        max_workers=16,
    )
    executions = {item.checkpoint: item for item in result.executions}
    pair, trials = archive._derive_pair(
        source_context_id=context.context_id,
        source_context_key=context.context_key,
        before=executions[2_048],
        after=executions[4_096],
    )
    assert trials
    assert all(
        item.local_snapshot.raw_prefix_extension
        .incremental_accepted_draws
        == 2_048
        for item in trials
    )
    assert all(
        item.local_snapshot.raw_prefix_extension
        .incremental_random_word_calls
        >= 2_048
        for item in trials
    )
    print(
        pair.pair_id,
        len(trials),
        len({item.portable_feature.feature_key for item in trials}),
    )


if __name__ == "__main__":
    main()
