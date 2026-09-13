"""A teacher-best-set objective for the unchanged goal-free NodeQ."""
from __future__ import annotations

import numpy as np
import torch


def teacher_best_mask(targets, legal, tolerance=1e-9):
    """Identify all legal maxima using the retained float64 teacher labels."""
    targets = np.asarray(targets, dtype=np.float64)
    legal = np.asarray(legal, dtype=bool)
    maximum = np.where(legal, targets, -np.inf).max(axis=-1, keepdims=True)
    return legal & (maximum - targets <= tolerance)


def best_action_loss(logits, best, legal):
    """Negative log probability mass of the full best set, averaged by state."""
    legal_normalizer = torch.logsumexp(logits.masked_fill(~legal, -torch.inf), dim=-1)
    best_normalizer = torch.logsumexp(logits.masked_fill(~best, -torch.inf), dim=-1)
    return (legal_normalizer - best_normalizer).mean()


def objective_metrics(logits, best, legal):
    """Stable float64 objective diagnostics for one retained evaluation state."""
    logits = np.asarray(logits, dtype=np.float64)
    legal_logits = logits[np.asarray(legal, dtype=bool)]
    best_logits = logits[np.asarray(best, dtype=bool)]
    legal_maximum = float(legal_logits.max())
    best_maximum = float(best_logits.max())
    nll = (legal_maximum - best_maximum
           + float(np.log(np.exp(legal_logits - legal_maximum).sum()))
           - float(np.log(np.exp(best_logits - best_maximum).sum())))
    return {"best_set_nll": nll, "best_set_probability": float(np.exp(-nll)),
            "best_set_size": int(len(best_logits))}
