"""Fit fixed-policy scalar offsets and compare unchanged policy candidates."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_anchored_success_v127 import choose_gpi

SCHEMA = 'acfqp.policy_calibration.v129'
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V129 build directory must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        path = build_dir / f'policy_calibration_v129_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(Path(__file__).with_suffix('.cpp')), '-o', str(path)],
            check=True, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(build_dir)))
        library = ctypes.CDLL(str(path)); counts['cpp_compilations'] += 1
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        library.policy_tail_values_v129.argtypes = [ip, ctypes.c_int, ip, ctypes.c_int, dp, dp]
        library.policy_tail_values_v129.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class PolicyOffsetCalibrator:
    """One translation fitted from complete retained games of a fixed policy."""
    def __init__(self, source_model, source_query, build_dir):
        started = perf_counter()
        self.source, self.source_query = source_model, dict(source_query)
        if source_query.get('reward_weight', 1.) != 1.:
            raise ValueError('V129 anchors use reward weight one')
        self.counts, self.setup_counts = Counter(), Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.n = 0
        self.target_sum = self.anchor_sum = self.residual_sum = 0.
        self.setup_seconds = perf_counter() - started

    @property
    def offset(self):
        return self.residual_sum / self.n if self.n else 0.

    def fit_episode(self, afterstates, scores, status):
        started = perf_counter(); work = Counter(calibration_games=1)
        boards = np.ascontiguousarray(afterstates, dtype=np.int32)
        if boards.size == 0:
            boards = np.empty((0, 16), dtype=np.int32)
        scores = np.ascontiguousarray(scores, dtype=np.float64)
        if boards.shape != (len(scores), 16) or np.any(boards < 0):
            raise ValueError('calibration afterstates and scores must align')
        work['calibration_observed_afterstates'] = len(scores)
        if status == 'CUTOFF':
            work['censored_games'] += 1; work['censored_afterstates'] += len(scores)
            row = dict(status=status, observed_afterstates=len(scores), n=0, analytic_goals=0,
                censored_afterstates=len(scores), target_sum=0., anchor_sum=0., residual_sum=0.)
        else:
            if status not in ('WON', 'LOST'):
                raise ValueError('calibration labels require a terminal game')
            goal = np.max(boards, axis=1) >= self.source.radix if len(boards) else np.zeros(0, dtype=bool)
            eligible = np.ascontiguousarray(boards[~goal], dtype=np.int32)
            tail_values = np.empty(len(eligible), dtype=np.float64)
            self.library.policy_tail_values_v129(eligible, len(eligible), self.source.patterns,
                self.source.radix, self.source.weights, tail_values)
            # Reverse cumulative rewards include this action once on both sides.
            targets = np.cumsum(scores[::-1])[::-1] / 2048.
            targets -= float(self.source_query.get('failure_penalty', 0.)) * (status == 'LOST')
            targets += float(self.source_query.get('goal_bonus', 0.)) * (status == 'WON')
            targets = targets[~goal]
            anchors = scores[~goal] / 2048. + tail_values
            residuals = targets - anchors
            row = dict(status=status, observed_afterstates=len(scores), n=len(eligible),
                analytic_goals=int(goal.sum()), censored_afterstates=0,
                target_sum=float(targets.sum()), anchor_sum=float(anchors.sum()),
                residual_sum=float(residuals.sum()))
            work.update(calibration_samples=len(eligible), source_tail_predictions=len(eligible),
                source_table_lookups=32 * len(eligible), calibration_analytic_goals=int(goal.sum()))
            self.n += row['n']; self.target_sum += row['target_sum']
            self.anchor_sum += row['anchor_sum']; self.residual_sum += row['residual_sum']
        self.counts.update(work)
        return dict(row, offset_after=self.offset, work=dict(work), seconds=perf_counter() - started)

    def to_payload(self):
        return dict(schema=SCHEMA, source_query=self.source_query, source_updates=self.source.updates,
            n=self.n, target_sum=self.target_sum, anchor_sum=self.anchor_sum,
            residual_sum=self.residual_sum, offset=self.offset, counts=dict(self.counts),
            setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds)


def calibrated_choice(models, offsets, board, query, mode='LEARNED'):
    """Translate only each policy's already selected candidate for comparison.

    No within-policy action is selected again after translation. Winning
    candidates keep their analytic query value, even when their policy offset
    is nonzero. Zero offsets yield the V127 GPI action and source-policy tie.
    """
    if len(models) != len(offsets):
        raise ValueError('each fixed policy needs one calibration offset')
    choices = [choose_gpi([model], board, query, mode=mode) for model in models]
    candidates = []
    for index, (model, offset, choice) in enumerate(zip(models, offsets, choices)):
        candidate = {key: choice[key] for key in ('action', 'score', 'afterstate',
            'anchor_value', 'success_probability', 'value')}
        analytic = max(choice['afterstate']) >= model.rule.goal_rank
        # No continuation is modeled for a terminal decision board either.
        shifted = not analytic and choice['action'] is not None
        comparison = choice['value'] + float(offset) if shifted else choice['value']
        candidates.append(dict(candidate, comparison_value=comparison, policy_index=index,
            applied_offset=float(offset) if shifted else 0.))
    selected = min(candidates, key=lambda row: (-row['comparison_value'], row['action'] or '', row['policy_index']))
    chosen_policy = choices[selected['policy_index']]
    return dict(selected, status=chosen_policy['status'], per_policy_candidates=candidates,
        per_policy_action_values=[choice['action_values'] for choice in choices])
