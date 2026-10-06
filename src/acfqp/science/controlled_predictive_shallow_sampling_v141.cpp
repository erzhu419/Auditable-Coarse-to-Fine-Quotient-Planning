// Shared V140 primitives preserve the initial sampled spawn and H1 semantics.
#include "controlled_predictive_program_planning_v140.cpp"

namespace {
std::mt19937_64 initial_rng(uint64_t simulation_seed, int action, int replica) {
    std::seed_seq seed{static_cast<uint32_t>(simulation_seed),
        static_cast<uint32_t>(simulation_seed>>32), static_cast<uint32_t>(action),
        static_cast<uint32_t>(replica)};
    return std::mt19937_64(seed);
}
}

extern "C" void shallow_first_spawn_v141(const int32_t* after, double probability_rank1,
    uint64_t simulation_seed, int action, int replica, int32_t* spawned, uint64_t* counts) {
    auto rng=initial_rng(simulation_seed,action,replica);
    ++counts[RNG_STARTS];
    std::copy(after,after+16,spawned);
    spawn(spawned,probability_rank1,rng,counts);
}

extern "C" int shallow_choose_v141(const int32_t* board, const int32_t* patterns, int radix,
    const double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, const int32_t* programs, int nprograms, double source_goal,
    double goal, double failure, double failure_shift, double success_shift,
    double probability_rank1, int convert, uint64_t simulation_seed, int32_t* moved,
    int64_t* scores, double* tails, double* values, int32_t* legal, int32_t* stats,
    uint64_t* counts) {
    ++counts[TERMINAL_CHECKS];
    if (*std::max_element(board,board+16)>=radix) { ++counts[GOALS]; return -2; }
    counts[BUDGET]+=4;
    for (int action=0; action<4; ++action) {
        ++counts[ROOT_SWIPES];
        const int changed=program_swipe(board,action,cells,programs,nprograms,
            moved+16*action,scores[action],counts);
        if (changed<0) return -3;
        legal[action]=changed; counts[ROOT_LEGAL]+=changed;
    }
    int best=-1; double best_value=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        if (!legal[action]) continue;
        const int32_t* after=moved+16*action;
        if (*std::max_element(after,after+16)>=radix) {
            ++counts[ROOT_GOALS]; ++counts[GOALS]; tails[action]=goal;
        } else {
            int empty=0;
            for (int cell=0; cell<16; ++cell) empty+=after[cell]==0;
            counts[ROOT_EMPTY_READS]+=16;
            const int budget=8*empty, trajectories=std::max(1,budget/16);
            stats[3*action]=budget; stats[3*action+2]=trajectories; counts[BUDGET]+=budget;
            const uint64_t action_before=counts[USED]; double total=0.;
            for (int replica=0; replica<trajectories; ++replica) {
                auto rng=initial_rng(simulation_seed,action,replica);
                ++counts[RNG_STARTS]; ++counts[ROLLOUTS];
                int32_t current[16]; std::copy(after,after+16,current);
                spawn(current,probability_rank1,rng,counts);
                total+=h1(current,patterns,radix,weights,table,line_scores,cells,
                    source_goal,goal,failure,failure_shift,success_shift,convert,counts);
                ++counts[MEAN_ADDITIONS];
            }
            stats[3*action+1]=static_cast<int>(counts[USED]-action_before);
            tails[action]=total/trajectories;
        }
        values[action]=static_cast<double>(scores[action])/2048.+tails[action];
        if (best<0 || values[action]>best_value) { best=action; best_value=values[action]; }
    }
    return best;
}
