"""Independent short-prefix prediction plus terminal paired residual correction."""
from collections import Counter
import random
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_data_v91 import extract_prefix, _key
from acfqp.science.controlled_predictive_decision_experience_v78 import rollout_from_board
from acfqp.science.controlled_predictive_fragment_experience_v83 import _controller_record
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, OPTIONS, QUERIES, _utility
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector


METHODS = ("MC", "PAIR_ONLY", "CORRECTED")


def compose_pair(candidate_prefix, reference_prefix, model, query, work=None):
    """Use one shared model for the pair's remaining consequences after action four."""
    candidate, reference = candidate_prefix, reference_prefix
    if any(prefix["status"] not in ("ACTIVE", "WON", "LOST") for prefix in (candidate, reference)):
        raise ValueError("an incomplete prefix cannot supply a paired prediction")
    direct = [c - r for c, r in zip(candidate["direct"], reference["direct"])]
    cactive, ractive = candidate["status"] == "ACTIVE", reference["status"] == "ACTIVE"
    if not cactive and not ractive:
        return direct
    tail = model.predict_pair(candidate["boundary_board"], reference["boundary_board"],
                              cactive, ractive, query, work)
    return [observed + remaining for observed, remaining in zip(direct, tail)]


def collect_prefixes(root, rule, seed_base, replicas=64):
    """Sample four actual actions per option, retaining earlier terminal outcomes."""
    if replicas <= 0:
        raise ValueError("replicas must be positive")
    started = perf_counter()
    prefixes, raw = {option: [] for option in OPTIONS}, []
    ground, planning, outcomes = Counter(), Counter(), Counter()
    wiring = dict(environment_uniforms_aligned=True, model_uniforms_aligned=True,
                  single_initiations=True, committed_lengths_match=True)
    for replica in range(replicas):
        env_seed, model_seed = seed_base + replica, seed_base + replica + 1_000_000_000_000
        for option in OPTIONS:
            controller = FragmentController(None, root["query"], rule, random.Random(model_seed),
                                            immediate=True, fixed_option=option)
            paths = []

            def act(board, step):
                before = controller.fragment_actions
                action = controller.choose(board, step)
                paths.append("fragment" if controller.fragment_actions > before else "H2")
                return action

            game = rollout_from_board(tuple(root["board"]), env_seed, act, max_steps=4)
            row = dict(option=option, replica=replica, env_seed=env_seed, model_seed=model_seed,
                game=game, controller=_controller_record(controller), planning_counts=dict(controller.work),
                action_paths=paths)
            raw.append(row)
            prefix = extract_prefix(row)
            prefixes[option].append(prefix)
            steps = game["steps_count"]
            duration = 0 if option == "H2" else int(option.split("_")[1])
            expected = min(duration, steps)
            wiring["environment_uniforms_aligned"] &= game["work"]["environment_random_draws"] == 2 * steps
            wiring["model_uniforms_aligned"] &= controller.work["model_uniform_draws"] == 4 * steps
            wiring["single_initiations"] &= len(controller.events) == 1 and controller.initiation_step == 0
            wiring["committed_lengths_match"] &= (
                paths == ["fragment"] * expected + ["H2"] * (steps - expected)
                and controller.fragment_actions == expected)
            ground.update(game["work"])
            planning.update(controller.work)
            outcomes[prefix["status"]] += 1
    return prefixes, raw, dict(requested_replicas=replicas, trajectories=len(raw),
        ground_work=dict(ground), planning_counts=dict(planning), outcomes=dict(outcomes),
        wiring=wiring, seconds=perf_counter() - started)


def _index(prefixes, full_replicas=None):
    indexed = {}
    for option in OPTIONS:
        selected = [prefix for prefix in prefixes[option]
                    if full_replicas is None or prefix["replica"] < full_replicas]
        indexed[option] = {prefix["replica"]: prefix for prefix in selected}
        if len(indexed[option]) != len(selected):
            raise ValueError("duplicate option prefix replica")
    replicas = sorted(indexed["H2"])
    if not replicas or any(set(indexed[option]) != set(replicas) for option in OPTIONS):
        raise ValueError("paired options require matching nonempty replica rosters")
    if full_replicas is not None and replicas != list(range(full_replicas)):
        raise ValueError("requested terminal replica prefix is incomplete")
    return indexed, replicas


def _variance(values, query):
    utilities = [_utility(value, QUERIES[query]) for value in values]
    return float(np.var(utilities, ddof=1)) if len(utilities) > 1 else None


def estimate_root(root, independent_prefixes, model, work=None, full_replicas=None):
    """Correct prediction bias with terminal residuals on a distinct sample set.

    The caller supplies independent short-prefix streams. The variance expression
    has both independent mean terms; it is conditional on the frozen model.
    """
    if root["censored"]:
        return dict(complete=False, estimates={}, details={})
    full, n_replicas = _index(root["prefixes"], full_replicas)
    short, m_replicas = _index(independent_prefixes)
    if any(prefix["full_target"] is None for option in OPTIONS for prefix in full[option].values()):
        return dict(complete=False, estimates={}, details={})
    query = root["query"]
    estimates = {method: {} for method in METHODS}
    details = {}
    for option in OPTIONS[1:]:
        y = [[c - r for c, r in zip(full[option][replica]["full_target"],
                                   full["H2"][replica]["full_target"])] for replica in n_replicas]
        zn = [compose_pair(full[option][replica], full["H2"][replica], model, query, work)
              for replica in n_replicas]
        zm = [compose_pair(short[option][replica], short["H2"][replica], model, query, work)
              for replica in m_replicas]
        residuals = (np.asarray(y) - np.asarray(zn)).tolist()
        estimates["MC"][option] = np.mean(y, axis=0).tolist()
        estimates["PAIR_ONLY"][option] = np.mean(zm, axis=0).tolist()
        estimates["CORRECTED"][option] = (np.mean(zm, axis=0) + np.mean(residuals, axis=0)).tolist()
        vy, vz, vr = (_variance(values, query) for values in (y, zm, residuals))
        details[option] = dict(full_targets=y, full_predictions=zn, short_predictions=zm,
            paired_residuals=residuals, full_replicas=n_replicas, short_replicas=m_replicas,
            mc_sample_variance=vy, short_sample_variance=vz, residual_sample_variance=vr,
            mc_variance_of_mean=None if vy is None else vy / len(y),
            corrected_variance_of_mean=(None if vz is None or vr is None
                                       else vz / len(zm) + vr / len(residuals)))
    return dict(complete=True, estimates=estimates, details=details)


def fit_selectors(roots, prefix_by_key, models, checkpoint):
    """Fit identical V84 heads using MC, prediction-only, or corrected root labels."""
    started = perf_counter()
    for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
        model = models[name]
        if model.checkpoint != checkpoint or model.excluded_fold != fold:
            raise ValueError("paired model checkpoint or excluded fold differs from label construction")
        if any(episode >= checkpoint or episode % 5 == 4
               or (fold is not None and episode % 2 == fold)
               for roster in model.training_episodes.values() for episode in roster):
            raise ValueError("paired model training episodes violate checkpoint or fold isolation")
    records = list(roots)
    rows, root_estimates, counts = {method: [] for method in METHODS}, [], Counter()
    label_start = perf_counter()
    for root in records:
        episode = root["episode"]
        if episode >= checkpoint or root["censored"]:
            continue
        model_name = "full" if episode % 5 == 4 else f"fold_{episode % 2}"
        model = models[model_name]
        if episode % 5 != 4 and any(episode in roster for roster in model.training_episodes.values()):
            raise ValueError("source episode entered its own paired continuation model")
        result = estimate_root(root, prefix_by_key[_key(root)], model, counts)
        root_estimates.append(dict(board=list(root["board"]), query=root["query"], episode=episode,
                                   continuation_model=model_name, **result))
        if not result["complete"]:
            continue
        for method in METHODS:
            for option in OPTIONS[1:]:
                rows[method].append(dict(board=list(root["board"]), query=root["query"],
                    episode=episode, option=option, target=result["estimates"][method][option]))
        counts["estimated_roots"] += 1
    label_seconds = perf_counter() - label_start
    selectors, head_fits = {}, {}
    for method in METHODS:
        selectors[method], head_fits[method] = JointSelector.fit(rows[method], checkpoint)
        counts.update(head_fits[method]["counts"])
    return selectors, rows, dict(checkpoint=checkpoint, input_roots=len(records),
        censored_roots_excluded=sum(root["episode"] < checkpoint and root["censored"] for root in records),
        future_roots_excluded=sum(root["episode"] >= checkpoint for root in records),
        root_estimates=root_estimates, head_fits=head_fits, counts=dict(counts),
        oof_episode_isolation=True, label_seconds=label_seconds, seconds=perf_counter() - started)
