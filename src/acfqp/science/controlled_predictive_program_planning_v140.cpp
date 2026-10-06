#include <algorithm>
#include <cstdint>
#include <limits>
#include <random>

extern "C" int ntuple_choose_v120(const int32_t*, const int32_t*, int, const double*,
    const int32_t*, const int64_t*, const int32_t*, double, double, int32_t*, int64_t*,
    double*, double*, int32_t*, uint64_t*);

namespace {
enum Count { SWIPES, TABLE_LINES, LEGAL, TERMINAL_CHECKS, PREDICTIONS, TABLE_READS, GOALS,
    ROOT_SWIPES, PROGRAM_SWIPES, BOOTSTRAP_SWIPES, BUDGET, USED, ROLLOUTS, ROLLOUT_ACTIONS,
    SAMPLES, UNIFORMS, RNG_STARTS, TREE_CALLS, FEATURE_READS, NEIGHBOR_CHECKS, FEATURE_VALUES,
    TREE_BRANCHES, TREE_ORDER_READS, LINE_LOOKUPS, LINE_TRIALS, LINE_GUARDS, LINE_HITS,
    LINE_MISSES, LINE_OUTPUTS, LINE_REWARDS, LINE_GATHERS, LINE_SCATTERS, LINE_MASK_READS,
    GUARD_RANK_READS, BOUND_RANK_READS, ROOT_LEGAL, ROOT_GOALS, LEAF_CHOOSES, LEAF_LOSSES,
    ROLLOUT_LOSSES, ROLLOUT_GOALS, EARLY_BOOTSTRAPS, DIRECT_CALLS, ROOT_EMPTY_READS,
    SPAWN_EMPTY_READS, SPAWN_WRITES, RETURN_ADDITIONS, MEAN_ADDITIONS, MASK_TESTS };
constexpr int PROGRAM_WIDTH=30;

int bind_line(const int32_t* line, const int32_t* programs, int nprograms,
              int32_t* output, int64_t& score, uint64_t* counts) {
    ++counts[LINE_LOOKUPS]; counts[LINE_MASK_READS]+=4;
    int mask=0;
    for (int i=0; i<4; ++i) if (!line[i]) mask|=1<<i;
    for (int index=0; index<nprograms; ++index) {
        const int32_t* p=programs+PROGRAM_WIDTH*index;
        ++counts[MASK_TESTS];
        if (p[0]!=mask) continue;
        ++counts[LINE_TRIALS]; bool accepted=true;
        for (int guard=0; guard<p[1]; ++guard) {
            const int32_t* g=p+3+5*guard;
            ++counts[LINE_GUARDS]; counts[GUARD_RANK_READS]+=2;
            if ((line[g[0]]+g[1]==line[g[2]]+g[3])!=static_cast<bool>(g[4])) {
                accepted=false; break;
            }
        }
        if (!accepted) continue;
        for (int cell=0; cell<4; ++cell) {
            const int32_t* expression=p+18+2*cell;
            output[cell]=expression[0]<0 ? 0 : line[expression[0]]+expression[1];
            ++counts[LINE_OUTPUTS]; counts[BOUND_RANK_READS]+=expression[0]>=0;
        }
        score=0;
        for (int term=0; term<p[2]; ++term) {
            const int32_t* expression=p+26+2*term;
            score+=int64_t{1}<<(line[expression[0]]+expression[1]);
            ++counts[LINE_REWARDS]; ++counts[BOUND_RANK_READS];
        }
        ++counts[LINE_HITS]; return index;
    }
    ++counts[LINE_MISSES]; return -1;
}

// No transition table or rewrite primitive participates in program execution.
int program_swipe(const int32_t* board, int action, const int32_t* cells,
                  const int32_t* programs, int nprograms, int32_t* after,
                  int64_t& score, uint64_t* counts) {
    ++counts[SWIPES]; ++counts[PROGRAM_SWIPES]; ++counts[USED]; score=0;
    for (int line=0; line<4; ++line) {
        const int32_t* positions=cells+16*action+4*line;
        int32_t input[4], output[4]; int64_t gained=0;
        for (int i=0; i<4; ++i) input[i]=board[positions[i]];
        ++counts[LINE_GATHERS];
        if (bind_line(input, programs, nprograms, output, gained, counts)<0) return -1;
        for (int i=0; i<4; ++i) after[positions[i]]=output[i];
        ++counts[LINE_SCATTERS]; score+=gained;
    }
    const bool changed=!std::equal(board, board+16, after);
    counts[LEGAL]+=changed; counts[TERMINAL_CHECKS]+=changed;
    return changed;
}

void features(const int32_t* board, bool* result, uint64_t* counts) {
    int empty=0, adjacent=0, maximum=0;
    for (int i=0; i<16; ++i) { empty+=board[i]==0; maximum=std::max(maximum,board[i]); }
    for (int row=0; row<4; ++row) for (int col=0; col<4; ++col) {
        const int i=4*row+col;
        if (col<3) adjacent+=board[i]>0 && board[i]==board[i+1];
        if (row<3) adjacent+=board[i]>0 && board[i]==board[i+4];
    }
    result[0]=empty<=2; result[1]=empty<=4; result[2]=empty<=8;
    result[3]=adjacent<=0; result[4]=adjacent<=2; result[5]=adjacent<=4;
    const int corners[]={0,3,12,15};
    for (int i=0; i<4; ++i) result[6+i]=maximum>0 && board[corners[i]]==maximum;
    for (int edge=0; edge<4; ++edge) {
        result[10+edge]=false;
        for (int i=0; i<4; ++i) {
            const int position=edge==0 ? i : edge==1 ? 12+i : edge==2 ? 4*i : 4*i+3;
            result[10+edge]|=maximum>0 && board[position]==maximum;
        }
    }
    counts[FEATURE_READS]+=16; counts[NEIGHBOR_CHECKS]+=24; counts[FEATURE_VALUES]+=14;
}

const int32_t* order(const int32_t* board, int previous, const int32_t* trees, uint64_t* counts) {
    bool values[14]; features(board,values,counts); ++counts[TREE_CALLS];
    int index=0;
    while (trees[previous*35+index*5]>=0) {
        const int predicate=trees[previous*35+index*5];
        index=2*index+1+values[predicate]; ++counts[TREE_BRANCHES];
    }
    counts[TREE_ORDER_READS]+=4;
    return trees+previous*35+index*5+1;
}

void spawn(int32_t* board, double probability_rank1, std::mt19937_64& rng, uint64_t* counts) {
    int empty[16], n=0;
    for (int cell=0; cell<16; ++cell) if (!board[cell]) empty[n++]=cell;
    const double ucell=(rng()>>11)*0x1.0p-53, urank=(rng()>>11)*0x1.0p-53;
    board[empty[static_cast<int>(ucell*n)]]=urank<probability_rank1 ? 1 : 2;
    counts[SPAWN_EMPTY_READS]+=16; counts[UNIFORMS]+=2; ++counts[SPAWN_WRITES]; ++counts[SAMPLES];
}

double h1(const int32_t* board, const int32_t* patterns, int radix, const double* weights,
          const int32_t* table, const int64_t* scores, const int32_t* cells,
          double source_goal, double goal, double failure, double failure_shift,
          double success_shift, int convert, uint64_t* counts) {
    ++counts[LEAF_CHOOSES]; ++counts[TERMINAL_CHECKS];
    if (*std::max_element(board,board+16)>=radix) { ++counts[GOALS]; return goal; }
    int32_t moved[64], legal[4]; int64_t gained[4]; double tails[4], values[4];
    const uint64_t before=counts[SWIPES];
    const int best=ntuple_choose_v120(board,patterns,radix,weights,table,scores,cells,
        1.,source_goal,moved,gained,tails,values,legal,counts);
    counts[BOOTSTRAP_SWIPES]+=counts[SWIPES]-before; counts[USED]+=counts[SWIPES]-before;
    if (best<0) { ++counts[LEAF_LOSSES]; return -failure; }
    double chosen=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        if (!legal[action]) continue;
        const bool won=*std::max_element(moved+16*action,moved+16*(action+1))>=radix;
        const double value=won ? static_cast<double>(gained[action])/2048.+goal
            : convert ? values[action]+failure_shift+success_shift : values[action];
        if (value>chosen) chosen=value;
    }
    return chosen;
}
}

extern "C" int program_line_v140(const int32_t* line, const int32_t* programs,
    int nprograms, int32_t* output, int64_t* score, uint64_t* counts) {
    return bind_line(line,programs,nprograms,output,*score,counts);
}

extern "C" void program_order_v140(const int32_t* board, int previous,
    const int32_t* trees, int32_t* output, uint64_t* counts) {
    const int32_t* selected=order(board,previous,trees,counts);
    std::copy(selected,selected+4,output);
}

extern "C" double program_h1_v140(const int32_t* board, const int32_t* patterns, int radix,
    const double* weights, const int32_t* table, const int64_t* scores, const int32_t* cells,
    double source_goal, double goal, double failure, double failure_shift,
    double success_shift, int convert, uint64_t* counts) {
    return h1(board,patterns,radix,weights,table,scores,cells,source_goal,goal,failure,
        failure_shift,success_shift,convert,counts);
}

extern "C" int program_choose_v140(const int32_t* board, const int32_t* patterns, int radix,
    const double* weights, const int32_t* table, const int64_t* line_scores, const int32_t* cells,
    const int32_t* programs, int nprograms, const int32_t* trees, double source_goal,
    double goal, double failure, double failure_shift, double success_shift, double probability_rank1,
    int convert, int direct, int previous, uint64_t simulation_seed, int32_t* moved,
    int64_t* scores, double* tails, double* values, int32_t* legal, int32_t* stats, uint64_t* counts) {
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
    if (direct) {
        ++counts[DIRECT_CALLS];
        const int32_t* selected=order(board,previous,trees,counts);
        int best=-1;
        for (int position=0; position<4; ++position) {
            const int action=selected[position];
            if (!legal[action]) continue;
            values[action]=4-position; tails[action]=values[action]-static_cast<double>(scores[action])/2048.;
            if (best<0) best=action;
        }
        return best;
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
                std::seed_seq seed{static_cast<uint32_t>(simulation_seed),
                    static_cast<uint32_t>(simulation_seed>>32),static_cast<uint32_t>(action),
                    static_cast<uint32_t>(replica)};
                std::mt19937_64 rng(seed); ++counts[RNG_STARTS]; ++counts[ROLLOUTS];
                int32_t current[16]; std::copy(after,after+16,current);
                spawn(current,probability_rank1,rng,counts);
                double result=0.; int last=action; bool terminal=false;
                for (int depth=0; depth<3; ++depth) {
                    if (allowance-static_cast<int>(counts[USED]-before)<8) {
                        ++counts[EARLY_BOOTSTRAPS]; break;
                    }
                    const int32_t* selected=order(current,last,trees,counts);
                    int32_t next[16]; int64_t gained=0; int chosen=-1;
                    for (int position=0; position<4; ++position) {
                        const int changed=program_swipe(current,selected[position],cells,programs,
                            nprograms,next,gained,counts);
                        if (changed<0) return -3;
                        if (changed) { chosen=selected[position]; break; }
                    }
                    if (chosen<0) { result-=failure; ++counts[ROLLOUT_LOSSES]; terminal=true; break; }
                    ++counts[ROLLOUT_ACTIONS]; ++counts[RETURN_ADDITIONS];
                    result+=static_cast<double>(gained)/2048.; last=chosen;
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
