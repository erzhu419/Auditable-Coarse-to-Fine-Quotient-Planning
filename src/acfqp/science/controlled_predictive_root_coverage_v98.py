"""Acquire fresh root coverage under a hard budget of physical transitions."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_budgeted_fragments_v86 import collect_source, sample_root
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES
from acfqp.science.controlled_predictive_paired_bellman_data_v96 import extract_paired_bellman_rows


MAX_STEPS = 2000


def source_seed(life, episode, query):
    return 98_000_000 + life * 100_000 + episode * 10 + tuple(QUERIES).index(query)


def branch_seed(life, episode, query):
    return 980_000_000_000 + life * 1_000_000_000 + episode * 100 + tuple(QUERIES).index(query) * 10


def _write(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")


def acquire_batch(life, replicas, rule, budget, cursor, folder):
    """Spend one incremental budget, advancing past every completed or cut item.

    Cursor indexes episode first, then query. A source cutoff or incomplete
    five-option block is charged and discarded without resumption. Rows retain
    the original 1/32 weight for both allocations: four replicas give half the
    root mass of eight before global normalization. For a fixed allocation,
    replacing this by 1/(4*replicas) is only a uniform scaling of tree weights.
    """
    if replicas not in (4, 8) or budget < 0 or cursor < 0:
        raise ValueError("V98 requires four/eight replicas and nonnegative budget/cursor")
    started = perf_counter()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = {name: folder / f"{name}_games.jsonl.gz" for name in ("source", "branch")}
    source_work, branch_work, source_planning, branch_planning = (Counter() for _ in range(4))
    source_outcomes, branch_outcomes = Counter(), Counter()
    partition = {name: Counter(source_transitions=0, branch_transitions=0, total_transitions=0)
                 for name in ("training", "heldout", "unincorporated")}
    query_counts = {query: Counter(source_games=0, source_cutoffs=0, missing_trigger_sources=0,
        complete_roots=0, training_roots=0, heldout_roots=0, incomplete_roots=0,
        source_transitions=0, branch_transitions=0, paired_rows=0, training_paired_rows=0,
        heldout_paired_rows=0) for query in QUERIES}
    rows, complete_roots, records = [], [], []
    start_cursor, used = cursor, 0
    with gzip.open(paths["source"], "wt") as sources, gzip.open(paths["branch"], "wt") as branches:
        while used < budget:
            before = used
            episode, query_index = divmod(cursor, len(QUERIES))
            query = tuple(QUERIES)[query_index]
            start_seed, pair_seed = source_seed(life, episode, query), branch_seed(life, episode, query)
            root, raw_source, source_log = collect_source(life, episode, query, rule,
                start_seed, budget - used, max_steps=MAX_STEPS)
            _write(sources, raw_source)
            source_work.update(source_log["ground_work"])
            source_planning.update(source_log["planning_counts"])
            source_outcomes.update(source_log["outcomes"])
            source_steps = source_log["ground_work"].get("sampled_transitions", 0)
            used += source_steps
            source_status = raw_source["game"]["status"]
            query_counts[query].update(source_games=1, source_transitions=source_steps,
                source_cutoffs=int(source_status == "CUTOFF"), missing_trigger_sources=int(root is None))
            record = dict(cursor=cursor, episode=episode, query=query, replicas=replicas,
                source_seed=start_seed, branch_seed=pair_seed, source_status=source_status,
                source_cutoff_cause=("budget" if used == budget else "max_steps") if source_status == "CUTOFF" else None,
                root=root, source_transitions=source_steps, branch_transitions=0,
                branch_trajectories=0, branch_cutoff_trajectories=0,
                missing_branch_trajectories=len(OPTIONS) * replicas, complete_block=False, paired_rows=0,
                branch_cutoff_cause=None, discard_reason="source_cutoff" if source_status == "CUTOFF" else
                    "no_trigger" if root is None else "budget_before_branches")
            source_usable = source_status in ("WON", "LOST") and root is not None
            disposition = "unincorporated"
            if source_usable and used < budget:
                _, raw_branches, branch_log = sample_root(root, rule, pair_seed,
                    budget - used, replicas=replicas, max_steps=MAX_STEPS)
                for raw in raw_branches:
                    _write(branches, dict(root=root, **raw))
                branch_work.update(branch_log["ground_work"])
                branch_planning.update(branch_log["planning_counts"])
                branch_outcomes.update(branch_log["outcomes"])
                branch_steps = branch_log["ground_work"].get("sampled_transitions", 0)
                used += branch_steps
                record.update(branch_transitions=branch_steps, branch_trajectories=len(raw_branches),
                    branch_cutoff_trajectories=sum(raw["game"]["status"] == "CUTOFF" for raw in raw_branches),
                    missing_branch_trajectories=len(OPTIONS) * replicas - len(raw_branches))
                query_counts[query]["branch_transitions"] += branch_steps
                indexed = {(raw["option"], raw["replica"]): raw for raw in raw_branches}
                complete = (set(indexed) == {(option, replica) for option in OPTIONS for replica in range(replicas)}
                    and len(raw_branches) == len(indexed)
                    and all(raw["game"]["status"] in ("WON", "LOST") for raw in raw_branches))
                if complete != branch_log["complete_block"]:
                    raise ValueError("budgeted branch completion disagrees with retained option/replica records")
                record["complete_block"] = complete
                if complete:
                    record["discard_reason"] = None
                    pair_rows = []
                    for option in OPTIONS[1:]:
                        for replica in range(replicas):
                            candidate = dict(root=root, **indexed[option, replica])
                            reference = dict(root=root, **indexed["H2", replica])
                            pair_rows.extend(extract_paired_bellman_rows(candidate, reference))
                    rows.extend(pair_rows)
                    record["paired_rows"] = len(pair_rows)
                    heldout = episode % 5 == 4
                    disposition = "heldout" if heldout else "training"
                    complete_roots.append(dict(root, replicas=replicas, paired_rows=len(pair_rows), heldout=heldout,
                        source_transitions=source_steps, branch_transitions=branch_steps))
                    query_counts[query].update(complete_roots=1, paired_rows=len(pair_rows))
                    query_counts[query]["heldout_roots" if heldout else "training_roots"] += 1
                    query_counts[query]["heldout_paired_rows" if heldout else "training_paired_rows"] += len(pair_rows)
                else:
                    record["discard_reason"] = "incomplete_branch_block"
                    record["branch_cutoff_cause"] = "budget" if used == budget else "max_steps"
                    query_counts[query]["incomplete_roots"] += 1
            elif source_usable:
                query_counts[query]["incomplete_roots"] += 1
            record.update(disposition=disposition, budget_exhausted=used == budget,
                          used_transitions_after=used)
            partition[disposition].update(source_transitions=source_steps,
                branch_transitions=record["branch_transitions"],
                total_transitions=source_steps + record["branch_transitions"])
            records.append(record)
            cursor += 1
            if not before < used <= budget:
                raise ValueError("acquisition must make progress without exceeding its physical budget")
    counts = Counter()
    for values in query_counts.values():
        counts.update(values)
    counts.update(branch_trajectories=sum(record["branch_trajectories"] for record in records),
        source_rows_written=len(records), branch_rows_written=sum(record["branch_trajectories"] for record in records),
        terminal_anchor_rows=sum(not row["next_candidate_active"] and not row["next_reference_active"] for row in rows),
        bootstrap_rows=sum(row["next_candidate_active"] or row["next_reference_active"] for row in rows),
        tree_fits=0)
    return rows, cursor, dict(life=life, replicas=replicas, budget=budget,
        start_cursor=start_cursor, next_cursor=cursor, episode_cutoff=cursor // len(QUERIES) + 1,
        used_transitions=used, unused_budget=budget - used, budget_exhausted=used == budget,
        paths={name: str(path.resolve()) for name, path in paths.items()},
        source=dict(ground_work=dict(source_work), planning_counts=dict(source_planning), outcomes=dict(source_outcomes)),
        branches=dict(ground_work=dict(branch_work), planning_counts=dict(branch_planning), outcomes=dict(branch_outcomes)),
        cost_partition={name: dict(values) for name, values in partition.items()},
        queries={query: dict(values, training_episodes=sorted({row["episode"] for row in rows
            if row["query"] == query and row["episode"] % 5 != 4}),
            heldout_episodes=sorted({row["episode"] for row in rows if row["query"] == query and row["episode"] % 5 == 4}))
            for query, values in query_counts.items()},
        counts=dict(counts), completed_roots=complete_roots, root_records=records,
        row_weight=1 / 32, max_steps=MAX_STEPS, seconds=perf_counter() - started)
