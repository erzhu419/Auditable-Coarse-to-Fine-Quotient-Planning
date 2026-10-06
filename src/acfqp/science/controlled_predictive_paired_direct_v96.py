"""Direct option selection from model prefixes and a paired H2 continuation."""
from collections import Counter
from math import fsum
from time import perf_counter

from acfqp.science.controlled_predictive_direct_value_v95 import _simulate_prefix
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility


class PairedDirectSelector:
    def __init__(self, value_model, rule, seed_base, replicas=32):
        if replicas <= 0:
            raise ValueError("replicas must be positive")
        self.value_model, self.rule, self.seed_base, self.replicas = value_model, rule, seed_base, replicas
        self.checkpoint = value_model.checkpoint
        self.last_prefixes, self.last_log = [], None

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        started = perf_counter()
        prefixes, indexed = [], {}
        model_work, planning, values, outcomes = Counter(), Counter(), Counter(), Counter()
        wiring = dict(spawn_uniforms_aligned=True, model_uniforms_aligned=True,
                      single_initiations=True, committed_lengths_match=True, terminal_absorbs=True)
        for replica in range(self.replicas):
            for option in OPTIONS:
                prefix = _simulate_prefix(board, query, option, replica, self.seed_base + replica, self.rule)
                indexed[replica, option] = prefix
                prefixes.append(prefix)
                model_work.update(prefix["model_work"])
                planning.update(prefix["planning_counts"])
                outcomes[prefix["status"]] += 1
                steps, record = prefix["steps_count"], prefix["controller"]
                duration = 0 if option == "H2" else int(option.split("_")[1])
                expected = min(duration, steps)
                wiring["spawn_uniforms_aligned"] &= prefix["model_work"]["spawn_uniform_draws"] == 2 * steps
                wiring["model_uniforms_aligned"] &= prefix["planning_counts"]["model_uniform_draws"] == 4 * steps
                wiring["single_initiations"] &= (len(record["events"]) == 1
                    and record["initiation_step"] == 0 and record["selected_option"] == option)
                wiring["committed_lengths_match"] &= (record["fragment_actions"] == expected
                    and prefix["action_paths"] == ["fragment"] * expected + ["H2"] * (steps - expected))
                wiring["terminal_absorbs"] &= (all(step["status"] == "ACTIVE" for step in prefix["steps"][:-1])
                    and (prefix["status"] != "ACTIVE" or steps == 4))
            reference = indexed[replica, "H2"]
            reference.update(paired_direct=[0., 0., 0.], paired_tail=[0., 0., 0.], paired_completed=[0., 0., 0.])
            for option in OPTIONS[1:]:
                candidate = indexed[replica, option]
                direct = [c - r for c, r in zip(candidate["direct"], reference["direct"])]
                tail = self.value_model.predict_pair(candidate["final_board"], reference["final_board"],
                    candidate["status"] == "ACTIVE", reference["status"] == "ACTIVE", query, values)
                candidate.update(paired_direct=direct, paired_tail=tail,
                    paired_completed=[observed + future for observed, future in zip(direct, tail)])
        predictions = {"H2": dict(target=[0., 0., 0.], value=0.)}
        chosen, best = "H2", 0.
        for option in OPTIONS[1:]:
            if option not in allowed:
                continue
            target = [fsum(indexed[replica, option]["paired_completed"][component]
                           for replica in range(self.replicas)) / self.replicas for component in range(3)]
            value = float(_utility(target, QUERIES[query]))
            predictions[option] = dict(target=target, value=value)
            if value > best:
                chosen, best = option, value
        self.last_prefixes = prefixes
        self.last_log = dict(replicas=self.replicas, trajectories=len(prefixes), model_work=dict(model_work),
            planning_counts=dict(planning), value_counts=dict(values), wiring=wiring,
            outcomes=dict(outcomes), seconds=perf_counter() - started)
        if work is not None:
            work["candidate_selector_decisions"] = work.get("candidate_selector_decisions", 0) + 1
            work["candidate_trajectories"] = work.get("candidate_trajectories", 0) + len(prefixes)
            for group in (model_work, planning, values):
                for name, value in group.items():
                    key = "candidate_" + name
                    work[key] = work.get(key, 0) + value
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"], value=best,
                    predictions=predictions)
