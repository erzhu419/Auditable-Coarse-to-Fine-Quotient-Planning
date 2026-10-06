#include <algorithm>
#include <cstdint>
#include <limits>

extern "C" int ntuple_choose_v120(const int32_t*, const int32_t*, int, const double*,
    const int32_t*, const int64_t*, const int32_t*, double, double, int32_t*, int64_t*,
    double*, double*, int32_t*, uint64_t*);
extern "C" int contextual_choose_v134(const int32_t*, const int32_t*, const int32_t*,
    int, int, const double*, const int32_t*, const int64_t*, const int32_t*, double,
    double, int32_t*, int64_t*, double*, double*, int32_t*, uint64_t*);

namespace {
enum Count { ROOT_SWIPES=17, ROOT_LEGAL, ROOT_GOALS, LEAF_CHOOSES, SECOND_SWIPES,
    SPAWN_OUTCOMES, RANK1_OUTCOMES, RANK2_OUTCOMES, POSTSPAWN_STATES,
    LEAF_LOSSES, LEAF_GOALS, PROBABILITY_PRODUCTS, PROBABILITY_SUMS,
    FULL_COMPARISONS, SHORT_COMPARISONS, MEAN_PRODUCTS, MEAN_SUMS };

// V135 leaf ordering and arithmetic, with a zero-nonterminal-tail readout
// obtained from the same second-action scores and legality. No second search.
void leaf_values(const int32_t* board, const int32_t* patterns, const int32_t* extra,
    int radix, int mode, const double* weights, const int32_t* table,
    const int64_t* line_scores, const int32_t* cells, double source_goal,
    double target_goal, double failure, double failure_shift,
    double success_shift, int convert, double* full, double* short_value,
    uint64_t* counts) {
    ++counts[LEAF_CHOOSES];
    ++counts[3];
    if (*std::max_element(board, board+16) >= radix) {
        ++counts[6];
        ++counts[LEAF_GOALS];
        *full = *short_value = target_goal;
        return;
    }
    int32_t moved[64], legal[4];
    int64_t scores[4];
    double tails[4], values[4];
    const uint64_t before = counts[0];
    const int best = mode < 0
        ? ntuple_choose_v120(board, patterns, radix, weights, table, line_scores, cells,
            1.0, source_goal, moved, scores, tails, values, legal, counts)
        : contextual_choose_v134(board, patterns, extra, radix, mode, weights, table,
            line_scores, cells, 1.0, source_goal, moved, scores, tails, values, legal, counts);
    counts[SECOND_SWIPES] += counts[0]-before;
    if (best < 0) {
        ++counts[LEAF_LOSSES];
        *full = *short_value = -failure;
        return;
    }
    *full = *short_value = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        if (!legal[action]) continue;
        const bool goal = *std::max_element(moved+16*action, moved+16*(action+1)) >= radix;
        const double value = goal ? static_cast<double>(scores[action])/2048.0+target_goal
            : convert ? values[action]+failure_shift+success_shift : values[action];
        if (value > *full) *full = value;
        ++counts[FULL_COMPARISONS];
        const double local = static_cast<double>(scores[action])/2048.0+(goal ? target_goal : 0.0);
        if (local > *short_value) *short_value = local;
        ++counts[SHORT_COMPARISONS];
    }
}
}

extern "C" int natural_action_components_v283(const int32_t* board,
    const int32_t* patterns, const int32_t* extra, int radix, int mode,
    const double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double target_goal, double failure,
    double failure_shift, double success_shift, int convert,
    int32_t* moved, int64_t* scores, int32_t* legal,
    double* full_leaves, double* short_leaves, double* full_means,
    double* short_means, uint64_t* counts) {
    ++counts[3];
    if (*std::max_element(board, board+16) >= radix) {
        ++counts[6];
        return -2;
    }
    int legal_count = 0;
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved+16*action;
        std::copy(board, board+16, after);
        scores[action] = 0;
        ++counts[0];
        ++counts[ROOT_SWIPES];
        for (int line = 0; line < 4; ++line) {
            const int32_t* line_cells = cells+16*action+4*line;
            int index = 0;
            for (int i = 0; i < 4; ++i) index = index*radix+board[line_cells[i]];
            for (int i = 0; i < 4; ++i) after[line_cells[i]] = table[4*index+i];
            scores[action] += line_scores[index];
            ++counts[1];
        }
        legal[action] = !std::equal(board, board+16, after);
        if (!legal[action]) continue;
        ++legal_count;
        ++counts[2];
        ++counts[3];
        ++counts[ROOT_LEGAL];
        if (*std::max_element(after, after+16) >= radix) {
            ++counts[6];
            ++counts[ROOT_GOALS];
            full_means[2*action] = full_means[2*action+1] = target_goal;
            short_means[2*action] = short_means[2*action+1] = target_goal;
            continue;
        }
        int empty = 0;
        for (int cell = 0; cell < 16; ++cell) empty += after[cell] == 0;
        for (int cell = 0; cell < 16; ++cell) {
            if (after[cell] != 0) continue;
            for (int rank = 1; rank <= 2; ++rank) {
                int32_t spawned[16];
                std::copy(after, after+16, spawned);
                spawned[cell] = rank;
                ++counts[SPAWN_OUTCOMES];
                ++counts[rank == 1 ? RANK1_OUTCOMES : RANK2_OUTCOMES];
                ++counts[POSTSPAWN_STATES];
                const int offset = 32*action+2*cell+rank-1;
                leaf_values(spawned, patterns, extra, radix, mode, weights, table,
                    line_scores, cells, source_goal, target_goal, failure,
                    failure_shift, success_shift, convert,
                    full_leaves+offset, short_leaves+offset, counts);
                const double probability = 1.0/empty;
                full_means[2*action+rank-1] += probability*full_leaves[offset];
                short_means[2*action+rank-1] += probability*short_leaves[offset];
                counts[MEAN_PRODUCTS] += 2;
                counts[MEAN_SUMS] += 2;
            }
        }
    }
    return legal_count ? 0 : -1;
}
