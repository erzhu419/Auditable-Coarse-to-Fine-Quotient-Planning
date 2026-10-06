// V140 root execution, spawn stream and final bootstrap remain unchanged.
#include "controlled_predictive_program_planning_v140.cpp"

namespace {
enum ContinuationCount { CONT_CHOICES=MASK_TESTS+1, CONT_SWIPES, CONT_PREDICTIONS,
    CONT_GOALS, CONT_LOSSES };

int h1_action(const int32_t* board, const int32_t* patterns, int radix,
    const double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert, int32_t* after,
    int64_t& score, double& value, uint64_t* counts) {
    ++counts[CONT_CHOICES]; ++counts[TERMINAL_CHECKS];
    std::copy(board,board+16,after); score=0;
    if (*std::max_element(board,board+16)>=radix) {
        ++counts[GOALS]; ++counts[CONT_GOALS]; value=goal; return -2;
    }
    int32_t moved[64], legal[4]; int64_t gained[4]; double tails[4], values[4];
    const uint64_t before=counts[SWIPES], predictions=counts[PREDICTIONS];
    const int raw=ntuple_choose_v120(board,patterns,radix,weights,table,line_scores,cells,
        1.,source_goal,moved,gained,tails,values,legal,counts);
    counts[CONT_SWIPES]+=counts[SWIPES]-before; counts[USED]+=counts[SWIPES]-before;
    counts[CONT_PREDICTIONS]+=counts[PREDICTIONS]-predictions;
    if (raw<0) { ++counts[CONT_LOSSES]; value=-failure; return -1; }
    int best=-1; value=-std::numeric_limits<double>::infinity();
    // Conversion can change the winner when only some candidates reach the goal.
    for (int action=0; action<4; ++action) {
        if (!legal[action]) continue;
        const bool won=*std::max_element(moved+16*action,moved+16*(action+1))>=radix;
        const double candidate=won ? static_cast<double>(gained[action])/2048.+goal
            : convert ? values[action]+failure_shift+success_shift : values[action];
        if (best<0 || candidate>value) { best=action; value=candidate; }
    }
    std::copy(moved+16*best,moved+16*(best+1),after); score=gained[best]; return best;
}

std::mt19937_64 continuation_rng(uint64_t simulation_seed, int action, int replica) {
    std::seed_seq seed{static_cast<uint32_t>(simulation_seed),
        static_cast<uint32_t>(simulation_seed>>32),static_cast<uint32_t>(action),
        static_cast<uint32_t>(replica)};
    return std::mt19937_64(seed);
}
}

extern "C" int continuation_action_v142(const int32_t* board, const int32_t* patterns,
    int radix, const double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert, int32_t* after,
    int64_t* score, double* value, uint64_t* counts) {
    return h1_action(board,patterns,radix,weights,table,line_scores,cells,source_goal,
        goal,failure,failure_shift,success_shift,convert,after,*score,*value,counts);
}

extern "C" int continuation_choose_v142(const int32_t* board, const int32_t* patterns,
    int radix, const double* weights, const int32_t* table, const int64_t* line_scores,
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
                const int allowance=budget/trajectories+(replica<budget%trajectories);
                const uint64_t before=counts[USED];
                auto rng=continuation_rng(simulation_seed,action,replica);
                ++counts[RNG_STARTS]; ++counts[ROLLOUTS];
                int32_t current[16]; std::copy(after,after+16,current);
                spawn(current,probability_rank1,rng,counts);
                double result=0.; bool terminal=false;
                for (int depth=0; depth<3; ++depth) {
                    if (allowance-static_cast<int>(counts[USED]-before)<8) {
                        ++counts[EARLY_BOOTSTRAPS]; break;
                    }
                    int32_t next[16]; int64_t gained=0; double chosen_value=0.;
                    const int chosen=h1_action(current,patterns,radix,weights,table,line_scores,
                        cells,source_goal,goal,failure,failure_shift,success_shift,convert,
                        next,gained,chosen_value,counts);
                    if (chosen<0) {
                        result+=chosen_value;
                        ++counts[chosen==-2 ? ROLLOUT_GOALS : ROLLOUT_LOSSES];
                        terminal=true; break;
                    }
                    ++counts[ROLLOUT_ACTIONS]; ++counts[RETURN_ADDITIONS];
                    result+=static_cast<double>(gained)/2048.;
                    std::copy(next,next+16,current);
                    if (*std::max_element(current,current+16)>=radix) {
                        result+=goal; ++counts[ROLLOUT_GOALS]; ++counts[GOALS]; terminal=true; break;
                    }
                    spawn(current,probability_rank1,rng,counts);
                }
                if (!terminal) result+=h1(current,patterns,radix,weights,table,line_scores,cells,
                    source_goal,goal,failure,failure_shift,success_shift,convert,counts);
                if (counts[USED]-before>static_cast<uint64_t>(allowance)) return -4;
                total+=result; ++counts[MEAN_ADDITIONS];
            }
            stats[3*action+1]=static_cast<int>(counts[USED]-action_before);
            tails[action]=total/trajectories;
        }
        values[action]=static_cast<double>(scores[action])/2048.+tails[action];
        if (best<0 || values[action]>best_value) { best=action; best_value=values[action]; }
    }
    return best;
}
