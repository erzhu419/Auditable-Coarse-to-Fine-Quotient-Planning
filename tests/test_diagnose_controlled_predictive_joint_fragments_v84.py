"""Synthetic retained means distinguish ties, ordering and duration choices."""
from collections import Counter
import importlib.util
from pathlib import Path

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("joint_fragment_diagnosis_v84",
    ROOT / "scripts/diagnose_controlled_predictive_joint_fragments_v84.py")
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class SyntheticSelector:
    def __init__(self, old=False):
        self.old = old

    def select(self, board, query, allowed=None, work=None):
        work["synthetic_selector_calls"] += 1
        values = ([4, 3, 2, 2] if board[0] == 1 else [4, 3, 6, 5])
        if self.old:
            values = [1] * 4
        full = dict(H2=dict(target=[0, 0, 0], value=0))
        full.update({option: dict(target=[value, 0, 0], value=value)
                     for option, value in zip(OPTIONS[1:], values)})
        predictions = {option: full[option] for option in OPTIONS
                       if allowed is None or option in allowed}
        chosen, best = "H2", 0
        for option, prediction in predictions.items():
            if prediction["value"] > best:
                chosen, best = option, prediction["value"]
        return dict(option=chosen, value=best, predicted_advantage=predictions[chosen]["target"],
                    predictions=predictions)


def test_ordering_ties_duration_restriction_and_observed_targets():
    rows = [dict(query="reward", episode=episode, board=[rank] + [0] * 15,
                 option=option, target=[value, 0, 0])
            for episode, rank, observed in ((0, 1, (4, 3, 2, 2)), (4, 2, (-1, -2, -3, -3)))
            for option, value in zip(OPTIONS[1:], observed)]
    counts = Counter()
    summaries, witnesses = diagnosis.diagnose_rows(rows, SyntheticSelector(),
        SyntheticSelector(old=True), 99, 6, counts)
    train = next(row for row in summaries if row["query"] == "reward" and row["split"] == "training")
    held = next(row for row in summaries if row["query"] == "reward" and row["split"] == "heldout")
    assert train["roots"] == held["roots"] == 1
    ranking = train["methods"]["JOINT"]["candidate_ranking"]
    assert ranking["pairs"] == 6 and ranking["strict_observed_pairs"] == 5
    assert ranking["observed_ties"] == ranking["observed_ties_also_predicted_tied"] == 1
    assert ranking["concordant"] == 5 and ranking["observed_strict_order_accuracy"] == 1
    duration = train["methods"]["JOINT"]["same_primitive_duration_ranking"]
    assert duration["pairs"] == duration["concordant"] == 2
    old = train["methods"]["OLD"]
    assert old["candidate_ranking"]["predicted_ties_on_strict_observed_pairs"] == 5
    assert old["candidate_ranking"]["observed_strict_order_accuracy"] == 0
    assert old["identical_alternative_prediction_roots"] == old["positive_top_score_tie_roots"] == 1
    assert held["methods"]["JOINT"]["selected_options"] == {"SPACE_4": 1}
    assert held["methods"]["JOINT"]["selected_durations"] == {4: 1}
    assert held["methods"]["JOINT_ONE_STEP"]["selected_options"] == {"SPACE_1": 1}
    assert held["methods"]["JOINT_ONE_STEP"]["selected_durations"] == {1: 1}
    assert held["methods"]["JOINT"]["predicted_selected_utility_mean"] == 6
    assert held["methods"]["JOINT"]["observed_selected_utility_mean"] == -3
    assert held["methods"]["JOINT"]["negative_interventions"] == 1
    assert held["methods"]["JOINT_ONE_STEP"]["observed_selected_utility_mean"] == -1
    witness = next(row for row in witnesses if row["episode"] == 4)
    assert witness["retained_mean_targets"]["H2"] == [0, 0, 0]
    assert witness["retained_mean_targets"]["SNAKE_4"] == [-3, 0, 0]
    assert witness["methods"]["JOINT_ONE_STEP"]["candidate_pairs"] == witness["methods"]["JOINT"]["candidate_pairs"]
    pair = witness["methods"]["JOINT"]["candidate_pairs"][1]
    assert (pair["left"], pair["right"]) == ("SPACE_1", "SPACE_4")
    assert pair["observed_mean_utility_difference"] == 2 and pair["predicted_utility_difference"] == -2
    assert pair["same_primitive_duration_pair"] and pair["relation"] == "discordant"
    assert counts == dict(retained_option_rows_read=8, synthetic_selector_calls=6)
