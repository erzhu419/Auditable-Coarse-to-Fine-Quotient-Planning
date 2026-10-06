// Read-only V299 diagnostics share the unchanged V135/V120 transition programs.
#include "controlled_predictive_frozen_leaf_planning_v135.cpp"

extern "C" double ntuple_value_v120(const int32_t*, const int32_t*, int, const double*);

namespace mechanism_v299 {
enum Extra { DIRECT_TERMINAL_CHECKS=30, FEATURE_EXTRACTIONS, FEATURE_OCCURRENCES,
    FEATURE_DIGIT_READS, FEATURE_ADDRESS_OPERATIONS, QUERY_SHIFT_ADDITIONS,
    SECOND_ACTION_COMPARISONS, ROOT_ACTION_COMPARISONS, FIXED_PROBABILITY_PRODUCTS,
    FIXED_PROBABILITY_SUMS, RESELECTED_SECOND_ACTIONS };

void features(const int32_t* board, const int32_t* patterns, int radix,
              int64_t* output, uint64_t* counts) {
    int64_t stride=1;
    for (int i=0; i<6; ++i) stride*=radix;
    for (int tuple=0; tuple<32; ++tuple) {
        int64_t address=0;
        for (int digit=0; digit<6; ++digit)
            address=address*radix+board[patterns[tuple*6+digit]];
        output[tuple]=(tuple/8)*stride+address;
    }
    ++counts[FEATURE_EXTRACTIONS]; counts[FEATURE_OCCURRENCES]+=32;
    counts[FEATURE_DIGIT_READS]+=192; counts[FEATURE_ADDRESS_OPERATIONS]+=192;
}

void charge_prediction_features(uint64_t predictions, uint64_t* counts) {
    counts[FEATURE_EXTRACTIONS]+=predictions;
    counts[FEATURE_OCCURRENCES]+=32*predictions;
    counts[FEATURE_DIGIT_READS]+=192*predictions;
    counts[FEATURE_ADDRESS_OPERATIONS]+=192*predictions;
}

int second(const int32_t* board, const int32_t* patterns, int radix,
    const double* weights, const int32_t* table, const int64_t* scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert,
    double* converted, uint64_t* counts) {
    ++counts[20]; ++counts[3];
    if (*std::max_element(board,board+16)>=radix) {
        ++counts[6]; ++counts[27]; return -2;
    }
    int32_t moved[64], legal[4]; int64_t rewards[4]; double tails[4], values[4];
    const uint64_t swipes=counts[0], predictions=counts[4];
    const int raw=ntuple_choose_v120(board,patterns,radix,weights,table,scores,cells,
        1.,source_goal,moved,rewards,tails,values,legal,counts);
    counts[21]+=counts[0]-swipes;
    charge_prediction_features(counts[4]-predictions,counts);
    if (raw<0) { ++counts[26]; return -1; }
    int best=-1; double maximum=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        if (!legal[action]) continue;
        const bool winning=*std::max_element(moved+16*action,moved+16*(action+1))>=radix;
        converted[action]=winning ? static_cast<double>(rewards[action])/2048.+goal
            : convert ? values[action]+failure_shift+success_shift : values[action];
        if (!winning && convert) counts[QUERY_SHIFT_ADDITIONS]+=2;
        ++counts[SECOND_ACTION_COMPARISONS];
        if (converted[action]>maximum) { maximum=converted[action]; best=action; }
    }
    return best;
}
}

extern "C" void mechanism_features_v299(const int32_t* boards, int n,
    const int32_t* patterns, int radix, int64_t* output, uint64_t* counts) {
    for (int i=0; i<n; ++i)
        mechanism_v299::features(boards+16*i,patterns,radix,output+32*i,counts);
}

extern "C" void mechanism_predict_v299(const int32_t* boards, int n,
    const int32_t* patterns, int radix, const double* weights, double goal,
    double failure_shift, double success_shift, double* output, uint64_t* counts) {
    for (int i=0; i<n; ++i) {
        const int32_t* board=boards+16*i;
        ++counts[mechanism_v299::DIRECT_TERMINAL_CHECKS];
        if (*std::max_element(board,board+16)>=radix) {
            output[i]=goal; ++counts[6];
        } else {
            output[i]=ntuple_value_v120(board,patterns,radix,weights)+failure_shift+success_shift;
            ++counts[4]; counts[5]+=32;
            counts[mechanism_v299::QUERY_SHIFT_ADDITIONS]+=2;
            mechanism_v299::charge_prediction_features(1,counts);
        }
    }
}

extern "C" void mechanism_h2_v299(const int32_t* boards, int n,
    const int32_t* patterns, int radix, const double* source_weights,
    const double* current_weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert, const double* probabilities,
    double* source_q, double* current_q, double* fixed_q, int32_t* legal_output,
    int32_t* selected, uint64_t* counts) {
    using namespace mechanism_v299;
    for (int root=0; root<n; ++root) {
        const int32_t* board=boards+16*root;
        ++counts[3];
        if (*std::max_element(board,board+16)>=radix) {
            ++counts[6];
            std::fill(selected+3*root,selected+3*root+3,-2); continue;
        }
        double maxima[3]={-std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()};
        for (int action=0; action<4; ++action) {
            int32_t after[16]; std::copy(board,board+16,after); int64_t reward=0;
            ++counts[0]; ++counts[17];
            for (int line=0; line<4; ++line) {
                const int32_t* line_cells=cells+16*action+4*line;
                int index=0;
                for (int i=0; i<4; ++i) index=index*radix+board[line_cells[i]];
                for (int i=0; i<4; ++i) after[line_cells[i]]=table[4*index+i];
                reward+=line_scores[index]; ++counts[1];
            }
            if (std::equal(board,board+16,after)) continue;
            legal_output[4*root+action]=1; ++counts[2]; ++counts[3]; ++counts[18];
            double expectations[3]={0.,0.,0.};
            if (*std::max_element(after,after+16)>=radix) {
                std::fill(expectations,expectations+3,goal); ++counts[6]; ++counts[19];
            } else {
                int empty=0; for (int i=0; i<16; ++i) empty+=after[i]==0;
                for (int cell=0; cell<16; ++cell) {
                    if (after[cell]) continue;
                    for (int rank=1; rank<=2; ++rank) {
                        int32_t spawned[16]; std::copy(after,after+16,spawned); spawned[cell]=rank;
                        ++counts[22]; ++counts[rank==1 ? 23 : 24]; ++counts[25];
                        double source[4],current[4];
                        const int s=second(spawned,patterns,radix,source_weights,table,line_scores,
                            cells,source_goal,goal,failure,failure_shift,success_shift,convert,source,counts);
                        const int m=second(spawned,patterns,radix,current_weights,table,line_scores,
                            cells,source_goal,goal,failure,failure_shift,success_shift,convert,current,counts);
                        const double sv=s==-2 ? goal : s==-1 ? -failure : source[s];
                        const double mv=m==-2 ? goal : m==-1 ? -failure : current[m];
                        const double fv=s<0 ? sv : current[s];
                        counts[RESELECTED_SECOND_ACTIONS]+=s!=m;
                        const double probability=(rank==1 ? 1.-probabilities[root] : probabilities[root])/empty;
                        expectations[0]+=probability*sv; expectations[1]+=probability*mv;
                        expectations[2]+=probability*fv;
                        counts[28]+=2; counts[29]+=2;
                        ++counts[FIXED_PROBABILITY_PRODUCTS]; ++counts[FIXED_PROBABILITY_SUMS];
                    }
                }
            }
            double* outputs[3]={source_q,current_q,fixed_q};
            for (int model=0; model<3; ++model) {
                const double value=static_cast<double>(reward)/2048.+expectations[model];
                outputs[model][4*root+action]=value; ++counts[ROOT_ACTION_COMPARISONS];
                if (value>maxima[model]) { maxima[model]=value; selected[3*root+model]=action; }
            }
        }
    }
}
