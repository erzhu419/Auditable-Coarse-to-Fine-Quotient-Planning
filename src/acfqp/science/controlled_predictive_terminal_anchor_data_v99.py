"""Load accepted V98 terminal blocks once, preserving the original censoring."""
from collections import Counter
from copy import deepcopy
from itertools import groupby
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_continuation_data_v91 import _key, _rows, TERMINAL
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES
from acfqp.science.controlled_predictive_paired_bellman_data_v96 import extract_paired_bellman_rows


def load_batch(folder):
    """Reconstruct one incremental batch for its recorded four/eight replicas.

    All branch costs are read, including discarded partial blocks. Source costs
    are inherited from the acquisition ledger without rereading source games.
    Complete original roots remain the only suppliers of training/heldout rows.
    """
    started = perf_counter()
    folder = Path(folder)
    construction_path = folder / "construction.json"
    branch_path = folder / "branch_games.jsonl.gz"
    acquisition = json.loads(construction_path.read_text())["acquisition"]
    replicas = acquisition["replicas"]
    if replicas not in (4, 8):
        raise ValueError("V98 retained allocation must have four or eight replicas")
    records = acquisition["root_records"]
    cursors = list(range(acquisition["start_cursor"], acquisition["next_cursor"]))
    if [record["cursor"] for record in records] != cursors:
        raise ValueError("retained root records disagree with the incremental cursor window")
    if acquisition["episode_cutoff"] != acquisition["next_cursor"] // len(QUERIES) + 1:
        raise ValueError("episode cutoff disagrees with the incremental cursor window")
    accepted = {_key(root): root for root in acquisition["completed_roots"]}
    if len(accepted) != len(acquisition["completed_roots"]):
        raise ValueError("duplicate accepted V98 root")
    branch_records, completed_keys = {}, set()
    partition = {name: Counter(source_transitions=0, branch_transitions=0, total_transitions=0)
                 for name in ("training", "heldout", "unincorporated")}
    for record in records:
        episode, qi = divmod(record["cursor"], len(QUERIES))
        if (record["episode"] != episode or record["query"] != tuple(QUERIES)[qi]
                or record["replicas"] != replicas):
            raise ValueError("root query/episode/replicas disagree with the acquisition window")
        complete = record["complete_block"]
        disposition = ("heldout" if episode % 5 == 4 else "training") if complete else "unincorporated"
        if record["disposition"] != disposition:
            raise ValueError("retained complete/censored root disposition disagrees with its episode")
        if record["root"] is not None:
            key = _key(record["root"])
            if key[:2] != (record["query"], episode):
                raise ValueError("captured root metadata disagrees with its source episode")
            if record["branch_trajectories"]:
                if key in branch_records:
                    raise ValueError("duplicate retained branch root")
                branch_records[key] = record
            if complete:
                completed_keys.add(key)
                root = accepted.get(key)
                if (root is None or root["replicas"] != replicas or root["heldout"] != (episode % 5 == 4)
                        or any(root[field] != record["root"][field] for field in record["root"])
                        or record["source_status"] not in TERMINAL):
                    raise ValueError("accepted roots disagree with the complete source/root records")
        partition[disposition].update(source_transitions=record["source_transitions"],
            branch_transitions=record["branch_transitions"],
            total_transitions=record["source_transitions"] + record["branch_transitions"])
    if completed_keys != set(accepted):
        raise ValueError("accepted root roster is not the acquisition's complete block roster")
    rows, seen, extracted = [], set(), set()
    work, planning, outcomes, counts = Counter(), Counter(), Counter(), Counter()
    expected = {(option, replica) for option in OPTIONS for replica in range(replicas)}
    for key, stream in groupby(_rows(branch_path), key=lambda raw: _key(raw["root"])):
        if key in seen or key not in branch_records:
            raise ValueError("branch root is repeated or absent from the incremental acquisition")
        seen.add(key)
        record = branch_records[key]
        indexed, root_work, root_outcomes = {}, Counter(), Counter()
        for raw in stream:
            identity, game = (raw["option"], raw["replica"]), raw["game"]
            if identity not in expected or identity in indexed or raw["root"] != record["root"]:
                raise ValueError("retained branch option/replica/root differs from its original cohort")
            if raw["env_seed"] != record["branch_seed"] + raw["replica"]:
                raise ValueError("retained branch seed differs from the acquisition stream")
            if (len(game["steps"]) != game["work"]["sampled_transitions"]
                    or sum(step["score"] for step in game["steps"]) != game["return_score"]):
                raise ValueError("retained trajectory score or transition count disagrees with its steps")
            indexed[identity] = raw
            root_work.update(game["work"])
            work.update(game["work"])
            planning.update(raw["planning_counts"])
            root_outcomes[game["status"]] += 1
            outcomes[game["status"]] += 1
            counts["trajectories_read"] += 1
            counts["steps_read"] += len(game["steps"])
        complete = set(indexed) == expected and all(raw["game"]["status"] in TERMINAL for raw in indexed.values())
        if (complete != record["complete_block"] or complete != (key in accepted)
                or len(indexed) != record["branch_trajectories"]
                or root_work["sampled_transitions"] != record["branch_transitions"]
                or root_outcomes["CUTOFF"] != record["branch_cutoff_trajectories"]):
            raise ValueError("retained branch completion or costs disagree with the acquisition ledger")
        if not complete:
            counts["excluded_branch_roots"] += 1
            counts["excluded_branch_trajectories"] += len(indexed)
            continue
        before = len(rows)
        for option in OPTIONS[1:]:
            for replica in range(replicas):
                candidate, reference = indexed[option, replica], indexed["H2", replica]
                rows.extend(extract_paired_bellman_rows(candidate, reference))
                counts["paired_score_steps_processed"] += len(candidate["game"]["steps"]) + len(reference["game"]["steps"])
        if len(rows) - before != record["paired_rows"] or len(rows) - before != accepted[key]["paired_rows"]:
            raise ValueError("extracted row count disagrees with the accepted root ledger")
        extracted.add(key)
    if seen != set(branch_records) or extracted != set(accepted):
        raise ValueError("retained branch file is missing acquisition roots")
    if (work != Counter(acquisition["branches"]["ground_work"])
            or planning != Counter(acquisition["branches"]["planning_counts"])
            or outcomes != Counter(acquisition["branches"]["outcomes"])):
        raise ValueError("retained branch work/outcomes differ from the acquisition ledger")
    source_work = acquisition["source"]["ground_work"]
    if (sum(record["source_transitions"] for record in records) != source_work.get("sampled_transitions", 0)
            or source_work.get("sampled_transitions", 0) + work["sampled_transitions"] != acquisition["used_transitions"]
            or any(partition[name] != Counter(acquisition["cost_partition"][name]) for name in partition)):
        raise ValueError("inherited physical costs do not match the original source/branch partition")
    counts.update(complete_roots=len(accepted), training_roots=sum(key[1] % 5 != 4 for key in accepted),
        heldout_roots=sum(key[1] % 5 == 4 for key in accepted), paired_rows=len(rows),
        training_paired_rows=sum(row["episode"] % 5 != 4 for row in rows),
        heldout_paired_rows=sum(row["episode"] % 5 == 4 for row in rows),
        terminal_anchor_rows=sum(not row["next_candidate_active"] and not row["next_reference_active"] for row in rows),
        bootstrap_rows=sum(row["next_candidate_active"] or row["next_reference_active"] for row in rows),
        source_trajectory_files_read=0, branch_trajectory_files_read=1, new_environment_transitions=0, tree_fits=0)
    if any(counts[key] != acquisition["counts"][key] for key in (
            "complete_roots", "training_roots", "heldout_roots", "paired_rows",
            "training_paired_rows", "heldout_paired_rows", "terminal_anchor_rows", "bootstrap_rows")):
        raise ValueError("reconstructed cohort counts disagree with the acquisition ledger")
    return rows, dict(source=str(folder.resolve()),
        paths=dict(construction=str(construction_path.resolve()), branch_games=str(branch_path.resolve())),
        life=acquisition["life"], replicas=replicas, budget=acquisition["budget"],
        start_cursor=acquisition["start_cursor"], next_cursor=acquisition["next_cursor"],
        episode_cutoff=acquisition["episode_cutoff"], counts=dict(counts), row_weight=1 / 32,
        root_rosters={query: {role: [deepcopy(root) for key, root in accepted.items()
            if key[0] == query and (key[1] % 5 == 4) == (role == "heldout")]
            for role in ("training", "heldout")} for query in QUERIES},
        inherited_source_work=deepcopy(source_work), inherited_branch_work=dict(work),
        inherited_source_planning=deepcopy(acquisition["source"]["planning_counts"]),
        inherited_branch_planning=dict(planning), inherited_physical_transitions=acquisition["used_transitions"],
        inherited_cost_partition={name: dict(values) for name, values in partition.items()},
        source_cost_provenance="Acquisition ledger; source trajectory file not reread.",
        seconds=perf_counter() - started)
