#include <algorithm>
#include <cstdint>
#include <limits>

namespace {
constexpr int occurrences = 32;
constexpr int cells_per_tuple = 6;

void addresses(const int32_t* board, const int32_t* patterns, int radix,
               int64_t* indices) {
    int64_t stride = 1;
    for (int i = 0; i < cells_per_tuple; ++i) stride *= radix;
    for (int tuple = 0; tuple < occurrences; ++tuple) {
        int64_t address = 0;
        for (int cell = 0; cell < cells_per_tuple; ++cell)
            address = address * radix + board[patterns[tuple * cells_per_tuple + cell]];
        indices[tuple] = (tuple / 8) * stride + address;
    }
}

double prediction(const int32_t* board, const int32_t* patterns, int radix,
                  const double* weights) {
    int64_t indices[occurrences];
    addresses(board, patterns, radix, indices);
    double value = 0.0;
    for (int i = 0; i < occurrences; ++i) value += weights[indices[i]];
    return value;
}
}

extern "C" double ntuple_value_v120(const int32_t* board, const int32_t* patterns,
                                   int radix, const double* weights) {
    return prediction(board, patterns, radix, weights);
}

extern "C" double ntuple_update_v120(const int32_t* board, const int32_t* patterns,
                                    int radix, double* weights, double target,
                                    double alpha, int32_t* unique_updates) {
    int64_t indices[occurrences];
    addresses(board, patterns, radix, indices);
    double before = 0.0;
    for (int i = 0; i < occurrences; ++i) before += weights[indices[i]];
    const double error = target - before;
    std::sort(indices, indices + occurrences);
    *unique_updates = 0;
    for (int first = 0; first < occurrences;) {
        int end = first + 1;
        while (end < occurrences && indices[end] == indices[first]) ++end;
        weights[indices[first]] += alpha * error * (end - first);
        ++*unique_updates;
        first = end;
    }
    return error;
}

// All action transitions come from the caller's identified line program.
extern "C" int ntuple_choose_v120(const int32_t* board, const int32_t* patterns,
                                 int radix, const double* weights,
                                 const int32_t* table, const int64_t* line_scores,
                                 const int32_t* action_cells,
                                 double reward_weight, double goal_bonus,
                                 int32_t* moved, int64_t* scores,
                                 double* tails, double* values, int32_t* legal,
                                 uint64_t* counts) {
    int best = -1;
    double best_value = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved + action * 16;
        std::copy(board, board + 16, after);
        scores[action] = 0;
        ++counts[0]; // learned_swipe_calls
        for (int line = 0; line < 4; ++line) {
            const int32_t* cells = action_cells + action * 16 + line * 4;
            int index = 0;
            for (int i = 0; i < 4; ++i) index = index * radix + board[cells[i]];
            for (int i = 0; i < 4; ++i) after[cells[i]] = table[index * 4 + i];
            scores[action] += line_scores[index];
            ++counts[1]; // line_table_lookups
        }
        legal[action] = !std::equal(board, board + 16, after);
        if (!legal[action]) continue;
        ++counts[2]; // legal_swipes
        ++counts[3]; // learned_terminal_checks
        const bool goal = *std::max_element(after, after + 16) >= radix;
        if (goal) {
            tails[action] = goal_bonus;
            ++counts[6]; // terminal_goal_bypasses
        } else {
            tails[action] = prediction(after, patterns, radix, weights);
            ++counts[4]; // value_predictions
            counts[5] += occurrences; // table_lookups
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
