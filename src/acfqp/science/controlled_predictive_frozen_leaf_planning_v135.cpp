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
// The first 17 counters are V134's unchanged native operation counts.
enum Count { ROOT_SWIPES=17, ROOT_LEGAL, ROOT_GOALS, LEAF_CHOOSES, SECOND_SWIPES,
    SPAWN_OUTCOMES, RANK1_OUTCOMES, RANK2_OUTCOMES, POSTSPAWN_STATES,
    LEAF_LOSSES, LEAF_GOALS, PROBABILITY_PRODUCTS, PROBABILITY_SUMS };

double leaf_value(const int32_t* board, const int32_t* patterns, const int32_t* extra,
                  int radix, int mode, const double* weights, const int32_t* table,
                  const int64_t* line_scores, const int32_t* cells, double source_goal,
                  double target_goal, double failure, double failure_shift,
                  double success_shift, int convert, uint64_t* counts) {
    ++counts[LEAF_CHOOSES];
    ++counts[3]; // learned_terminal_checks at the leaf state
    if (*std::max_element(board, board+16) >= radix) {
        ++counts[6];
        ++counts[LEAF_GOALS];
        return target_goal;
    }
    int32_t moved[64], legal[4];
    int64_t scores[4];
    double tails[4], values[4];
    const uint64_t swipes_before = counts[0];
    const int best = mode < 0
        ? ntuple_choose_v120(board, patterns, radix, weights, table, line_scores, cells,
            1.0, source_goal, moved, scores, tails, values, legal, counts)
        : contextual_choose_v134(board, patterns, extra, radix, mode, weights, table,
            line_scores, cells, 1.0, source_goal, moved, scores, tails, values, legal, counts);
    counts[SECOND_SWIPES] += counts[0]-swipes_before;
    if (best < 0) {
        ++counts[LEAF_LOSSES];
        return -failure;
    }
    // Query conversion can turn a raw strict ordering into a rounded tie.
    // Re-select across every legal converted value in lexical action order.
    double chosen = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        if (!legal[action]) continue;
        const bool goal = *std::max_element(moved+16*action, moved+16*(action+1)) >= radix;
        const double value = goal ? static_cast<double>(scores[action])/2048.0+target_goal
            : convert ? values[action]+failure_shift+success_shift : values[action];
        if (value > chosen) chosen = value;
    }
    return chosen;
}
}

extern "C" int frozen_leaf_choose_v135(const int32_t* board, const int32_t* patterns,
    const int32_t* extra, int radix, int mode, const double* weights,
    const int32_t* table, const int64_t* line_scores, const int32_t* cells,
    double source_goal, double target_goal, double failure, double failure_shift,
    double success_shift, double probability_rank1, double probability_rank2,
    int convert, int32_t* moved, int64_t* scores,
    double* tails, double* values, int32_t* legal, uint64_t* counts) {
    ++counts[3];
    if (*std::max_element(board, board+16) >= radix) {
        ++counts[6];
        return -2;
    }
    int best = -1;
    double best_value = -std::numeric_limits<double>::infinity();
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
        ++counts[2];
        ++counts[3];
        ++counts[ROOT_LEGAL];
        if (*std::max_element(after, after+16) >= radix) {
            tails[action] = target_goal;
            ++counts[6];
            ++counts[ROOT_GOALS];
        } else {
            int empty = 0;
            for (int i = 0; i < 16; ++i) empty += after[i] == 0;
            double expectation = 0.0;
            for (int cell = 0; cell < 16; ++cell) {
                if (after[cell] != 0) continue;
                for (int rank = 1; rank <= 2; ++rank) {
                    int32_t spawned[16];
                    std::copy(after, after+16, spawned);
                    spawned[cell] = rank;
                    ++counts[SPAWN_OUTCOMES];
                    ++counts[rank == 1 ? RANK1_OUTCOMES : RANK2_OUTCOMES];
                    ++counts[POSTSPAWN_STATES];
                    const double value = leaf_value(spawned, patterns, extra, radix, mode,
                        weights, table, line_scores, cells, source_goal, target_goal, failure,
                        failure_shift, success_shift, convert, counts);
                    const double probability = (rank == 1 ? probability_rank1 : probability_rank2)/empty;
                    expectation += probability*value;
                    ++counts[PROBABILITY_PRODUCTS];
                    ++counts[PROBABILITY_SUMS];
                }
            }
            tails[action] = expectation;
        }
        values[action] = static_cast<double>(scores[action])/2048.0+tails[action];
        if (best < 0 || values[action] > best_value) {
            best = action;
            best_value = values[action];
        }
    }
    return best;
}
