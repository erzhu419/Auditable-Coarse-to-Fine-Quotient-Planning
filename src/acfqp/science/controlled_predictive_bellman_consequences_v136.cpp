#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
constexpr int N = 32;
enum Count { SWIPES, LINE_LOOKUPS, LEGAL, TERMINAL_CHECKS, JOINT_PREDICTIONS,
    REWARD_PREDICTIONS, SUCCESS_PREDICTIONS, TABLE_LOOKUPS, GOAL_BYPASSES,
    CONTEXT_READS, CONTEXT_SELECTIONS, CONTEXT_OFFSETS, REWARD_OCCURRENCES,
    SUCCESS_OCCURRENCES, REWARD_WRITES, SUCCESS_WRITES, FEATURE_NORM,
    SIGMOIDS, BANK0_PRED, BANK1_PRED, BANK0_UPDATE, BANK1_UPDATE,
    ROOT_SWIPES, ROOT_LEGAL, ROOT_GOALS, LEAF_CHOOSES, SECOND_SWIPES,
    SPAWN_OUTCOMES, RANK1_OUTCOMES, RANK2_OUTCOMES, LEAF_LOSSES,
    PROBABILITY_PRODUCTS, PROBABILITY_SUMS, FEATURE_OCCURRENCES, PROBABILITY_CLOSURES };

int64_t bank_stride(int radix) {
    int64_t size = 4;
    for (int i = 0; i < 6; ++i) size *= radix;
    return size;
}

void addresses(const int32_t* board, const int32_t* patterns, const int32_t* extra,
    int radix, int mode, int64_t* indices, uint64_t* counts, bool update) {
    const int64_t bank_size = bank_stride(radix), tuple_size = bank_size/4;
    for (int tuple = 0; tuple < N; ++tuple) {
        int64_t address = 0;
        for (int cell = 0; cell < 6; ++cell)
            address = address*radix+board[patterns[6*tuple+cell]];
        const int bank = mode < 0 ? 0 : board[extra[tuple]] > 0;
        indices[tuple] = bank*bank_size+(tuple/8)*tuple_size+address;
        ++counts[(update ? BANK0_UPDATE : BANK0_PRED)+bank];
    }
    counts[FEATURE_OCCURRENCES] += N;
    if (mode >= 0) {
        counts[CONTEXT_READS] += N;
        counts[CONTEXT_SELECTIONS] += N;
        counts[CONTEXT_OFFSETS] += N;
    }
}

double sigmoid(double z) {
    if (z >= 0.0) return 1.0/(1.0+std::exp(-z));
    const double e = std::exp(z);
    return e/(1.0+e);
}

// Output: raw reward, reward, logit, success.
void prediction(const int32_t* board, const int32_t* patterns, const int32_t* extra,
    int radix, int mode, int64_t head_size, const double* weights, double reward_intercept,
    double* output, uint64_t* counts, bool update = false, int64_t* saved_indices = nullptr) {
    int64_t local_indices[N];
    int64_t* indices = saved_indices ? saved_indices : local_indices;
    addresses(board, patterns, extra, radix, mode, indices, counts, update);
    double raw_reward = 0.0, z = 0.0;
    for (int i = 0; i < N; ++i) raw_reward += weights[indices[i]];
    for (int i = 0; i < N; ++i) z += weights[head_size+indices[i]];
    output[0] = raw_reward;
    output[1] = raw_reward+reward_intercept;
    output[2] = z;
    output[3] = sigmoid(z);
    ++counts[JOINT_PREDICTIONS];
    ++counts[REWARD_PREDICTIONS];
    ++counts[SUCCESS_PREDICTIONS];
    ++counts[SIGMOIDS];
    counts[TABLE_LOOKUPS] += 2*N;
}

struct Config {
    const int32_t *patterns, *extra, *table, *cells;
    const int64_t* line_scores;
    const double* weights;
    int radix, mode;
    int64_t head_size;
    double reward_intercept, failure_shift, success_shift, teacher_failure,
        teacher_coefficient, failure, goal, probability_rank1, probability_rank2;
};

double query_value(int64_t score, double raw_reward, double success, const Config& c) {
    const double anchor = (static_cast<double>(score)/2048.0+raw_reward)
        +c.failure_shift+c.success_shift;
    return anchor+c.teacher_coefficient*(success-0.5)+(c.teacher_failure-c.failure)
        +((c.failure+c.goal)-c.teacher_coefficient)*success;
}

bool swipe(const int32_t* board, int action, const Config& c,
    int32_t* after, int64_t& score, uint64_t* counts) {
    std::copy(board, board+16, after);
    score = 0;
    ++counts[SWIPES];
    for (int line = 0; line < 4; ++line) {
        const int32_t* cells = c.cells+16*action+4*line;
        int index = 0;
        for (int i = 0; i < 4; ++i) index = index*c.radix+board[cells[i]];
        for (int i = 0; i < 4; ++i) after[cells[i]] = c.table[4*index+i];
        score += c.line_scores[index];
        ++counts[LINE_LOOKUPS];
    }
    const bool legal = !std::equal(board, board+16, after);
    if (legal) { ++counts[LEGAL]; ++counts[TERMINAL_CHECKS]; }
    return legal;
}

// Joint continuation of the SAME action selected by the evaluated query.
void leaf_choice(const int32_t* board, const Config& c, double* result, uint64_t* counts) {
    ++counts[LEAF_CHOOSES];
    ++counts[TERMINAL_CHECKS];
    if (*std::max_element(board, board+16) >= c.radix) {
        result[0] = c.goal; result[1] = 0.0; result[2] = 1.0;
        ++counts[GOAL_BYPASSES];
        return;
    }
    bool found = false;
    result[0] = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        int32_t after[16]; int64_t score;
        ++counts[SECOND_SWIPES];
        if (!swipe(board, action, c, after, score, counts)) continue;
        double predicted[4], value;
        if (*std::max_element(after, after+16) >= c.radix) {
            predicted[1] = 0.0; predicted[3] = 1.0;
            value = static_cast<double>(score)/2048.0+c.goal;
            ++counts[GOAL_BYPASSES];
        } else {
            prediction(after, c.patterns, c.extra, c.radix, c.mode, c.head_size,
                c.weights, c.reward_intercept, predicted, counts);
            value = query_value(score, predicted[0], predicted[3], c);
        }
        if (!found || value > result[0]) {
            found = true;
            result[0] = value;
            result[1] = static_cast<double>(score)/2048.0+predicted[1];
            result[2] = predicted[3];
        }
    }
    if (!found) {
        result[0] = -c.failure; result[1] = 0.0; result[2] = 0.0;
        ++counts[LEAF_LOSSES];
    }
}
}

extern "C" void bellman_value_v136(const int32_t* board, const int32_t* patterns,
    const int32_t* extra, int radix, int mode, int64_t head_size, const double* weights,
    double reward_intercept, double* output, uint64_t* counts) {
    prediction(board, patterns, extra, radix, mode, head_size, weights, reward_intercept, output, counts);
}

extern "C" void bellman_update_v136(const int32_t* board, const int32_t* patterns,
    const int32_t* extra, int radix, int mode, int64_t head_size, double* weights,
    double reward_intercept, double target_reward, double target_success, double alpha,
    double* output, uint64_t* counts) {
    int64_t indices[N];
    prediction(board, patterns, extra, radix, mode, head_size, weights,
        reward_intercept, output, counts, true, indices);
    const double raw_target = target_reward-reward_intercept;
    const double reward_error = raw_target-output[0];
    const double success_error = target_success-output[3];
    output[4] = raw_target; output[5] = reward_error; output[6] = success_error;
    std::sort(indices, indices+N);
    for (int first = 0; first < N;) {
        int end = first+1;
        while (end < N && indices[end] == indices[first]) ++end;
        const int m = end-first;
        weights[indices[first]] += alpha*reward_error*m;
        weights[head_size+indices[first]] += alpha*success_error*m;
        ++counts[REWARD_WRITES]; ++counts[SUCCESS_WRITES];
        counts[FEATURE_NORM] += m*m;
        first = end;
    }
    counts[REWARD_OCCURRENCES] += N;
    counts[SUCCESS_OCCURRENCES] += N;
}

extern "C" int bellman_choose_v136(const int32_t* board, const int32_t* patterns,
    const int32_t* extra, int radix, int mode, int64_t head_size, const double* weights,
    const int32_t* table, const int64_t* line_scores, const int32_t* cells,
    double reward_intercept, double failure_shift, double success_shift,
    double teacher_failure, double teacher_coefficient, double failure, double goal,
    double probability_rank1, double probability_rank2, int depth,
    int32_t* moved, int64_t* scores, double* values, double* tails,
    double* rewards, double* successes, int32_t* legal, uint64_t* counts) {
    const Config c{patterns, extra, table, cells, line_scores, weights, radix, mode,
        head_size, reward_intercept, failure_shift, success_shift, teacher_failure,
        teacher_coefficient, failure, goal, probability_rank1, probability_rank2};
    ++counts[TERMINAL_CHECKS];
    if (*std::max_element(board, board+16) >= radix) {
        ++counts[GOAL_BYPASSES];
        return -2;
    }
    int best = -1;
    double best_value = -std::numeric_limits<double>::infinity();
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved+16*action;
        ++counts[ROOT_SWIPES];
        legal[action] = swipe(board, action, c, after, scores[action], counts);
        if (!legal[action]) continue;
        ++counts[ROOT_LEGAL];
        const double score = static_cast<double>(scores[action])/2048.0;
        if (*std::max_element(after, after+16) >= radix) {
            rewards[action] = 0.0; successes[action] = 1.0;
            tails[action] = goal; values[action] = score+goal;
            ++counts[ROOT_GOALS]; ++counts[GOAL_BYPASSES];
        } else if (depth == 1) {
            double predicted[4];
            prediction(after, patterns, extra, radix, mode, head_size, weights,
                reward_intercept, predicted, counts);
            rewards[action] = predicted[1]; successes[action] = predicted[3];
            values[action] = query_value(scores[action], predicted[0], predicted[3], c);
            tails[action] = values[action]-score;
        } else {
            int empty = 0;
            for (int cell = 0; cell < 16; ++cell) empty += after[cell] == 0;
            double expectation[3] = {0.0, 0.0, 0.0};
            for (int cell = 0; cell < 16; ++cell) {
                if (after[cell] != 0) continue;
                for (int rank = 1; rank <= 2; ++rank) {
                    int32_t successor[16];
                    std::copy(after, after+16, successor); successor[cell] = rank;
                    ++counts[SPAWN_OUTCOMES];
                    ++counts[rank == 1 ? RANK1_OUTCOMES : RANK2_OUTCOMES];
                    double chosen[3];
                    leaf_choice(successor, c, chosen, counts);
                    const double p = (rank == 1 ? probability_rank1 : probability_rank2)/empty;
                    for (int component = 0; component < 3; ++component)
                        expectation[component] += p*chosen[component];
                    counts[PROBABILITY_PRODUCTS] += 3; counts[PROBABILITY_SUMS] += 3;
                }
            }
            tails[action] = expectation[0]; rewards[action] = expectation[1];
            successes[action] = std::max(0.0, std::min(1.0, expectation[2]));
            if (successes[action] != expectation[2]) ++counts[PROBABILITY_CLOSURES];
            values[action] = score+expectation[0];
        }
        if (best < 0 || values[action] > best_value) { best = action; best_value = values[action]; }
    }
    return best;
}
