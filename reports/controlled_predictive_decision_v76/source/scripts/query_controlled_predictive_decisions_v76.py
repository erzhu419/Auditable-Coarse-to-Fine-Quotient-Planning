"""Run frozen V76 decision methods without training libraries or ground dynamics."""
from collections import Counter
from fractions import Fraction
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("EXACT", "GREEDY", "RULE", "SELECTIVE")
WORK_PHASES = ("features", "root_predictions", "root_dynamics", "root_dp",
               "h1_dynamics", "h1_dp", "fallback")


def _module(path, name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def encode(value):
    """JSON representation with an explicit, reversible Fraction tag."""
    if isinstance(value, Fraction):
        return {"fraction": [value.numerator, value.denominator]}
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"fraction"}:
            return Fraction(*value["fraction"])
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return tuple(decode(item) for item in value)
    return value


def canonical_h1(contract):
    return tuple(sorted((action, score, tuple(sorted(masses)))
                        for action, score, masses in contract))


def _weights(query):
    return tuple(Fraction(str(query.get(name, default))) for name, default in
                 (("reward_weight", 1), ("failure_penalty", 0), ("goal_bonus", 0)))


def _metrics(reward, failure, success, query):
    reward, failure, success = map(Fraction, (reward, failure, success))
    rw, fp, gb = _weights(query)
    return dict(value=rw * reward - fp * failure + gb * success,
                reward=reward, failure=failure, success=success)


def _terminal(status, query, work):
    work["terminal_metric_evaluations"] += 1
    return _metrics(0, int(status == "LOST"), int(status == "WON"), query)


def _best(action_values):
    # Sorted action names decide every exact utility tie.
    return min(action_values, key=lambda action: (-action_values[action]["value"], action))


def choose_h1(contract, query, work=None, *, terminal_status="CUTOFF"):
    """Solve a complete analytic H1 contract, retaining all action metrics.

    Empty contracts need the observed terminal status; there is no action at a
    terminal observation. The optional Counter charges only this evaluation.
    """
    if work is None:
        work = Counter()
    work["h1_queries"] += 1
    if not contract:
        return dict(action=None, action_values={},
                    metrics=_terminal(terminal_status, query, work))
    action_values = {}
    for action, score, masses in contract:
        work["h1_action_rows"] += 1
        failure = success = Fraction()
        for status, probability in masses:
            work["h1_terminal_probability_combinations"] += 1
            failure += probability * int(status == "LOST")
            success += probability * int(status == "WON")
        action_values[action] = _metrics(Fraction(score, 2048), failure, success, query)
    action = _best(action_values)
    return dict(action=action, action_values=action_values, metrics=action_values[action])


def h2_metrics(native, query, work=None):
    """Solve native H2 joint rows with complete binding-sensitive H1 keys."""
    if work is None:
        work = Counter()
    work["h2_queries"] += 1
    if native and native[0] == "TERMINAL":
        return dict(action=None, action_values={}, continuations=[],
                    metrics=_terminal(native[1], query, work))
    cache, action_values = {}, {}
    for action, outcomes in native:
        work["h2_action_rows"] += 1
        reward = failure = success = Fraction()
        for child, incoming_reward, probability in outcomes:
            work["h2_probability_combinations"] += 1
            if child[0] == "TERMINAL":
                metrics = _terminal(child[1], query, work)
            else:
                contract = child[1]
                if contract in cache:
                    work["h1_contract_cache_hits"] += 1
                else:
                    work["h1_contract_cache_misses"] += 1
                    cache[contract] = choose_h1(contract, query, work)
                metrics = cache[contract]["metrics"]
            reward += probability * (incoming_reward + metrics["reward"])
            failure += probability * metrics["failure"]
            success += probability * metrics["success"]
        action_values[action] = _metrics(reward, failure, success, query)
    action = _best(action_values)
    continuations = [dict(contract=contract, action=solution["action"])
                     for contract, solution in sorted(cache.items())]
    return dict(action=action, action_values=action_values,
                metrics=action_values[action], continuations=continuations)


def _h1_observation(board, rule, effect, work):
    compiler = effect._compiler(rule)
    contract = canonical_h1(compiler.observation_contract(tuple(board)))
    work.update(compiler.work)
    status = "ACTIVE"
    if not contract:
        status, _ = rule.classify(tuple(board), work)
    return contract, status


def _case(method, case, queries, rule, predictor, model, effect):
    started = perf_counter()
    work = {name: Counter() for name in WORK_PHASES}
    times = dict(features=0.0, root_predictions=0.0, root_construction=0.0,
                 root_planning=0.0, h1_construction=0.0, h1_planning=0.0)
    actions, continuations, root_values = {}, {}, {}
    native, action_features, greedy_contract, greedy_status = None, None, None, None
    if method in {"RULE", "SELECTIVE"}:
        tick = perf_counter()
        action_features = predictor.features(case["board"], rule, work["features"])
        times["features"] = perf_counter() - tick
    elif method == "EXACT":
        tick = perf_counter()
        native = effect.semantic_h2(case["board"], rule, work=work["root_dynamics"],
                                    share_successors=True)
        times["root_construction"] += perf_counter() - tick
    else:
        tick = perf_counter()
        greedy_contract, greedy_status = _h1_observation(
            case["board"], rule, effect, work["root_dynamics"])
        times["root_construction"] += perf_counter() - tick

    for name, query in queries.items():
        confidence = margin = None
        fallback = False
        if method in {"RULE", "SELECTIVE"}:
            tick = perf_counter()
            scores = predictor.score_actions(model, action_features, query, work["root_predictions"])
            work["root_predictions"]["query_feature_vectors"] += len(action_features)
            work["root_predictions"]["query_action_scores"] += len(scores)
            ranked = sorted(scores, key=lambda action: (-scores[action], action))
            action = ranked[0] if ranked else None
            if ranked:
                confidence = scores[action]
                margin = confidence - scores[ranked[1]] if len(ranked) > 1 else 1.0
            times["root_predictions"] += perf_counter() - tick
            if method == "SELECTIVE" and ranked:
                work["fallback"]["threshold_decisions"] += 1
                fallback = confidence < 0.9 or margin < 0.2
                if fallback:
                    work["fallback"]["fallback_queries"] += 1
                    if native is None:
                        tick = perf_counter()
                        native = effect.semantic_h2(case["board"], rule,
                            work=work["root_dynamics"], share_successors=True)
                        times["root_construction"] += perf_counter() - tick
                        work["fallback"]["fallback_case_builds"] += 1
                    tick = perf_counter()
                    action = h2_metrics(native, query, work["root_dp"])["action"]
                    times["root_planning"] += perf_counter() - tick
                else:
                    work["fallback"]["accepted_rule_queries"] += 1
        elif method == "EXACT":
            tick = perf_counter()
            solution = h2_metrics(native, query, work["root_dp"])
            action = solution["action"]
            continuations[name] = solution["continuations"]
            root_values[name] = solution["action_values"]
            times["root_planning"] += perf_counter() - tick
        else:
            tick = perf_counter()
            action = choose_h1(greedy_contract, query, work["root_dp"],
                               terminal_status=greedy_status)["action"]
            times["root_planning"] += perf_counter() - tick
        actions[name] = dict(action=action, fallback=fallback,
                             confidence=confidence, margin=margin)

    # A fresh compiler makes the common observed H1 step identical in all arms.
    tick = perf_counter()
    h1_contract, h1_status = _h1_observation(case["h1_observation"], rule, effect, work["h1_dynamics"])
    times["h1_construction"] = perf_counter() - tick
    h1_actions = {}
    tick = perf_counter()
    for name, query in queries.items():
        solution = choose_h1(h1_contract, query, work["h1_dp"], terminal_status=h1_status)
        h1_actions[name] = dict(action=solution["action"], metrics=solution["metrics"])
    times["h1_planning"] = perf_counter() - tick
    result = dict(name=case["name"], actions=actions, h1_actions=h1_actions,
                  work={name: dict(counts) for name, counts in work.items()}, times=times)
    if method == "EXACT":
        result.update(exact_contract=native, continuations=continuations, root_values=root_values)
    result["case_total"] = perf_counter() - started
    return result


def run(method, inputs_path, rule_path, model_path, output):
    started = perf_counter()
    data = json.loads(inputs_path.read_text())
    rule_payload = json.loads(rule_path.read_text())
    dynamics = _module(ROOT / "src/acfqp/science/controlled_predictive_relational_dynamics_v69.py",
                       "acfqp_v76_worker_dynamics")
    effect = _module(ROOT / "scripts/query_controlled_predictive_effect_v74.py",
                     "acfqp_v76_worker_effect")
    rule = dynamics.LearnedDynamics.from_payload(rule_payload)
    predictor = model = None
    if method in {"RULE", "SELECTIVE"}:
        if model_path is None:
            raise ValueError("RULE and SELECTIVE require --model")
        model = json.loads(model_path.read_text())
        predictor = _module(ROOT / "src/acfqp/science/controlled_predictive_decision_rule_v76.py",
                            "acfqp_v76_worker_predictor")
    load_seconds = perf_counter() - started
    tick = perf_counter()
    cases = [_case(method, case, data["queries"], rule, predictor, model, effect)
             for case in data["cases"]]
    execution_seconds = perf_counter() - tick
    work = {name: Counter() for name in WORK_PHASES}
    for case in cases:
        for name, counts in case["work"].items():
            work[name].update(counts)
    counts = dict(case_count=len(cases), root_queries=len(cases) * len(data["queries"]),
        h1_queries=len(cases) * len(data["queries"]),
        root_action_decisions=sum(row["action"] is not None for case in cases for row in case["actions"].values()),
        root_no_action=sum(row["action"] is None for case in cases for row in case["actions"].values()),
        accepted_rule_queries=work["fallback"]["accepted_rule_queries"],
        fallback_queries=work["fallback"]["fallback_queries"],
        fallback_case_builds=work["fallback"]["fallback_case_builds"])
    ground = sorted(name for name in sys.modules if name.startswith("acfqp.domains"))
    forbidden = sorted(name for name in sys.modules
                       if name.split(".")[0] in {"sklearn", "numpy"})
    if ground or forbidden:
        raise AssertionError(f"forbidden inference imports: {ground + forbidden}")
    result = dict(schema="acfqp.decisions_worker.v76", method=method, cases=cases, counts=counts,
        work={name: dict(value) for name, value in work.items()},
        times=dict(load=load_seconds, execution=execution_seconds,
                   worker_seconds_before_write=perf_counter() - started),
        ground_imports=ground, forbidden_imports=forbidden)
    # Parent cold-process wall time includes encoding, output write and teardown.
    output.write_text(json.dumps(encode(result), allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--rule", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.method, args.inputs, args.rule, args.model, args.output)
