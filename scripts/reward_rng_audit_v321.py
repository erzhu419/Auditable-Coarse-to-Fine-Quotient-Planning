"""Independent first six mt19937_64 uniforms for the fixed H4 reward reader.

H4 consumes at most three intermediate spawn pairs. The first six twisted words
depend only on initializer words 0..6 and 156..161. These words have not been
overwritten when literal twist positions 0..5 execute, so the remaining
initializer/twist positions cannot affect these six outputs. Initializer
recurrence through position 161 remains exact; batching changes only execution.
"""
import numpy as np


def first_six_uniforms(seeds):
    """Return the exact upper-53-bit uniforms with shape ``seeds.shape + (6,)``."""
    seeds = np.asarray(seeds, dtype=np.uint64)
    word = seeds.reshape(-1).copy()
    front = np.empty((word.size, 7), dtype=np.uint64)
    lag = np.empty((word.size, 6), dtype=np.uint64)
    front[:, 0] = word
    multiplier = np.uint64(6364136223846793005)
    for index in range(1, 162):
        word = multiplier * (word ^ (word >> np.uint64(62))) + np.uint64(index)
        if index <= 6:
            front[:, index] = word
        elif index >= 156:
            lag[:, index-156] = word
    merged = (front[:, :6] & np.uint64(0xffffffff80000000)) | (front[:, 1:] & np.uint64(0x7fffffff))
    value = lag ^ (merged >> np.uint64(1)) ^ np.where(
        merged & np.uint64(1), np.uint64(0xb5026f5aa96619e9), np.uint64(0))
    value ^= (value >> np.uint64(29)) & np.uint64(0x5555555555555555)
    value ^= (value << np.uint64(17)) & np.uint64(0x71d67fffeda60000)
    value ^= (value << np.uint64(37)) & np.uint64(0xfff7eee000000000)
    value ^= value >> np.uint64(43)
    return ((value >> np.uint64(11)).astype(np.float64) * 2.**-53).reshape(seeds.shape+(6,))
