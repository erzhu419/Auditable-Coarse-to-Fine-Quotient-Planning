"""Layer-preserving soft pair abstraction with an isolated absorbing code."""
from __future__ import annotations

from typing import Any

import numpy as np


def _pair_layers(adapter: Any) -> np.ndarray:
    layers = []
    for pair in adapter.valid_pair_indices:
        state = int(pair) // adapter.mdp.num_actions
        source = adapter.state_to_source[state]
        layers.append(-1 if source is None else adapter.closure.model.layers[source])
    return np.asarray(layers, dtype=int)


def _layer_order(pair_layers: np.ndarray) -> list[int]:
    return [int(layer) for layer in np.unique(pair_layers) if layer != -1] + [-1]


def fit_layered_abstraction(adapter: Any, distance: np.ndarray, author_abstraction: Any, *, beta: float) -> Any:
    """Independently fit each remaining-horizon block using the original flat BA.

    Conditional uniform priors preserve global uniform-pair posterior columns.
    The conditional pruning threshold maintains the original global code-mass
    threshold. Terminal is the sole fixed code outside the fitted blocks.
    """
    pair_layers = _pair_layers(adapter)
    count = pair_layers.size
    distance = np.asarray(distance, dtype=float)
    if distance.shape != (count, count):
        raise ValueError("Distance must contain the adapter's legal pairs")
    blocks = []
    for layer in _layer_order(pair_layers):
        indices = np.flatnonzero(pair_layers == layer)
        if layer == -1:
            if indices.size != 1:
                raise ValueError("The absorbing layer must have exactly one legal pair")
            block = author_abstraction.StateActionAbstraction(
                beta=beta, encoder=np.ones((1, 1)), posterior=np.ones((1, 1)),
                decoder=np.zeros(1, dtype=int), full_encoder=np.ones((1, 1)),
                full_decoder=np.zeros(1, dtype=int), solver_kind="flat",
            )
        else:
            block = author_abstraction.fit_soft_abstraction(
                distortion=distance[np.ix_(indices, indices)],
                mu=np.full(indices.size, 1. / indices.size), beta=beta,
                num_abstract=indices.size, max_outer=200, max_inner=50,
                tolerance=1e-6, prune_mass_threshold=1e-4 * count / indices.size,
                solver_kind="flat",
            )
        blocks.append((indices, block))
    code_count = sum(block.encoder.shape[1] for _, block in blocks)
    full_count = sum(block.full_encoder.shape[1] for _, block in blocks)
    encoder = np.zeros((count, code_count))
    posterior = np.zeros((count, code_count))
    decoder = np.empty(code_count, dtype=int)
    full_encoder = np.zeros((count, full_count))
    full_decoder = np.empty(full_count, dtype=int)
    offset = full_offset = 0
    for indices, block in blocks:
        codes = np.arange(offset, offset + block.encoder.shape[1])
        full_codes = np.arange(full_offset, full_offset + block.full_encoder.shape[1])
        encoder[np.ix_(indices, codes)] = block.encoder
        posterior[np.ix_(indices, codes)] = block.posterior
        decoder[codes] = indices[block.decoder]
        full_encoder[np.ix_(indices, full_codes)] = block.full_encoder
        full_decoder[full_codes] = indices[block.full_decoder]
        offset += codes.size
        full_offset += full_codes.size
    return author_abstraction.StateActionAbstraction(
        beta=beta, encoder=encoder, posterior=posterior, decoder=decoder,
        full_encoder=full_encoder, full_decoder=full_decoder, solver_kind="flat",
    )


def layer_inventory(adapter: Any, abstraction: Any) -> dict[str, Any]:
    """Describe actual encoder/posterior isolation using each decoder's layer."""
    pair_layers = _pair_layers(adapter)
    code_layers = pair_layers[abstraction.decoder]
    full_code_layers = pair_layers[abstraction.full_decoder]
    crossed = pair_layers[:, None] != code_layers[None, :]
    full_crossed = pair_layers[:, None] != full_code_layers[None, :]
    terminal_rows = np.flatnonzero(pair_layers == -1)
    terminal_codes = np.flatnonzero(code_layers == -1)
    terminal_unique = terminal_rows.size == terminal_codes.size == 1
    terminal_pure = False
    if terminal_unique:
        row, code = int(terminal_rows[0]), int(terminal_codes[0])
        expected = np.zeros(abstraction.encoder.shape[1])
        expected[code] = 1.
        terminal_pure = bool(np.array_equal(abstraction.encoder[row], expected))
    order = _layer_order(pair_layers)
    return {
        "layers": order,
        "pair_count_by_layer": {str(layer): int(np.count_nonzero(pair_layers == layer)) for layer in order},
        "code_count_by_layer": {str(layer): int(np.count_nonzero(code_layers == layer)) for layer in order},
        "full_code_count_by_layer": {str(layer): int(np.count_nonzero(full_code_layers == layer)) for layer in order},
        "cross_layer_mass_max": float(np.max(np.sum(np.abs(abstraction.encoder) * crossed, axis=1))),
        "full_cross_layer_mass_max": float(np.max(np.sum(np.abs(abstraction.full_encoder) * full_crossed, axis=1))),
        "posterior_block_mass_max": float(np.max(np.sum(np.abs(abstraction.posterior) * crossed, axis=0))),
        "terminal_row_pure": terminal_pure,
        "terminal_code_unique": terminal_unique,
        "decoder_layer_consistent": bool(not np.any(abstraction.encoder[crossed]) and not np.any(abstraction.full_encoder[full_crossed])),
        "terminal_code_index": int(terminal_codes[0]) if terminal_unique else None,
    }


def stable_legal_policy(adapter: Any, grounded_rect_q: np.ndarray, *, reward_scale: float = 1., tie_tolerance: float = 1e-12) -> np.ndarray:
    """Read out the first legal action within tolerance in original reward units.

    This is only a policy readout; the Bellman operator still uses exact max.
    """
    if not np.isfinite(reward_scale) or reward_scale <= 0.:
        raise ValueError("Reward scale must be positive and finite")
    values = np.asarray(grounded_rect_q, dtype=float).reshape(adapter.legal_mask.shape) / reward_scale
    maxima = np.max(np.where(adapter.legal_mask, values, -np.inf), axis=1)
    gaps = maxima[:, None] - values
    eligible = adapter.legal_mask & (gaps <= tie_tolerance)
    return np.argmax(eligible, axis=1)
