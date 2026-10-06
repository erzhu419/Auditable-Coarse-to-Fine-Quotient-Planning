// V311 game-start linear residuals with selected nonwinning states and full factual targets.
#include "native_linear_win_v311.cpp"

extern "C" void fit_masked_linear_v313(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,const int32_t* selected,int n_fit_games,
    const int32_t* patterns,int radix,double* reward_weights,double* win_weights,
    double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,uint64_t* selection,int64_t* examples,double* values) {
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
            ++targets[LINEAR_GOAL_CHECKS]; ++selection[0];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[WINNING_SKIPS]; ++selection[1]; continue;
            }
            ++selection[2];
            if (!selected[step]) { ++selection[3]; continue; }
            ++selection[4];
            steps.push_back(step); features.resize(features.size()+32);
            linear_addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
            ++normalization[ADDRESS_EXTRACTIONS]; normalization[ADDRESS_OCCURRENCES]+=32;
            normalization[ADDRESS_DIGIT_READS]+=192; normalization[ADDRESS_MULTIPLY_ADDS]+=192;
        }
        selection[5]+=!steps.empty();
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

