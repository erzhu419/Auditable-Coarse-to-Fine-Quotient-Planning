"""Learn positive, negative and unresolved paired fragment evidence by root.

The two-standard-error labels are operational training targets, not calibrated
confidence intervals. POINT and SUPPORTED use the same learned partitions and
root-weighted consequence means; only candidate eligibility differs.
"""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_joint_fragments_v84 import (
    OPTIONS, ONE_STEP_OPTIONS, QUERIES, FEATURE_NAMES, TREE_PARAMETERS,
    _array, _pack_roots, _merge, _utility,
)
from acfqp.science.controlled_predictive_lifelong_v77 import _apply


LABEL_MULTIPLIER = 2.0
SUPPORT_THRESHOLD = 0.5
LABEL_VALUES = (-1, 0, 1)
LABEL_NAMES = {-1: "negative", 0: "unresolved", 1: "positive"}
MODES = ("POINT", "SUPPORTED")


def paired_evidence(samples, query):
    """Summarize paired utility samples using their actual pooled replica count."""
    values = np.asarray(samples, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or len(values) < 2:
        raise ValueError("paired evidence requires at least two reward/failure/success samples")
    utilities = np.asarray([_utility(row, QUERIES[query]) for row in values], dtype=float)
    mean = float(utilities.mean())
    standard_error = float(utilities.std(ddof=1) / np.sqrt(len(utilities)))
    lower, upper = mean - LABEL_MULTIPLIER * standard_error, mean + LABEL_MULTIPLIER * standard_error
    label = 1 if lower > 0 else -1 if upper < 0 else 0
    return dict(n=len(values), mean_utility=mean, standard_error=standard_error,
                lower=lower, upper=upper, label=label, status=LABEL_NAMES[label])


def _key(root):
    return root["query"], root["episode"], tuple(root["board"])


def _label_counts(roots):
    counts = {option: Counter({name: 0 for name in LABEL_NAMES.values()}) for option in OPTIONS[1:]}
    for root in roots:
        for option in OPTIONS[1:]:
            counts[option][root["evidence"][option]["status"]] += 1
    return {option: dict(values) for option, values in counts.items()}


def reconstruct_roots(base_logs, extra_logs, mean_rows):
    """Pool complete raw blocks, checking against the retained V86 mean dataset."""
    started = perf_counter()
    grouped = {}
    counts = Counter(base_blocks_read=0, base_blocks_excluded=0,
                     extra_blocks_read=0, extra_blocks_excluded=0, extra_complete_blocks=0)

    def add(log, is_base):
        prefix = "base" if is_base else "extra"
        counts[prefix + "_blocks_read"] += 1
        complete = not log.get("censored_root", False) if is_base else log["complete_block"]
        if not complete:
            counts[prefix + "_blocks_excluded"] += 1
            return
        root, samples = log["root"], log["pair_deltas"]
        if set(samples) != set(OPTIONS[1:]):
            raise ValueError("a complete block must contain paired samples for all four options")
        sizes = {len(value) for value in samples.values()}
        if len(sizes) != 1 or next(iter(sizes)) < 2:
            raise ValueError("complete option blocks must have the same paired replica count")
        for value in samples.values():
            if np.asarray(value).shape != (next(iter(sizes)), 3):
                raise ValueError("paired samples must carry reward/failure/success vectors")
        key = _key(root)
        if is_base and key in grouped:
            raise ValueError("base logs must contain each root once, not cumulative checkpoint copies")
        old_count = len(grouped[key]["pair_deltas"][OPTIONS[1]]) if key in grouped else 0
        if not is_base and log["original_replicas"] != old_count:
            raise ValueError("extra block original replica count does not match reconstructed samples")
        if key not in grouped:
            grouped[key] = dict(query=root["query"], episode=root["episode"], board=list(root["board"]),
                                pair_deltas={option: [] for option in OPTIONS[1:]})
        for option in OPTIONS[1:]:
            grouped[key]["pair_deltas"][option].extend(deepcopy(samples[option]))
        if not is_base:
            if log["resulting_replicas"] != old_count + next(iter(sizes)):
                raise ValueError("extra block resulting replica count does not match pooled samples")
            counts["extra_complete_blocks"] += 1

    for log in base_logs:
        add(log, True)
    for log in extra_logs:
        add(log, False)
    retained = {_key(root): np.asarray(root["target"]).reshape(4, 3)
                for root in _pack_roots(mean_rows)}
    if set(retained) != set(grouped):
        raise ValueError("reconstructed paired roots do not match retained V86 mean dataset roots")
    roots, largest_difference = [], 0.0
    for key, root in sorted(grouped.items()):
        samples = root["pair_deltas"]
        means = np.asarray([np.asarray(samples[option], dtype=float).mean(axis=0) for option in OPTIONS[1:]])
        difference = float(np.max(np.abs(means - retained[key])))
        largest_difference = max(largest_difference, difference)
        if not np.allclose(means, retained[key], rtol=0, atol=1e-12):
            raise ValueError("pooled paired means disagree with the retained V86 weighted means")
        root.update(n_replicas=len(samples[OPTIONS[1]]), target=means.reshape(-1).tolist(),
                    targets={option: value.tolist() for option, value in zip(OPTIONS[1:], means)},
                    evidence={option: paired_evidence(samples[option], root["query"]) for option in OPTIONS[1:]})
        roots.append(root)
    training = [root for root in roots if root["episode"] % 5 != 4]
    heldout = [root for root in roots if root["episode"] % 5 == 4]
    return roots, dict(counts=dict(counts), roots=len(roots), training_roots=len(training),
        heldout_roots=len(heldout), paired_root_replicas=sum(root["n_replicas"] for root in roots),
        replica_count_distribution=dict(Counter(root["n_replicas"] for root in roots)),
        largest_mean_difference=largest_difference, retained_means_match=True,
        labels=_label_counts(roots), training_labels=_label_counts(training), heldout_labels=_label_counts(heldout),
        seconds=perf_counter() - started)


def _fit(x, labels, targets, counts):
    from sklearn.tree import DecisionTreeClassifier

    model = DecisionTreeClassifier(**TREE_PARAMETERS).fit(x, labels)
    tree = model.tree_
    membership = model.decision_path(x).toarray().astype(bool)
    frequencies, values = [], []
    for node in range(tree.node_count):
        selected = membership[:, node]
        frequencies.append([[float(np.mean(labels[selected, option] == label)) for label in LABEL_VALUES]
                            for option in range(4)])
        values.append(targets[selected].mean(axis=0).tolist())
    counts.update(tree_fits=1, classifier_tree_fits=1, fit_rows=len(x), fit_roots=len(x),
                  fit_candidate_labels=4 * len(x), leaf_stat_roots=len(x),
                  node_stat_memberships=int(membership.sum()))
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(), samples=tree.n_node_samples.tolist(),
        frequencies=frequencies, values=values)


class EvidenceSelector:
    """Classify evidence by whole root and use a matched point-mean ablation."""

    def __init__(self, trees, checkpoint, mode="SUPPORTED"):
        if mode not in MODES:
            raise ValueError("mode must be POINT or SUPPORTED")
        self.trees, self.checkpoint, self.mode = trees, checkpoint, mode

    @classmethod
    def fit(cls, roots, checkpoint=12):
        started = perf_counter()
        roots = list(roots)
        counts = Counter(input_roots_read=len(roots))
        trees, query_logs = {}, {}
        for query in QUERIES:
            selected = [root for root in roots if root["query"] == query]
            training = [root for root in selected if root["episode"] % 5 != 4]
            heldout = [root for root in selected if root["episode"] % 5 == 4]
            if not training:
                raise ValueError(f"checkpoint {checkpoint} has no training roots for {query}")
            counts["training_roots_read"] += len(training)
            counts["paired_root_replicas_read"] += sum(root["n_replicas"] for root in training)
            x = _array(training, counts)
            labels = np.asarray([[root["evidence"][option]["label"] for option in OPTIONS[1:]]
                                 for root in training], dtype=int)
            targets = np.asarray([root["target"] for root in training], dtype=float)
            tree = trees[query] = _fit(x, labels, targets, counts)
            query_logs[query] = dict(training_roots=len(training), heldout_roots=len(heldout),
                paired_training_root_replicas=sum(root["n_replicas"] for root in training),
                paired_heldout_root_replicas=sum(root["n_replicas"] for root in heldout),
                training_labels=_label_counts(training), heldout_labels=_label_counts(heldout),
                nodes=len(tree["left"]), leaves=sum(left < 0 for left in tree["left"]),
                training_target_mean=targets.mean(axis=0).reshape(4, 3).tolist())
        training_count = sum(root["episode"] % 5 != 4 for root in roots)
        return cls(trees, checkpoint), dict(checkpoint=checkpoint, input_roots=len(roots),
            training_roots=training_count, heldout_roots=len(roots) - training_count,
            training_records=4 * training_count, heldout_records=4 * (len(roots) - training_count),
            root_weight="equal", min_samples_leaf_unit="roots", label_multiplier=LABEL_MULTIPLIER,
            support_threshold=SUPPORT_THRESHOLD, label_interval="operational two-standard-error band; not calibrated CI",
            queries=query_logs, counts=dict(counts), seconds=perf_counter() - started)

    def with_mode(self, mode):
        return type(self)(deepcopy(self.trees), self.checkpoint, mode)

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        counts = Counter(evidence_selector_decisions=1)
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0)}
        chosen, best = "H2", 0.0
        if any(option in allowed for option in OPTIONS[1:]):
            tree = self.trees[query]
            leaf = int(_apply(tree, _array([dict(board=board)], counts), counts)[0])
            vectors = np.asarray(tree["values"][leaf]).reshape(4, 3)
            counts.update(evidence_prediction_roots=1, predicted_output_vectors=4, predicted_candidate_frequencies=4)
            for index, option in enumerate(OPTIONS[1:]):
                if option not in allowed:
                    continue
                target = vectors[index].tolist()
                value = float(_utility(target, QUERIES[query]))
                fractions = tree["frequencies"][leaf][index]
                supported = fractions[2] > SUPPORT_THRESHOLD
                predictions[option] = dict(target=target, value=value,
                    evidence_fractions={LABEL_NAMES[label]: fractions[i] for i, label in enumerate(LABEL_VALUES)},
                    positive_fraction=fractions[2], evidence_supported=supported)
                counts["fragment_prediction_rows"] += 1
                if value > best and (self.mode == "POINT" or supported):
                    chosen, best = option, value
        _merge(work, counts)
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"],
                    value=best, predictions=predictions, mode=self.mode)

    def to_payload(self):
        return dict(schema="acfqp.evidence_terminal_fragments.v88", checkpoint=self.checkpoint, mode=self.mode,
            options=list(OPTIONS), queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            tree_parameters=dict(TREE_PARAMETERS), label_values=list(LABEL_VALUES),
            label_multiplier=LABEL_MULTIPLIER, support_threshold=SUPPORT_THRESHOLD,
            root_weight="equal", min_samples_leaf_unit="roots", trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"], payload["mode"])
