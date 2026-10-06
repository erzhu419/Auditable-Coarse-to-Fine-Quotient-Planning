"""Freeze the complete V81 first-round heldout cohort and its local choices."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import _predict
from acfqp.science.controlled_predictive_policy_advantage_v81 import (
    Policy, QUERIES, action_features,
)


def prepare_roots(source_folder, lifecycle, rule):
    """Select against each recorded reference, without rerunning its parent.

    This conditions the experiment on the action actually used when the V81
    label was collected. Every first-round heldout root remains in the cohort,
    including roots where the learned layer retains that reference action.
    """
    started = perf_counter()
    folder = Path(source_folder) / f"life_{lifecycle}" / "iteration_1"
    logs_path = folder / "root_logs.json"
    policy_path = folder / "current_policy.json"
    source = json.loads(logs_path.read_text())
    policy = Policy.from_payload(json.loads(policy_path.read_text()))
    if policy.iteration != 1 or policy.parent.iteration != 0:
        raise ValueError("V82 requires the fixed first-round policy and H2 parent")
    heldout = sorted((entry for entry in source if entry["root"]["episode"] % 5 == 4),
                     key=lambda entry: (entry["root"]["query"], entry["root_index"]))
    counts = Counter(source_root_records_read=len(source), policy_payloads_read=1)
    inherited_work = Counter()
    roots = []
    for entry in heldout:
        if entry["censored_root"]:
            raise ValueError("The fixed source cohort contains a censored root")
        root = entry["root"]
        reference = root["reference_action"]
        _, moves = rule.classify(root["board"], counts)
        legal_actions = sorted(action for action, _, _ in moves)
        if reference not in legal_actions:
            raise ValueError("The retained reference must be legal at its source root")
        alternatives = [action for action in legal_actions if action != reference]
        selected, advantage, best = reference, [0.0, 0.0, 0.0], 0.0
        if alternatives:
            x = np.asarray([action_features(root["board"], action, reference, rule, counts)
                            for action in alternatives], dtype=np.float32)
            predictions = _predict(policy.trees[root["query"]], x, counts)
            counts["advantage_prediction_rows"] += len(alternatives)
            query = QUERIES[root["query"]]
            for action, vector in zip(alternatives, predictions):
                value = (query["reward_weight"] * vector[0]
                         - query["failure_penalty"] * vector[1]
                         + query["goal_bonus"] * vector[2])
                if value > best:
                    selected, advantage, best = action, vector.tolist(), float(value)
        original = ([list(delta) for delta in entry["pair_deltas"][selected]]
                    if selected != reference else [[0.0] * 3 for _ in range(2)])
        observed = np.mean(original, axis=0).tolist()
        roots.append(dict(lifecycle=lifecycle, query=root["query"], episode=root["episode"],
            step=root["step"], root_index=entry["root_index"], board=list(root["board"]),
            reference_action=reference, selected_action=selected,
            predicted_advantage=advantage, old_observed_advantage=observed,
            original_replica_deltas=original, legal_actions=legal_actions,
            override=selected != reference))
        inherited_work.update(entry["ground_work"])
    return roots, dict(roots=len(roots), overrides=sum(root["override"] for root in roots),
        roots_by_query=dict(Counter(root["query"] for root in roots)),
        source_paths=dict(root_logs=str(logs_path.resolve()), policy=str(policy_path.resolve())),
        inherited_source=dict(trajectories=sum(entry["trajectories"] for entry in heldout),
                              ground_work=dict(inherited_work)),
        counts=dict(counts), ground_calls=0, tree_fits=0, model_uniform_draws=0,
        seconds=perf_counter() - started)
