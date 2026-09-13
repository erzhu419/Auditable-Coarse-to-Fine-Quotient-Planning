"""Prepare tie-aware source decisions from retained kernels and saved values."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import json
import math
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/controlled_predictive_composition_v69"
LABELS = ROOT / "reports/controlled_predictive_observation_v70"
QUERY_SOURCE = ROOT / "reports/controlled_predictive_effect_v74"
TRAIN_QUERIES = ("risk_0", "risk_0_05", "risk_0_2", "risk_1", "risk_5", "goal_1_risk_1")
ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT")
OPTIMAL_TOLERANCE = 1e-12


def prepare():
    """Return board-deduplicated data plus original occurrence-weighted labels.

    Saved source child values supply continuation. This computes action-Q
    teacher labels without running a planner, dynamics model, or ground kernel.
    Only the six declared query labels enter the returned training data.
    """
    started = perf_counter()
    work = Counter()

    def read(path):
        tick = perf_counter()
        text = path.read_text()
        result = json.loads(text)
        work["read_seconds"] += perf_counter() - tick
        work["files_read"] += 1
        work["bytes_read"] += len(text.encode())
        return result

    cases = read(SOURCE / "roster.json")["target"]
    query_definitions = read(QUERY_SOURCE / cases[0]["name"] / "inputs.json")["queries"]
    queries = {name: query_definitions[name] for name in TRAIN_QUERIES}
    boards, occurrences, board_ids = [], [], {}
    occurrences_by_case, occurrences_by_board = Counter(), Counter()
    max_residual = 0.0
    for case in cases:
        name = case["name"]
        occurrences_by_case[name] += 0
        kernel = read(SOURCE / name / "COMPOSED.model.json")
        saved_plans = read(SOURCE / name / "COMPOSED.plans.json")
        retained_labels = read(LABELS / name / "COMPOSED_MAP.package.json")["router"]["labels"]
        cells = {state: (h, status) for state, h, status in kernel["cells"]}
        rows = defaultdict(dict)
        for state, action, entries in kernel["rows"]:
            if cells[state] != (2, "ACTIVE"):
                continue
            rows[state][action] = tuple((Fraction(p, q), child, Fraction(r, s))
                                        for p, q, child, r, s in entries)
            work["source_h2_action_rows_decoded"] += 1
            work["source_h2_outcomes_decoded"] += len(entries)
        teachers = {}
        for h, board, state in retained_labels:
            if h != 2:
                continue
            if cells.get(state) != (2, "ACTIVE"):
                raise ValueError(f"{name}: retained H2 label does not name an active source cell")
            physical = tuple(board)
            if physical not in board_ids:
                board_id = len(boards)
                board_ids[physical] = board_id
                boards.append(dict(board_id=board_id, board=list(physical), horizon=2))
            board_id = board_ids[physical]
            legal = sorted(rows[state])
            if state not in teachers:
                teacher_rows = []
                for query_name in TRAIN_QUERIES:
                    query = queries[query_name]
                    plan = saved_plans[query_name]
                    values = plan["values"]
                    q_values = {}
                    for action in legal:
                        outcomes = rows[state][action]
                        # Keep V1 planner's Fraction/float operation and row order.
                        q_values[action] = math.fsum(
                            p * (query["reward_weight"] * reward + values[str(child)])
                            for p, child, reward in outcomes)
                        work["teacher_q_action_evaluations"] += 1
                        work["teacher_q_outcome_terms"] += len(outcomes)
                    best = max(q_values.values())
                    residual = abs(best - values[str(state)])
                    max_residual = max(max_residual, residual)
                    if residual > OPTIMAL_TOLERANCE:
                        raise ValueError(f"{name}: reconstructed {query_name} Q differs from its saved value")
                    optimal = [action for action in legal
                               if best - q_values[action] <= OPTIMAL_TOLERANCE]
                    chosen = plan["policy"][str(state)]
                    if chosen not in optimal:
                        raise ValueError(f"{name}: saved action is outside the source optimal membership")
                    teacher_rows.append(dict(query_name=query_name, best_q=best,
                        stored_action=chosen, optimal_actions=optimal,
                        actions=[dict(action=action, optimal=action in optimal,
                                      q_value=q_values[action], regret=best - q_values[action])
                                 for action in legal]))
                    work["teacher_state_query_rows"] += 1
                teachers[state] = teacher_rows
            else:
                work["teacher_cell_reuses"] += 1
            query_rows = teachers[state]
            excluded = [action for action in ACTION_ORDER if action not in legal]
            occurrences.append(dict(board_id=board_id, case=name, state=state,
                legal_actions=legal, excluded_illegal_actions=excluded, query_rows=query_rows))
            occurrences_by_case[name] += 1
            occurrences_by_board[board_id] += 1
            work["case_occurrences"] += 1
            work["training_state_query_occurrences"] += len(query_rows)
            work["training_action_occurrences"] += len(query_rows) * len(legal)
            work["excluded_illegal_action_query_occurrences"] += len(query_rows) * len(excluded)
            work["optimal_action_occurrences"] += sum(len(row["optimal_actions"]) for row in query_rows)
            work["tied_state_query_occurrences"] += sum(len(row["optimal_actions"]) > 1 for row in query_rows)
        work["source_cases"] += 1
    if work["source_cases"] != 32 or work["case_occurrences"] != 1500:
        raise ValueError("source preparation did not cover the frozen 32 cases and 1500 H2 occurrences")
    work["physical_unique_boards"] = len(boards)
    work["source_cases_with_h2"] = sum(value > 0 for value in occurrences_by_case.values())
    work["cross_occurrence_repeated_boards"] = work["case_occurrences"] - len(boards)
    work["maximum_source_value_residual"] = max_residual
    counts = dict(work)
    counts.update(occurrences_by_case=dict(occurrences_by_case),
                  occurrences_by_board={str(key): value for key, value in occurrences_by_board.items()},
                  ground_calls=0, fit_calls=0, new_planning_calls=0)
    data = dict(schema="acfqp.decision_source.v76", queries=queries,
        untrained_query_names=[name for name in query_definitions if name not in TRAIN_QUERIES],
        boards=boards, occurrences=occurrences, optimal_tolerance=OPTIMAL_TOLERANCE,
        source_scope="Previously exposed V69 H2 observations are training source in V76. Physical boards are stored once for feature extraction; each original case occurrence, query, and legal action retains unit training weight. All actions within 1e-12 of maximum Q are optimal, including ties. Q uses exact retained probabilities/rewards and saved continuation values. The eight other query labels are not extracted, and target observations are never read.")
    counts["prepare_seconds"] = perf_counter() - started
    return data, counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data, counts = prepare()
    args.output.write_text(json.dumps(dict(data=data, counts=counts), allow_nan=False) + "\n")
    print(json.dumps(counts, indent=2))
