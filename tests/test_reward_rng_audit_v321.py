"""A wrong truncated dependency or temper step must fail exact literal RNG agreement."""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from reward_rng_audit_v321 import first_six_uniforms
from verify_closed_loop_v313 import TileRandom


def test_six_uniforms_bit_exact_for_64_declared_life_task_round_group_member_seeds():
    seeds = np.asarray([
        [321500000000+life*10000000+task*1000000+number*100000+group*4+member for member in range(4)]
        for life, group in ((0, 0), (1, 1), (14, 16382), (15, 16383))
        for task in (0, 1) for number in (1, 2)], dtype=np.uint64)
    expected = np.empty(seeds.shape+(6,), dtype=np.float64)
    for index in np.ndindex(seeds.shape):
        literal = TileRandom(int(seeds[index]))
        expected[index] = [literal.random() for _ in range(6)]
    actual = first_six_uniforms(seeds)
    assert actual.dtype == np.float64 and actual.shape == (16, 4, 6)
    np.testing.assert_array_equal(actual, expected)
    assert seeds[-1, -1] == 321651265535


def test_batch_boundaries_do_not_change_seed_or_first_six_draw_order():
    seeds = np.arange(321500100000, 321500100032, dtype=np.uint64).reshape(8, 4)
    whole = first_six_uniforms(seeds)
    chunks = np.concatenate([first_six_uniforms(seeds[:3]), first_six_uniforms(seeds[3:])])
    np.testing.assert_array_equal(whole, chunks)
    flat = first_six_uniforms(seeds.reshape(-1)).reshape(8, 4, 6)
    np.testing.assert_array_equal(whole, flat)
