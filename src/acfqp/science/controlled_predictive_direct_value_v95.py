"""Choose a fragment from model-only four-action prefixes and shared H2 value."""
from collections import Counter
from math import fsum
import random
from time import perf_counter

from acfqp.science.controlled_predictive_fragment_experience_v83 import _controller_record
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, OPTIONS, QUERIES, _utility
from acfqp.science.controlled_predictive_lifelong_planner_v77 import _spawn


def _simulate_prefix(board, query, option, replica, spawn_seed, rule):
    """Apply the supplied rewrite/spawn law; a winning swipe still spawns first."""
    board = tuple(board)
    initial = board
    model_work = Counter()
    status, _ = rule.classify(board, model_work)
    if status != "ACTIVE":
        raise ValueError("direct selection requires an active trigger board")
    planning_seed = spawn_seed + 1_000_000_000_000
    spawn_rng = random.Random(spawn_seed)
    controller = FragmentController(None, query, rule, random.Random(planning_seed),
                                    immediate=True, fixed_option=option)
    steps, paths, score = [], [], 0
    for step in range(4):
        before = controller.fragment_actions
        action = controller.choose(board, step)
        paths.append("fragment" if controller.fragment_actions > before else "H2")
        afterstate, gained, changed = rule.swipe(board, action, model_work)
        if not changed:
            raise ValueError("prefix controller selected an illegal model action")
        draws = spawn_rng.random(), spawn_rng.random()
        model_work["spawn_uniform_draws"] += 2
        next_board = _spawn(afterstate, draws, rule, model_work)
        model_work["synthetic_transitions"] += 1
        status, _ = rule.classify(next_board, model_work)
        steps.append(dict(board=list(board), action=action, afterstate=list(afterstate),
            next_board=list(next_board), score=gained, status=status))
        score += gained
        board = next_board
        if status != "ACTIVE":
            break
    return dict(option=option, replica=replica, spawn_seed=spawn_seed, planning_seed=planning_seed,
        initial_board=list(initial), final_board=list(board), status=status,
        return_score=score, steps_count=len(steps), steps=steps, action_paths=paths,
        controller=_controller_record(controller), planning_counts=dict(controller.work),
        model_work=dict(model_work), direct=[score / 2048, float(status == "LOST"), float(status == "WON")])


class DirectSelector:
    """Simulate fixed candidate prefixes, then choose by their paired R/F/S means."""

    def __init__(self, value_model, rule, seed_base, replicas=32):
        if replicas <= 0:
            raise ValueError("replicas must be positive")
        self.value_model, self.rule = value_model, rule
        self.seed_base, self.replicas = seed_base, replicas
        self.checkpoint = value_model.checkpoint
        self.last_prefixes, self.last_log = [], None

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        started = perf_counter()
        prefixes, indexed = [], {}
        model_work, planning_counts, value_counts, outcomes = Counter(), Counter(), Counter(), Counter()
        wiring = dict(spawn_uniforms_aligned=True, model_uniforms_aligned=True,
                      single_initiations=True, committed_lengths_match=True, terminal_absorbs=True)
        for replica in range(self.replicas):
            for option in OPTIONS:
                prefix = _simulate_prefix(board, query, option, replica, self.seed_base + replica, self.rule)
                tail = (self.value_model.predict(prefix["final_board"], query, value_counts)
                        if prefix["status"] == "ACTIVE" else [0.0, 0.0, 0.0])
                prefix["tail"] = tail
                prefix["completed"] = [direct + future for direct, future in zip(prefix["direct"], tail)]
                prefixes.append(prefix)
                indexed[replica, option] = prefix
                model_work.update(prefix["model_work"])
                planning_counts.update(prefix["planning_counts"])
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
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0)}
        chosen, best = "H2", 0.0
        for option in OPTIONS[1:]:
            if option not in allowed:
                continue
            target = [fsum(indexed[replica, option]["completed"][component]
                - indexed[replica, "H2"]["completed"][component]
                for replica in range(self.replicas)) / self.replicas for component in range(3)]
            value = float(_utility(target, QUERIES[query]))
            predictions[option] = dict(target=target, value=value)
            if value > best:
                chosen, best = option, value
        self.last_prefixes = prefixes
        self.last_log = dict(replicas=self.replicas, trajectories=len(prefixes), model_work=dict(model_work),
            planning_counts=dict(planning_counts), value_counts=dict(value_counts), wiring=wiring,
            outcomes=dict(outcomes), seconds=perf_counter() - started)
        if work is not None:
            work["candidate_selector_decisions"] = work.get("candidate_selector_decisions", 0) + 1
            work["candidate_trajectories"] = work.get("candidate_trajectories", 0) + len(prefixes)
            for group in (model_work, planning_counts, value_counts):
                for name, value in group.items():
                    key = "candidate_" + name
                    work[key] = work.get(key, 0) + value
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"],
                    value=best, predictions=predictions)
