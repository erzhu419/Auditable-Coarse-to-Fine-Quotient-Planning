"""Give the four-action decision boundary half of each retained pair's mass."""
from collections import defaultdict
from math import fsum
from time import perf_counter

from acfqp.science.controlled_predictive_paired_continuation_data_v92 import PAIR_WEIGHT


MASS_FIELDS = (
    "prior_total_mass", "new_total_mass", "prior_boundary_mass", "new_boundary_mass",
    "prior_tail_mass", "new_tail_mass", "singleton_boundary_mass",
)


def _summary(groups):
    result = {key: sum(group[key] for group in groups) for key in ("groups", "singletons", "rows")}
    result.update({key: fsum(group[key] for group in groups) for key in MASS_FIELDS})
    result["max_pair_mass_error"] = max((group["max_pair_mass_error"] for group in groups), default=0.)
    for version in ("prior", "new"):
        total = result[f"{version}_total_mass"]
        result[f"{version}_boundary_share"] = result[f"{version}_boundary_mass"] / total if total else None
    return result


def redistribute_weights(rows, checkpoint):
    """Reweight eligible V93 pairs without changing their total training mass.

    Input contains one lifecycle. V93 collects at most one root per query and
    episode, so query/episode/option/replica identifies one full grid. Heldout
    and future rows retain their original weights. Row dictionaries are copied;
    observed states and targets are neither changed nor recomputed.
    """
    started = perf_counter()
    weighted = [dict(row) for row in rows]
    groups, episodes = defaultdict(list), defaultdict(set)
    counts = dict(input_rows=len(weighted), training_rows=0, heldout_rows=0, future_rows=0,
                  groups=0, changed_weight_rows=0, new_environment_transitions=0, tree_fits=0)
    for index, row in enumerate(weighted):
        episode = row["episode"]
        if episode >= checkpoint:
            counts["future_rows"] += 1
        elif episode % 5 == 4:
            counts["heldout_rows"] += 1
        else:
            counts["training_rows"] += 1
            groups[row["query"], episode, row["option"], row["replica"]].append(index)
            episodes[row["query"]].add(episode)
    by_query, all_groups = defaultdict(list), []
    for (query, episode, option, replica), indices in groups.items():
        ordered = sorted(indices, key=lambda index: weighted[index]["step"])
        m = len(ordered)
        if [weighted[index]["step"] for index in ordered] != list(range(4, 4 + 16 * m, 16)):
            raise ValueError("training pair requires exactly one k=4 row and its complete 4+16j grid")
        prior = [weighted[index]["weight"] for index in ordered]
        if any(weight != PAIR_WEIGHT for weight in prior):
            raise ValueError("boundary redistribution requires original fixed 1/32 row weights")
        updated = ([PAIR_WEIGHT] if m == 1 else
                   [m * PAIR_WEIGHT / 2] + [m * PAIR_WEIGHT / (2 * (m - 1))] * (m - 1))
        for index, previous, weight in zip(ordered, prior, updated):
            weighted[index]["weight"] = weight
            counts["changed_weight_rows"] += previous != weight
        summary = dict(groups=1, singletons=int(m == 1), rows=m,
            prior_total_mass=fsum(prior), new_total_mass=fsum(updated),
            prior_boundary_mass=prior[0], new_boundary_mass=updated[0],
            prior_tail_mass=fsum(prior[1:]), new_tail_mass=fsum(updated[1:]),
            max_pair_mass_error=abs(fsum(prior) - fsum(updated)),
            singleton_boundary_mass=prior[0] if m == 1 else 0.)
        all_groups.append(summary)
        by_query[query].append(summary)
    counts["groups"] = len(groups)
    return weighted, dict(checkpoint=checkpoint, target_boundary_share=0.5,
        scope="Eligible training rows only; singleton pairs retain all mass at the boundary.",
        eligible_episodes={query: sorted(values) for query, values in sorted(episodes.items())},
        queries={query: _summary(values) for query, values in sorted(by_query.items())},
        totals=_summary(all_groups), counts=counts, seconds=perf_counter() - started)
