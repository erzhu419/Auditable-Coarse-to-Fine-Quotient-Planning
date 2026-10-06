// Actual standard-2048 execution; the unchanged V135 function plans the policy.
#include <algorithm>
#include <cstdint>
#include <random>

extern "C" int frozen_leaf_choose_v135(const int32_t*, const int32_t*, const int32_t*,
    int, int, const double*, const int32_t*, const int64_t*, const int32_t*,
    double, double, double, double, double, double, double, int,
    int32_t*, int64_t*, double*, double*, int32_t*, uint64_t*);

namespace {
enum EnvironmentCount { TRANSITIONS, RANDOM_DRAWS, EXPLICIT_SWIPES, ALL_SWIPES,
    STATUS_CHECKS, STATUS_SWIPES };
enum RolloutCount { ROLLOUTS, RNG_STARTS, CONTINUATION_CHOICES };

double uniform(std::mt19937_64& rng) {
    return static_cast<double>(rng() >> 11)*0x1.0p-53;
}

// Sorted names DOWN, LEFT, RIGHT, UP. Execution does not read learned tables.
int cell(int action, int line, int position) {
    if (action == 0) return (3-position)*4+line;
    if (action == 1) return line*4+position;
    if (action == 2) return line*4+3-position;
    return position*4+line;
}

bool ground_swipe(const int32_t* board, int action, int32_t* after, int64_t& score) {
    score = 0;
    for (int line = 0; line < 4; ++line) {
        int32_t packed[4], merged[4] = {0, 0, 0, 0};
        int n = 0, output = 0;
        for (int pos = 0; pos < 4; ++pos) {
            const int rank = board[cell(action,line,pos)];
            if (rank) packed[n++] = rank;
        }
        for (int pos = 0; pos < n;) {
            int rank = packed[pos++];
            if (pos < n && packed[pos] == rank) {
                ++rank; ++pos; score += int64_t(1) << rank;
            }
            merged[output++] = rank;
        }
        for (int pos = 0; pos < 4; ++pos) after[cell(action,line,pos)] = merged[pos];
    }
    return !std::equal(board,board+16,after);
}

int ground_status(const int32_t* board, int goal, uint64_t* counts) {
    ++counts[STATUS_CHECKS];
    if (*std::max_element(board,board+16) >= goal) return 1;
    bool active = false;
    for (int action = 0; action < 4; ++action) {
        int32_t after[16]; int64_t score;
        active = ground_swipe(board,action,after,score) || active;
        ++counts[ALL_SWIPES]; ++counts[STATUS_SWIPES];
    }
    return active ? 0 : -1;
}

void ground_spawn(int32_t* board, double p_four, std::mt19937_64& rng,
                  uint64_t* counts) {
    int empty[16], n = 0;
    for (int i = 0; i < 16; ++i) if (!board[i]) empty[n++] = i;
    const double cell_draw = uniform(rng), rank_draw = uniform(rng);
    counts[RANDOM_DRAWS] += 2;
    board[empty[static_cast<int>(cell_draw*n)]] = rank_draw < 1.-p_four ? 1 : 2;
}
}

extern "C" void native_common_draws_v285(uint64_t seed, int n_steps, double* output) {
    std::mt19937_64 rng(seed);
    for (int i = 0; i < 2*n_steps; ++i) output[i] = uniform(rng);
}

extern "C" int native_continuation_v285(const int32_t* root,
    const int32_t* actions, int n_actions, const uint64_t* seeds, int n_replicas,
    int max_steps, const int32_t* patterns, const int32_t* extra, int radix,
    int mode, const double* weights, const int32_t* table,
    const int64_t* line_scores, const int32_t* cells, double source_goal,
    double target_goal, double failure, double failure_shift, double success_shift,
    double model_p_four, double environment_p_four, int convert,
    int64_t* metrics, int32_t* final_boards,
    uint64_t* environment_counts, uint64_t* planning_counts, uint64_t* rollout_counts) {
    for (int action_index = 0; action_index < n_actions; ++action_index) {
        for (int replica = 0; replica < n_replicas; ++replica) {
            // No action component in the seed: branch draws share step prefixes.
            std::mt19937_64 rng(seeds[replica]);
            ++rollout_counts[ROLLOUTS]; ++rollout_counts[RNG_STARTS];
            int32_t board[16]; std::copy(root,root+16,board);
            int64_t first_score = 0, total_score = 0;
            int status = 0, steps = 0, selected = actions[action_index];
            while (steps < max_steps && status == 0) {
                if (steps) {
                    int32_t moved[64], legal[4]; int64_t scores[4];
                    double tails[4], values[4];
                    ++rollout_counts[CONTINUATION_CHOICES];
                    selected = frozen_leaf_choose_v135(board,patterns,extra,radix,mode,
                        weights,table,line_scores,cells,source_goal,target_goal,failure,
                        failure_shift,success_shift,1.-model_p_four,model_p_four,convert,
                        moved,scores,tails,values,legal,planning_counts);
                    if (selected < 0) return 2;
                }
                int32_t after[16]; int64_t gained;
                ++environment_counts[EXPLICIT_SWIPES]; ++environment_counts[ALL_SWIPES];
                if (!ground_swipe(board,selected,after,gained)) return 1;
                if (!steps) first_score = gained;
                total_score += gained;
                std::copy(after,after+16,board);
                // V115 spawns even when this action has already formed a goal.
                ground_spawn(board,environment_p_four,rng,environment_counts);
                ++environment_counts[TRANSITIONS]; ++steps;
                status = ground_status(board,radix,environment_counts);
            }
            if (!status) status = 2;  // True nonterminal budget cutoff.
            const int index = action_index*n_replicas+replica;
            metrics[4*index] = first_score;
            metrics[4*index+1] = total_score;
            metrics[4*index+2] = steps;
            metrics[4*index+3] = status;
            std::copy(board,board+16,final_boards+16*index);
        }
    }
    return 0;
}
