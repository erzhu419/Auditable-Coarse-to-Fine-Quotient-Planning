#include <algorithm>
#include <cstdint>
#include <limits>

namespace {
constexpr int occurrences = 32;

int64_t bank_stride(int radix) {
    int64_t stride = 4;
    for (int i = 0; i < 6; ++i) stride *= radix;
    return stride;
}

void addresses(const int32_t* board, const int32_t* patterns, const int32_t* extra,
               int radix, int mode, int64_t* indices, uint64_t* counts, bool update) {
    const int64_t bank_size = bank_stride(radix);
    const int64_t tuple_size = bank_size / 4;
    int global_bank = 0;
    if (mode == 0) {
        int empty = 0;
        for (int i = 0; i < 16; ++i) empty += board[i] == 0;
        global_bank = empty <= 4;
        counts[7] += 16; // context_cell_reads
        counts[8] += 1;  // context_bank_selections
    } else {
        counts[7] += occurrences;
        counts[8] += occurrences;
    }
    for (int tuple = 0; tuple < occurrences; ++tuple) {
        int64_t address = 0;
        for (int cell = 0; cell < 6; ++cell)
            address = address * radix + board[patterns[tuple * 6 + cell]];
        const int bank = mode == 0 ? global_bank : board[extra[tuple]] > 0;
        indices[tuple] = bank * bank_size + (tuple / 8) * tuple_size + address;
        ++counts[(update ? 11 : 9) + bank];
    }
    counts[15] += occurrences; // context_bank_offset_additions
}

double prediction(const int32_t* board, const int32_t* patterns, const int32_t* extra,
                  int radix, int mode, const double* weights, uint64_t* counts) {
    int64_t indices[occurrences];
    addresses(board, patterns, extra, radix, mode, indices, counts, false);
    double value = 0.0;
    for (int i = 0; i < occurrences; ++i) value += weights[indices[i]];
    return value;
}
}

extern "C" double contextual_value_v134(const int32_t* board, const int32_t* patterns,
                                        const int32_t* extra, int radix, int mode,
                                        const double* weights, uint64_t* counts) {
    return prediction(board, patterns, extra, radix, mode, weights, counts);
}

extern "C" double contextual_update_v134(const int32_t* board, const int32_t* patterns,
                                         const int32_t* extra, int radix, int mode,
                                         double* weights, double target, double alpha,
                                         int32_t* unique_updates, uint64_t* counts) {
    int64_t indices[occurrences];
    addresses(board, patterns, extra, radix, mode, indices, counts, true);
    double before = 0.0;
    for (int i = 0; i < occurrences; ++i) before += weights[indices[i]];
    const double error = target - before;
    const int64_t bank_size = bank_stride(radix);
    std::sort(indices, indices + occurrences);
    *unique_updates = 0;
    for (int first = 0; first < occurrences;) {
        int end = first + 1;
        while (end < occurrences && indices[end] == indices[first]) ++end;
        weights[indices[first]] += alpha * error * (end - first);
        ++counts[13 + indices[first] / bank_size];
        counts[16] += (end - first) * (end - first); // update_feature_squared_norm
        ++*unique_updates;
        first = end;
    }
    return error;
}

// Transitions and arithmetic retain V120's identified line-program semantics.
extern "C" int contextual_choose_v134(const int32_t* board, const int32_t* patterns,
                                      const int32_t* extra, int radix, int mode,
                                      const double* weights, const int32_t* table,
                                      const int64_t* line_scores, const int32_t* action_cells,
                                      double reward_weight, double goal_bonus,
                                      int32_t* moved, int64_t* scores, double* tails,
                                      double* values, int32_t* legal, uint64_t* counts) {
    int best = -1;
    double best_value = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved + action * 16;
        std::copy(board, board + 16, after);
        scores[action] = 0;
        ++counts[0];
        for (int line = 0; line < 4; ++line) {
            const int32_t* cells = action_cells + action * 16 + line * 4;
            int index = 0;
            for (int i = 0; i < 4; ++i) index = index * radix + board[cells[i]];
            for (int i = 0; i < 4; ++i) after[cells[i]] = table[index * 4 + i];
            scores[action] += line_scores[index];
            ++counts[1];
        }
        legal[action] = !std::equal(board, board + 16, after);
        if (!legal[action]) continue;
        ++counts[2];
        ++counts[3];
        const bool goal = *std::max_element(after, after + 16) >= radix;
        if (goal) {
            tails[action] = goal_bonus;
            ++counts[6];
        } else {
            tails[action] = prediction(after, patterns, extra, radix, mode, weights, counts);
            ++counts[4];
            counts[5] += occurrences;
        }
        values[action] = reward_weight * (static_cast<double>(scores[action]) / 2048.0)
                         + tails[action];
        if (best < 0 || values[action] > best_value) {
            best = action;
            best_value = values[action];
        }
    }
    return best;
}
