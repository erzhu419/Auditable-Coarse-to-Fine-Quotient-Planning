"""Measure reward-parametric H2 shapes using retained exact kernels only."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def encode(value):
    if isinstance(value, Fraction):
        return {"fraction": [value.numerator, value.denominator]}
    if isinstance(value, tuple):
        return [encode(item) for item in value]
    return value


def h2_semantics(payload, work):
    cells = {state: (h, status) for state, h, status in payload["cells"]}
    rows = defaultdict(dict)
    for state, action, entries in payload["rows"]:
        if cells[state][0] in (1, 2):
            rows[state][action] = tuple((Fraction(p, q), child, Fraction(r, s))
                                        for p, q, child, r, s in entries)
            work["retained_action_rows_decoded"] += 1
            work["retained_outcomes_decoded"] += len(entries)
    leaves = {}
    for state, (h, status) in cells.items():
        if h != 1:
            continue
        if status != "ACTIVE":
            leaves[state] = ("TERMINAL", status)
            continue
        actions = []
        for action, entries in sorted(rows[state].items()):
            rewards = {reward for _, _, reward in entries}
            if len(rewards) != 1:
                raise ValueError("retained H1 action has nonconstant reward")
            mass = defaultdict(Fraction)
            for p, child, _ in entries:
                if cells[child][0] != 0 or cells[child][1] == "ACTIVE":
                    raise ValueError("retained H1 kernel is not terminal")
                mass[cells[child][1]] += p
            actions.append((action, next(iter(rewards)), tuple(sorted(mass.items()))))
        leaves[state] = ("H1", tuple(actions))
        work["h1_semantic_states"] += 1
    result = {}
    for state, (h, status) in cells.items():
        if h != 2 or status != "ACTIVE":
            continue
        actions = []
        for action, entries in sorted(rows[state].items()):
            mass = defaultdict(Fraction)
            for p, child, reward in entries:
                mass[leaves[child], reward] += p
            actions.append((action, tuple((leaf, reward, p)
                           for (leaf, reward), p in sorted(mass.items()) if p)))
        result[state] = tuple(actions)
        work["h2_semantic_states"] += 1
    return result


def leaf_shape(leaf):
    if leaf[0] == "TERMINAL":
        return leaf
    return "H1", tuple((action, mass) for action, _, mass in leaf[1])


def parameterize(semantic):
    bindings, actions, child_slots = [], [], 0

    def parameter(value):
        index = len(bindings)
        bindings.append(value)
        return "PARAM", index

    for action, entries in semantic:
        rewards = {reward for _, reward, _ in entries}
        if len(rewards) != 1:
            raise ValueError("retained H2 action has nonconstant reward")
        reward_slot = parameter(next(iter(rewards)))
        outcomes = []
        # Reward values only break ties between identical shapes and masses.
        # Every tied outcome still gets its own child and parameter slots.
        ordered = sorted(entries, key=lambda row: (leaf_shape(row[0]), row[2], row[0]))
        for leaf, _, probability in ordered:
            if leaf[0] == "TERMINAL":
                child = leaf
            else:
                child = ("H1_SLOT", child_slots, tuple(
                    (name, parameter(reward), masses) for name, reward, masses in leaf[1]))
                child_slots += 1
            outcomes.append((child, probability))
        actions.append((action, reward_slot, tuple(outcomes)))
    return tuple(actions), tuple(bindings), child_slots


def restore(template, bindings):
    actions = []
    for action, reward_slot, outcomes in template:
        reward = bindings[reward_slot[1]]
        mass = defaultdict(Fraction)
        for child, probability in outcomes:
            leaf = child if child[0] == "TERMINAL" else ("H1", tuple(
                (name, bindings[slot[1]], probabilities) for name, slot, probabilities in child[2]))
            mass[leaf, reward] += probability
        actions.append((action, tuple((leaf, value, p)
                       for (leaf, value), p in sorted(mass.items()) if p)))
    return tuple(actions)


def diagnose(source):
    started = perf_counter()
    source = Path(source)
    work = Counter()

    def read(path):
        text = path.read_text()
        work["files_read"] += 1
        work["bytes_read"] += len(text.encode())
        return json.loads(text)

    roster = read(source / "roster.json")["target"]
    previous = read(source / "analysis.json")
    global_templates, global_exact, rows = set(), set(), []
    all_recovery, all_correspondence = True, True
    example = None
    for case in roster:
        full = h2_semantics(read(source / case["name"] / "FULL.model.json"), work)
        exact = h2_semantics(read(source / case["name"] / "COMPOSED.model.json"), work)
        exact_values = set(exact.values())
        corresponding = set(full.values()) == exact_values and len(exact_values) == len(exact)
        all_correspondence &= corresponding
        templates, case_parameters, case_slots, distinct_binding_collisions = {}, 0, 0, 0
        recovered = 0
        for state, semantic in full.items():
            template, bindings, slots = parameterize(semantic)
            correct = restore(template, bindings) == semantic
            recovered += int(correct)
            all_recovery &= correct
            case_parameters += len(bindings)
            case_slots += slots
            if template in templates and templates[template][1] != bindings:
                distinct_binding_collisions += 1
                if example is None:
                    first_state, first_bindings = templates[template]
                    example = dict(case=case["name"], full_states=[first_state, state],
                        template=encode(template), bindings=[encode(first_bindings), encode(bindings)],
                        both_recover_exact=correct and restore(template, first_bindings) == full[first_state],
                        independent_h1_outcome_slots=slots)
            else:
                templates.setdefault(template, (state, bindings))
        work["full_h2_instances"] += len(full)
        work["exact_h2_cells_within_case_total"] += len(exact)
        work["parametric_templates_within_case_total"] += len(templates)
        work["instances_recovered_exactly"] += recovered
        work["independent_reward_bindings"] += case_parameters
        work["independent_h1_outcome_slots"] += case_slots
        work["instances_with_binding_different_from_first_shape_instance"] += distinct_binding_collisions
        global_templates.update(templates)
        global_exact.update(exact_values)
        rows.append(dict(case=case["name"], full_h2_instances=len(full), exact_h2_cells=len(exact),
            parametric_templates=len(templates), instances_recovered_exactly=recovered,
            exact_kernel_correspondence=corresponding, reward_binding_slots=case_parameters,
            h1_outcome_slots=case_slots, shape_reuses_with_different_binding=distinct_binding_collisions))
    expected_full = previous["arms"]["FULL"]["by_horizon"]["2"]["concrete_active_states"]
    expected_exact = previous["arms"]["COMPOSED"]["by_horizon"]["2"]["candidate_active_cells"]
    complete = (len(roster) == 32 and len({c["name"] for c in roster}) == 32 and previous["complete"] and
                work["full_h2_instances"] == expected_full == 1500 and
                work["exact_h2_cells_within_case_total"] == expected_exact == 1380)
    work["parametric_templates_global"] = len(global_templates)
    work["exact_h2_semantics_global"] = len(global_exact)
    return dict(schema="acfqp.parametric_shape_diagnostic.v75", complete=complete,
        exact_recovery=complete and all_recovery, exact_kernel_correspondence=complete and all_correspondence,
        source_path=str(source), counts=dict(work), cases=rows,
        first_shape_with_different_binding=example,
        ground_calls=0, fit_calls=0, construction_calls=0, planning_calls=0,
        scope="Exploratory structure diagnostic on retained H2 kernels. Each H2 action reward and each H1 outcome-slot action reward is an independent parameter. Distinct exact H1 bindings remain distinct outcome slots even when their reward-free shapes match. Repeated children across H2 actions have independent slots; no cross-slot equality constraint is learned. Templates are canonically ordered without retained cell IDs. This measures shape reuse plus exact reconstruction of observed bindings, not learned or generative strategic transfer.",
        elapsed_seconds_before_write=perf_counter() - started)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "reports/controlled_predictive_composition_v69")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/controlled_predictive_parametric_v75.shape_diagnostic.json")
    args = parser.parse_args()
    result = diagnose(args.source)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "exact_recovery", "exact_kernel_correspondence", "counts")}, indent=2))
