"""Fresh H2 trigger states and paired, committed fragment consequences."""
from collections import Counter
import random
from time import perf_counter

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_lifelong_experience_v77 import run_episode
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS,
)


def _controller_record(controller):
    return dict(events=controller.events, fragment_actions=controller.fragment_actions,
        initiation_step=controller.initiation_step, selected_option=controller.selected_option,
        remaining_actions=controller.remaining_actions,
        finished_fragment=controller.finished_fragment)


def collect_source(life, episode, query, rule, max_steps=2000):
    """Retain the first deployment-trigger board, while finishing its H2 game."""
    started = perf_counter()
    env_seed = 8_300_000 + life * 10_000 + episode
    model_seed = env_seed + 1_000_000
    controller = FragmentController(None, query, rule, random.Random(model_seed), mode="H2_ONLY")
    root = None

    def actor(board, step):
        nonlocal root
        if root is None and tuple(board).count(0) <= TRIGGER_EMPTY_CELLS:
            root = dict(board=list(board), query=query, episode=episode, step=step,
                        source_seed=env_seed)
        return controller.choose(board, step)

    game = run_episode(env_seed, actor, max_steps=max_steps)
    raw = dict(query=query, episode=episode, env_seed=env_seed, model_seed=model_seed,
        game=game, controller=_controller_record(controller), planning_counts=dict(controller.work))
    log = dict(games=1, roots=int(root is not None), ground_work=game["work"],
        planning_counts=dict(controller.work), outcomes={game["status"]: 1},
        seconds=perf_counter() - started)
    return root, raw, log


def sample_root(root, rule, life, replicas=8, max_steps=2000):
    """Pair full option returns against H2, averaging within root before fitting.

    Every option acts normally at the root. The controller commits to its fixed
    fragment and then permanently returns to H2, consuming four model uniforms
    per active step in every arm. A cutoff censors the whole root's labels.
    """
    started = perf_counter()
    query = root["query"]
    query_index = tuple(QUERIES).index(query)
    ground_work, planning_counts, outcomes = Counter(), Counter(), Counter()
    games, raw = {}, []
    for replica in range(replicas):
        env_seed = (8_310_000_000 + life * 10_000_000 + query_index * 100_000
                    + root["episode"] * 100 + replica)
        model_seed = env_seed + 1_000_000_000_000
        for option in OPTIONS:
            controller = FragmentController(None, query, rule, random.Random(model_seed),
                immediate=True, fixed_option=option)
            game = rollout_from_board(tuple(root["board"]), env_seed,
                controller.choose, max_steps=max_steps)
            games[replica, option] = game
            raw.append(dict(option=option, replica=replica, env_seed=env_seed,
                model_seed=model_seed, game=game, controller=_controller_record(controller),
                planning_counts=dict(controller.work)))
            ground_work.update(game["work"])
            planning_counts.update(controller.work)
            outcomes[game["status"]] += 1
    censored = bool(outcomes["CUTOFF"])
    rows, pair_deltas = [], {}
    if not censored:
        for option in OPTIONS[1:]:
            deltas = []
            for replica in range(replicas):
                candidate, reference = games[replica, option], games[replica, "H2"]
                deltas.append([
                    (candidate["return_score"] - reference["return_score"]) / 2048,
                    float(candidate["status"] == "LOST") - float(reference["status"] == "LOST"),
                    float(candidate["status"] == "WON") - float(reference["status"] == "WON"),
                ])
            pair_deltas[option] = deltas
            rows.append(dict(board=list(root["board"]), query=query, option=option,
                target=[sum(delta[index] for delta in deltas) / replicas for index in range(3)],
                episode=root["episode"]))
    log = dict(roots=1, rows=len(rows), trajectories=len(raw), censored_root=censored,
        ground_work=dict(ground_work), planning_counts=dict(planning_counts),
        outcomes=dict(outcomes), pair_deltas=pair_deltas,
        model_rng_streams=len(raw), model_uniform_draws=planning_counts.get("model_uniform_draws", 0),
        seconds=perf_counter() - started)
    return rows, raw, log
