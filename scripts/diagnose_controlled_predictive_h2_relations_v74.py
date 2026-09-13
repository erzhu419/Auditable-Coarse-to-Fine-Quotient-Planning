"""Exploratory retained-data upper bound for an H2 inactive-rank relation.

This is separate from the frozen V74 arms. It reads existing board labels and
exact contract IDs only, with no model construction, planning, fitting or
domain calls. Contract IDs are compared within each case, never across cases.
"""
from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def relation_key(board, goal):
    counts = Counter(board)
    eligible = {rank for rank in counts if 4 <= rank < goal and counts[rank] == 1
                and counts[rank - 1] == 0 and counts[rank - 2] == 0}
    key, variable = [], 0
    for rank in board:
        if rank in eligible:
            key.append(("VARIABLE", variable))
            variable += 1
        else:
            key.append(("RANK", rank))
    return tuple(key), variable


def diagnose(source, roster):
    started = perf_counter()
    targets = json.loads(roster.read_text())["target"]
    cases, total = [], Counter()
    for target in targets:
        case = target["name"]
        path = source / case / "COMPOSED_MAP.package.json"
        package = json.loads(path.read_text())
        goal = package["kernel"]["rule"]["goal_rank"]
        cells = {cell: (h, status) for cell, h, status in package["kernel"]["cells"]}
        boards = {tuple(board): cell for h, board, cell in package["router"]["labels"]
                  if h == 2 and cells[cell][1] == "ACTIVE"}
        groups, eligible_boards, eligible_tiles = defaultdict(list), 0, 0
        for board, cell in boards.items():
            key, eligible = relation_key(board, goal)
            groups[key].append((board, cell))
            eligible_boards += bool(eligible)
            eligible_tiles += eligible
        conflicts = [members for members in groups.values()
                     if len({cell for _, cell in members}) > 1]
        counts = dict(h2_geometries=len(boards), exact_h2_cells=len(set(boards.values())),
            relation_keys=len(groups), relation_geometry_reduction=len(boards) - len(groups),
            exact_geometry_reduction_upper_bound=len(boards) - len(set(boards.values())),
            relation_groups_merging_geometries=sum(len(members) > 1 for members in groups.values()),
            conflict_groups=len(conflicts), eligible_boards=eligible_boards, eligible_tiles=eligible_tiles)
        total.update(counts)
        cases.append(dict(case=case, source=str(path.relative_to(ROOT)), **counts,
            conflict_examples=[[dict(board=list(board), cell=cell) for board, cell in members[:4]]
                               for members in conflicts[:3]]))
    total["cases"] = len(cases)
    geometric = total["h2_geometries"]
    summary = dict(total)
    summary.update(relation_reduction_fraction=total["relation_geometry_reduction"] / geometric if geometric else 0,
        exact_reduction_upper_bound_fraction=total["exact_geometry_reduction_upper_bound"] / geometric if geometric else 0)
    return dict(schema="acfqp.h2_relation_diagnostic.v74", kind="exploratory_retained_data_diagnostic",
        part_of_v74_preregistered_arms=False, source=str(source), roster=str(roster),
        rule="4 <= r < goal; count(r)=1; count(r-1)=count(r-2)=0; distinct variables in position order",
        scope="Per-case H2 active geometries; exact IDs are never compared across cases.",
        ground_calls=0, fit_calls=0, planning_calls=0, model_builds=0,
        summary=summary, cases=cases, elapsed_seconds=perf_counter() - started)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
        default=ROOT / "reports/controlled_predictive_observation_v70")
    parser.add_argument("--roster", type=Path,
        default=ROOT / "reports/controlled_predictive_composition_v69/roster.json")
    parser.add_argument("--output", type=Path,
        default=ROOT / "reports/controlled_predictive_effect_v74.h2_relation_diagnostic.json")
    args = parser.parse_args()
    result = diagnose(args.source, args.roster)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result["summary"], sort_keys=True))
