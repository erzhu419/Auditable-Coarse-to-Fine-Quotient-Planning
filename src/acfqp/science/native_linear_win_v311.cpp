// Two active linear heads: factual reward suffix and unclipped terminal WIN regression.
#include "native_value_stream_v286.cpp"
#include <cmath>
#include <vector>

namespace {
enum LinearLearning { SAMPLES, COMBINED_PREDICTIONS, ALL_LOOKUPS, ALL_WRITES,
    FEATURE_OCCURRENCES, REWARD_PREDICTIONS, WIN_PREDICTIONS, REWARD_LOOKUPS,
    WIN_LOOKUPS, REWARD_WRITES, WIN_WRITES };
enum LinearTarget { GAME_LABELS, LABEL_ASSIGNMENTS, REWARD_SUFFIX_ASSIGNMENTS,
    REWARD_SUFFIX_ADDITIONS, LINEAR_GOAL_CHECKS, WINNING_SKIPS,
    UTILITY_SUFFIX_ASSIGNMENTS, UTILITY_SUFFIX_ADDITIONS };
enum LinearNormalization { FIT_GAMES, ADDRESS_EXTRACTIONS, ADDRESS_OCCURRENCES,
    ADDRESS_DIGIT_READS, ADDRESS_MULTIPLY_ADDS, SORT_CALLS, SORT_ITEMS,
    SORT_COMPARISONS, DENOMINATOR_OCCURRENCE_VISITS, UNIQUE_ADDRESSES,
    REWARD_GRADIENT_PRODUCTS, REWARD_GRADIENT_SUMS, WIN_GRADIENT_PRODUCTS,
    WIN_GRADIENT_SUMS, NORMALIZATION_DIVISIONS, UPDATE_PRODUCTS, GAME_COMMITS,
    REWARD_COMMITS, WIN_COMMITS, REWARD_PARAMETER_WRITES, WIN_PARAMETER_WRITES,
    ADDRESS_DENOMINATOR_SEARCHES, ADDRESS_DENOMINATOR_COMPARISONS,
    FEATURE_BUFFER_BYTES_PEAK };
enum LinearRepresentation { LINEAR_WIN_LOOKUPS, COMBINED_ADDITIONS, COMBINED_MULTIPLICATIONS };

void linear_addresses(const int32_t* board,const int32_t* patterns,int radix,int64_t* output) {
    int64_t stride=1;
    for (int digit=0; digit<6; ++digit) stride*=radix;
    for (int tuple=0; tuple<32; ++tuple) {
        int64_t address=0;
        for (int digit=0; digit<6; ++digit) address=address*radix+board[patterns[tuple*6+digit]];
        output[tuple]=(tuple/8)*stride+address;
    }
}

double linear_ntuple(const int64_t* addresses,const double* weights) {
    double value=0.;
    for (int occurrence=0; occurrence<32; ++occurrence) value+=weights[addresses[occurrence]];
    return value;
}

double linear_win(const int64_t* addresses,const double* weights,uint64_t* representation) {
    representation[LINEAR_WIN_LOOKUPS]+=32;
    return linear_ntuple(addresses,weights);
}

double linear_combine(double reward,double win,uint64_t* representation) {
    representation[COMBINED_ADDITIONS]+=2; ++representation[COMBINED_MULTIPLICATIONS];
    return reward+8.*(win-.5);
}

void linear_prediction(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* win,double* output,uint64_t* representation) {
    int64_t addresses[32]; linear_addresses(board,patterns,radix,addresses);
    output[0]=linear_ntuple(addresses,reward);
    output[1]=linear_win(addresses,win,representation);
    output[2]=linear_combine(output[0],output[1],representation);
}

void linear_swipe(const int32_t* board,int action,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,int radix,int32_t* after,
    int64_t& score,uint64_t* planning) {
    std::copy(board,board+16,after); score=0; ++planning[0];
    for (int line=0; line<4; ++line) {
        const int32_t* positions=cells+16*action+4*line; int index=0;
        for (int i=0; i<4; ++i) index=index*radix+board[positions[i]];
        for (int i=0; i<4; ++i) after[positions[i]]=table[4*index+i];
        score+=line_scores[index]; ++planning[1];
    }
}

double linear_leaf_value(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* win,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,uint64_t* planning,uint64_t* representation) {
    ++planning[20]; ++planning[3];
    if (*std::max_element(board,board+16)>=radix) { ++planning[6]; ++planning[27]; return 4.; }
    bool legal=false; double chosen=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t after[16]; int64_t score;
        linear_swipe(board,action,table,line_scores,cells,radix,after,score,planning); ++planning[21];
        if (std::equal(board,board+16,after)) continue;
        legal=true; ++planning[2]; ++planning[3]; double tail;
        if (*std::max_element(after,after+16)>=radix) { ++planning[6]; tail=4.; }
        else {
            double predicted[3]; linear_prediction(after,patterns,radix,reward,win,predicted,representation);
            tail=predicted[2]; ++planning[4]; planning[5]+=32;
        }
        const double value=score/2048.+tail;
        if (value>chosen) chosen=value;
    }
    if (!legal) { ++planning[26]; return -4.; }
    return chosen;
}
}

extern "C" void linear_predict_v311(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* win,double* output,uint64_t* representation) {
    linear_prediction(board,patterns,radix,reward,win,output,representation);
}

extern "C" int linear_choose_v311(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* win,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double model_p,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation) {
    ++planning[3];
    if (*std::max_element(board,board+16)>=radix) { ++planning[6]; return -2; }
    int best=-1; double maximum=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t* after=moved+16*action;
        linear_swipe(board,action,table,line_scores,cells,radix,after,scores[action],planning); ++planning[17];
        legal[action]=!std::equal(board,board+16,after);
        if (!legal[action]) continue;
        ++planning[2]; ++planning[3]; ++planning[18];
        if (*std::max_element(after,after+16)>=radix) {
            tails[action]=4.; ++planning[6]; ++planning[19];
        } else {
            int empty=0; for (int cell=0; cell<16; ++cell) empty+=after[cell]==0;
            double expectation=0.;
            for (int cell=0; cell<16; ++cell) if (!after[cell]) for (int rank=1; rank<=2; ++rank) {
                int32_t spawned[16]; std::copy(after,after+16,spawned); spawned[cell]=rank;
                ++planning[22]; ++planning[rank==1 ? 23 : 24]; ++planning[25];
                const double tail=linear_leaf_value(spawned,patterns,radix,reward,win,
                    table,line_scores,cells,planning,representation);
                expectation+=((rank==1 ? 1.-model_p : model_p)/empty)*tail;
                ++planning[28]; ++planning[29];
            }
            tails[action]=expectation;
        }
        values[action]=scores[action]/2048.+tails[action];
        if (best<0 || values[action]>maximum) { best=action; maximum=values[action]; }
    }
    return best;
}

extern "C" void fit_linear_v311(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,int n_fit_games,
    const int32_t* patterns,int radix,double* reward_weights,double* win_weights,
    double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,int64_t* examples,double* values) {
    int64_t start=0;
    std::vector<double> suffixes,reward_errors,win_errors,reward_gradients,win_gradients;
    std::vector<int64_t> steps,features,sorted,unique,denominators;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game]; const double label=terminal_codes[game]==1 ? 1. : 0.;
        ++targets[GAME_LABELS]; suffixes.resize(end-start); double suffix=0.;
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix; suffix+=rewards[step];
            ++targets[REWARD_SUFFIX_ASSIGNMENTS]; ++targets[REWARD_SUFFIX_ADDITIONS];
        }
        ++normalization[FIT_GAMES]; steps.clear(); features.clear();
        for (int64_t step=start; step<end; ++step) {
            ++targets[LINEAR_GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[WINNING_SKIPS]; continue;
            }
            steps.push_back(step); features.resize(features.size()+32);
            linear_addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
            ++normalization[ADDRESS_EXTRACTIONS]; normalization[ADDRESS_OCCURRENCES]+=32;
            normalization[ADDRESS_DIGIT_READS]+=192; normalization[ADDRESS_MULTIPLY_ADDS]+=192;
        }
        sorted=features; ++normalization[SORT_CALLS]; normalization[SORT_ITEMS]+=sorted.size();
        std::sort(sorted.begin(),sorted.end(),[normalization](int64_t a,int64_t b) {
            ++normalization[SORT_COMPARISONS]; return a<b;
        });
        unique.clear(); denominators.clear();
        for (size_t i=0; i<sorted.size(); ++i) {
            ++normalization[DENOMINATOR_OCCURRENCE_VISITS];
            if (!i || sorted[i]!=sorted[i-1]) { unique.push_back(sorted[i]); denominators.push_back(1); }
            else ++denominators.back();
        }
        normalization[UNIQUE_ADDRESSES]+=unique.size();
        reward_errors.resize(steps.size()); win_errors.resize(steps.size());
        reward_gradients.assign(unique.size(),0.); win_gradients.assign(unique.size(),0.);
        // Read both heads at game start; neither is written until all residuals are fixed.
        for (size_t sample=0; sample<steps.size(); ++sample) {
            const int64_t step=steps[sample]; const int64_t* row=features.data()+32*sample;
            const double reward=linear_ntuple(row,reward_weights);
            const double win=linear_win(row,win_weights,representation);
            const double combined=linear_combine(reward,win,representation);
            reward_errors[sample]=suffixes[step-start]-reward; win_errors[sample]=label-win;
            if (!learning[SAMPLES]) {
                examples[0]=game; examples[1]=step;
                const double v[]={suffixes[step-start],label,reward,win,combined,reward_errors[sample],win_errors[sample]};
                std::copy(v,v+7,values);
            }
            examples[2]=game; examples[3]=step;
            const double v[]={suffixes[step-start],label,reward,win,combined,reward_errors[sample],win_errors[sample]};
            std::copy(v,v+7,values+7);
            ++learning[SAMPLES]; ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS];
            ++learning[WIN_PREDICTIONS]; learning[REWARD_LOOKUPS]+=32; learning[WIN_LOOKUPS]+=32;
            learning[ALL_LOOKUPS]+=64; learning[FEATURE_OCCURRENCES]+=32; ++targets[LABEL_ASSIGNMENTS];
        }
        for (size_t sample=0; sample<steps.size(); ++sample) {
            int64_t local[32]; std::copy(features.data()+32*sample,features.data()+32*(sample+1),local);
            ++normalization[SORT_CALLS]; normalization[SORT_ITEMS]+=32;
            std::sort(local,local+32,[normalization](int64_t a,int64_t b) {
                ++normalization[SORT_COMPARISONS]; return a<b;
            });
            for (int first=0; first<32;) {
                int next=first+1; while (next<32 && local[next]==local[first]) ++next;
                ++normalization[ADDRESS_DENOMINATOR_SEARCHES];
                const auto at=std::lower_bound(unique.begin(),unique.end(),local[first],[normalization](int64_t a,int64_t b) {
                    ++normalization[ADDRESS_DENOMINATOR_COMPARISONS]; return a<b;
                })-unique.begin();
                reward_gradients[at]+=(next-first)*reward_errors[sample];
                win_gradients[at]+=(next-first)*win_errors[sample];
                ++normalization[REWARD_GRADIENT_PRODUCTS]; ++normalization[REWARD_GRADIENT_SUMS];
                ++normalization[WIN_GRADIENT_PRODUCTS]; ++normalization[WIN_GRADIENT_SUMS];
                first=next;
            }
        }
        if (!unique.empty()) { ++normalization[GAME_COMMITS]; ++normalization[REWARD_COMMITS]; ++normalization[WIN_COMMITS]; }
        for (size_t address=0; address<unique.size(); ++address) {
            reward_weights[unique[address]]+=alpha*reward_gradients[address]/denominators[address];
            ++learning[REWARD_WRITES]; ++learning[ALL_WRITES]; ++normalization[REWARD_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        for (size_t address=0; address<unique.size(); ++address) {
            win_weights[unique[address]]+=alpha*win_gradients[address]/denominators[address];
            ++learning[WIN_WRITES]; ++learning[ALL_WRITES]; ++normalization[WIN_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        const uint64_t bytes=8*(suffixes.capacity()+reward_errors.capacity()+win_errors.capacity()+
            reward_gradients.capacity()+win_gradients.capacity()+steps.capacity()+features.capacity()+
            sorted.capacity()+unique.capacity()+denominators.capacity());
        normalization[FEATURE_BUFFER_BYTES_PEAK]=std::max(normalization[FEATURE_BUFFER_BYTES_PEAK],bytes);
        start=end;
    }
}

extern "C" void score_linear_v311(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,int first_game,int n_games,
    const int32_t* patterns,int radix,const double* reward,const double* win,
    double* output,double* components,uint64_t* learning,uint64_t* targets,uint64_t* representation) {
    std::vector<double> suffixes,utility_suffixes;
    int64_t start=first_game ? ends[first_game-1] : 0;
    for (int game=first_game; game<n_games; ++game) {
        const int64_t end=ends[game]; const double label=terminal_codes[game]==1 ? 1. : 0.;
        suffixes.resize(end-start); utility_suffixes.resize(end-start);
        double suffix=0.,utility_suffix=label==1. ? 4. : -4.; ++targets[GAME_LABELS];
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix; suffix+=rewards[step];
            utility_suffixes[step-start]=utility_suffix; utility_suffix+=rewards[step];
            ++targets[REWARD_SUFFIX_ASSIGNMENTS]; ++targets[REWARD_SUFFIX_ADDITIONS];
            ++targets[UTILITY_SUFFIX_ASSIGNMENTS]; ++targets[UTILITY_SUFFIX_ADDITIONS];
        }
        double sums[6]={},parts[8]={}; int count=0;
        for (int64_t step=start; step<end; ++step) {
            ++targets[LINEAR_GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) { ++targets[WINNING_SKIPS]; continue; }
            double predicted[3]; linear_prediction(afterstates+16*step,patterns,radix,reward,win,predicted,representation);
            const double target=utility_suffixes[step-start];
            const double error=predicted[2]-target,reward_error=predicted[0]-suffixes[step-start],win_error=predicted[1]-label;
            sums[1]+=error; sums[2]+=error*error; sums[3]+=std::abs(error); sums[4]+=predicted[2]; sums[5]+=target;
            parts[0]+=reward_error; parts[1]+=reward_error*reward_error; parts[2]+=std::abs(reward_error);
            parts[3]+=win_error*win_error; parts[4]+=win_error; parts[5]+=predicted[1]; ++count;
            ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS]; ++learning[WIN_PREDICTIONS];
            learning[REWARD_LOOKUPS]+=32; learning[WIN_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=64; ++targets[LABEL_ASSIGNMENTS];
        }
        sums[0]=count;
        for (int j=1; j<6; ++j) sums[j]=count ? sums[j]/count : 0.;
        for (int j=0; j<6; ++j) parts[j]=count ? parts[j]/count : 0.;
        parts[6]=label; parts[7]=count;
        std::copy(sums,sums+6,output+6*(game-first_game));
        std::copy(parts,parts+8,components+8*(game-first_game)); start=end;
    }
}

extern "C" int evaluate_linear_v311(const uint64_t* seeds,int n_games,const int32_t* patterns,
    int radix,const double* reward,const double* win,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double model_p,double environment_p,int max_steps,
    int64_t* output,int32_t* final_boards,uint64_t* environment,uint64_t* planning,uint64_t* representation) {
    for (int game=0; game<n_games; ++game) {
        std::mt19937_64 rng(seeds[game]); int32_t board[16]={}; int position,rank;
        for (int initial=0; initial<2; ++initial) spawn_raw(board,environment_p,rng,position,rank,0,environment);
        int status=ground_status(board,radix,environment),steps=0; int64_t score=0;
        while (!status && steps<max_steps) {
            int32_t moved[64],legal[4],after[16]; int64_t scores[4],gained; double tails[4],values[4];
            const int chosen=linear_choose_v311(board,patterns,radix,reward,win,table,line_scores,cells,
                model_p,moved,scores,tails,values,legal,planning,representation);
            if (chosen<0 || !ground_swipe(board,chosen,after,gained)) return 1;
            ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
            std::copy(after,after+16,board); score+=gained;
            spawn_raw(board,environment_p,rng,position,rank,1,environment);
            ++environment[TRANSITIONS]; ++steps; status=ground_status(board,radix,environment);
        }
        if (!status) status=2;
        output[3*game]=score; output[3*game+1]=steps; output[3*game+2]=status;
        std::copy(board,board+16,final_boards+16*game);
    }
    return 0;
}
