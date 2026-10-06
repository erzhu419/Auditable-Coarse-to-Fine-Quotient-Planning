"""Terminal fragment acquisition with a hard budget of actual transitions."""
from collections import Counter
from copy import deepcopy
import random
from time import perf_counter

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_lifelong_experience_v77 import run_episode
from acfqp.science.controlled_predictive_fragment_experience_v83 import _controller_record
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS,
)


def collect_source(life, episode, query, rule, env_seed, remaining, max_steps=2000):
    """Finish a new H2 source game within the available interaction budget."""
    if remaining < 0:
        raise ValueError("remaining transitions must be nonnegative")
    started = perf_counter()
    if remaining == 0:
        return None, None, dict(games=0, roots=0, ground_work={}, planning_counts={},
            outcomes={}, unused_budget=0, budget_exhausted=True, seconds=perf_counter() - started)
    model_seed = env_seed + 1_000_000
    controller = FragmentController(None, query, rule, random.Random(model_seed), mode="H2_ONLY")
    root = None

    def actor(board, step):
        nonlocal root
        if root is None and tuple(board).count(0) <= TRIGGER_EMPTY_CELLS:
            root = dict(board=list(board), query=query, episode=episode, step=step, source_seed=env_seed)
        return controller.choose(board, step)

    game = run_episode(env_seed, actor, max_steps=min(max_steps, remaining))
    unused = remaining - game["work"]["sampled_transitions"]
    raw = dict(lifecycle=life, query=query, episode=episode, env_seed=env_seed, model_seed=model_seed,
        game=game, controller=_controller_record(controller), planning_counts=dict(controller.work))
    log = dict(games=1, roots=int(root is not None), ground_work=game["work"],
        planning_counts=dict(controller.work), outcomes={game["status"]: 1},
        unused_budget=unused, budget_exhausted=unused == 0, seconds=perf_counter() - started)
    return root, raw, log


def sample_root(root, rule, env_seed_base, remaining, replicas=8, max_steps=2000):
    """Keep all sampled work; fit labels require a complete terminal block."""
    if remaining < 0 or replicas <= 0:
        raise ValueError("remaining must be nonnegative and replicas must be positive")
    started = perf_counter()
    ground_work, planning_counts, outcomes = Counter(), Counter(), Counter()
    games, raw = {}, []
    for replica in range(replicas):
        for option in OPTIONS:
            available = remaining - ground_work["sampled_transitions"]
            if available == 0:
                break
            env_seed = env_seed_base + replica
            model_seed = env_seed + 1_000_000_000_000
            controller = FragmentController(None, root["query"], rule, random.Random(model_seed),
                immediate=True, fixed_option=option)
            game = rollout_from_board(tuple(root["board"]), env_seed, controller.choose,
                                      max_steps=min(max_steps, available))
            games[replica, option] = game
            raw.append(dict(option=option, replica=replica, env_seed=env_seed, model_seed=model_seed,
                game=game, controller=_controller_record(controller), planning_counts=dict(controller.work)))
            ground_work.update(game["work"])
            planning_counts.update(controller.work)
            outcomes[game["status"]] += 1
        if ground_work["sampled_transitions"] == remaining:
            break
    complete = len(raw) == len(OPTIONS) * replicas and all(
        item["game"]["status"] in ("WON", "LOST") for item in raw)
    rows, pair_deltas = [], {}
    if complete:
        for option in OPTIONS[1:]:
            deltas = []
            for replica in range(replicas):
                candidate, reference = games[replica, option], games[replica, "H2"]
                deltas.append([(candidate["return_score"] - reference["return_score"]) / 2048,
                    float(candidate["status"] == "LOST") - float(reference["status"] == "LOST"),
                    float(candidate["status"] == "WON") - float(reference["status"] == "WON")])
            pair_deltas[option] = deltas
            rows.append(dict(board=list(root["board"]), query=root["query"], episode=root["episode"],
                option=option, target=[sum(delta[index] for delta in deltas) / replicas for index in range(3)]))
    unused = remaining - ground_work["sampled_transitions"]
    log = dict(roots=int(bool(raw)), rows=len(rows), trajectories=len(raw), complete_block=complete,
        censored_root=bool(raw) and not complete, ground_work=dict(ground_work),
        planning_counts=dict(planning_counts), outcomes=dict(outcomes), pair_deltas=pair_deltas,
        model_rng_streams=len(raw), model_uniform_draws=planning_counts.get("model_uniform_draws", 0),
        unused_budget=unused, budget_exhausted=unused == 0, seconds=perf_counter() - started)
    return rows, raw, log


def combine_rows(original_rows, extra_rows, original_replicas, extra_replicas):
    """Combine terminal paired means using their replica counts, without mutation."""
    key = lambda row: (row["query"], row["episode"], tuple(row["board"]), row["option"])
    original, extra = list(original_rows), {key(row): row for row in extra_rows}
    if (len(original) != 4 or len(extra) != 4 or {key(row) for row in original} != set(extra)
            or original_replicas <= 0 or extra_replicas <= 0):
        raise ValueError("weighted combination requires matching four-option roots and positive replica counts")
    total = original_replicas + extra_replicas
    combined = deepcopy(original)
    for row in combined:
        other = extra[key(row)]
        row["target"] = [(old * original_replicas + new * extra_replicas) / total
                         for old, new in zip(row["target"], other["target"])]
    return combined
