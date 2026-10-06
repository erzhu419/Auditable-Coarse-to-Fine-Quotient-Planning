"""Fresh fixed-option versus H2 suffixes for frozen V89 leaf members."""
from collections import Counter
import random
from time import perf_counter

from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_fragment_experience_v83 import _controller_record
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, OPTIONS


def sample_pair_root(root, rule, seed_base, replicas=64, max_steps=2000):
    """Retain every trajectory; only terminal pairs receive R/F/S differences.

    The cohort fixes the option before this function sees any new outcomes.
    Replica count is fixed too: a cutoff or an apparent advantage never stops
    later replicas. Both arms receive the same environment and model streams.
    """
    if root["option"] not in OPTIONS[1:]:
        raise ValueError("paired replay requires a frozen non-H2 option")
    if replicas <= 0 or max_steps <= 0:
        raise ValueError("replicas and max_steps must be positive")
    started = perf_counter()
    raw, pairs = [], []
    ground_work, planning_counts, outcomes = Counter(), Counter(), Counter()
    wiring = dict(model_uniforms_aligned=True, single_initiations=True,
                  committed_lengths_match=True)
    option = root["option"]
    for replica in range(replicas):
        env_seed = seed_base + replica
        model_seed = env_seed + 1_000_000_000_000
        order = ("H2", option) if replica % 2 == 0 else (option, "H2")
        games = {}
        for selected in order:
            controller = FragmentController(None, root["query"], rule,
                random.Random(model_seed), immediate=True, fixed_option=selected)
            action_paths = []

            def act(board, step):
                before = controller.fragment_actions
                action = controller.choose(board, step)
                action_paths.append("fragment" if controller.fragment_actions > before else "H2")
                return action

            game = rollout_from_board(tuple(root["board"]), env_seed, act, max_steps=max_steps)
            games[selected] = game
            steps = game["steps_count"]
            duration = 0 if selected == "H2" else int(selected.split("_")[1])
            expected = min(duration, steps)
            wiring["committed_lengths_match"] &= (
                action_paths == ["fragment"] * expected + ["H2"] * (steps - expected)
                and controller.fragment_actions == expected)
            wiring["single_initiations"] &= (
                len(controller.events) == 1 and controller.initiation_step == 0
                and controller.selected_option == selected)
            wiring["model_uniforms_aligned"] &= controller.work["model_uniform_draws"] == 4 * steps
            raw.append(dict(root_id=root["id"], replica=replica, option=selected,
                env_seed=env_seed, model_seed=model_seed, game=game,
                controller=_controller_record(controller),
                planning_counts=dict(controller.work), action_paths=action_paths))
            ground_work.update(game["work"])
            planning_counts.update(controller.work)
            outcomes[game["status"]] += 1
        candidate, reference = games[option], games["H2"]
        complete = all(game["status"] in ("WON", "LOST") for game in games.values())
        target = None
        if complete:
            target = [
                (candidate["return_score"] - reference["return_score"]) / 2048,
                float(candidate["status"] == "LOST") - float(reference["status"] == "LOST"),
                float(candidate["status"] == "WON") - float(reference["status"] == "WON"),
            ]
        pairs.append(dict(replica=replica, seed=env_seed, complete_pair=complete,
            target=target, candidate_status=candidate["status"], reference_status=reference["status"]))
    log = dict(root_id=root["id"], requested_replicas=replicas,
        complete_pairs=sum(pair["complete_pair"] for pair in pairs), pairs=pairs,
        ground_work=dict(ground_work), planning_counts=dict(planning_counts),
        outcomes=dict(outcomes), trajectories=len(raw), wiring=wiring,
        seconds=perf_counter() - started)
    return raw, log
