// V301 full natural-game factual targets, selected nonwinning fit samples.
#include "native_split_risk_v301.cpp"

extern "C" void fit_masked_split_v307(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,const int32_t* selected,int n_fit_games,
    const int32_t* patterns,int radix,double* reward_weights,double* risk_weights,
    int kind,double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,uint64_t* selection,int64_t* examples,double* values) {
    int64_t start=0;
    std::vector<double> suffixes,reward_errors,risk_errors,global_features,
        reward_gradients,risk_gradients,global_denominators;
    std::vector<int64_t> steps,features,sorted,unique,denominators;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game]; const double label=terminal_codes[game]==1 ? 1. : 0.;
        ++targets[GAME_LABELS]; suffixes.resize(end-start); double suffix=0.;
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix; suffix+=rewards[step];
            ++targets[REWARD_SUFFIX_ASSIGNMENTS]; ++targets[REWARD_SUFFIX_ADDITIONS];
        }
        ++normalization[FIT_GAMES]; steps.clear(); features.clear(); global_features.clear();
        for (int64_t step=start; step<end; ++step) {
            ++targets[SPLIT_GOAL_CHECKS]; ++selection[0];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[WINNING_SKIPS]; ++selection[1]; continue;
            }
            ++selection[2];
            if (!selected[step]) { ++selection[3]; continue; }
            ++selection[4];
            steps.push_back(step); features.resize(features.size()+32);
            split_addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
            ++normalization[ADDRESS_EXTRACTIONS]; normalization[ADDRESS_OCCURRENCES]+=32;
            normalization[ADDRESS_DIGIT_READS]+=192; normalization[ADDRESS_MULTIPLY_ADDS]+=192;
            if (kind) {
                global_features.resize(global_features.size()+20);
                split_global_features(afterstates+16*step,radix,global_features.data()+global_features.size()-20,representation);
            }
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
        reward_errors.resize(steps.size()); risk_errors.resize(steps.size());
        reward_gradients.assign(unique.size(),0.); risk_gradients.assign(kind ? 20 : unique.size(),0.);
        global_denominators.assign(20,0.);
        // Both predictions are read from the same game-start heads before any write.
        for (size_t sample=0; sample<steps.size(); ++sample) {
            const int64_t step=steps[sample]; const int64_t* row=features.data()+32*sample;
            const double reward=split_ntuple(row,reward_weights);
            const double logit=split_logit(row,kind ? global_features.data()+20*sample : nullptr,
                kind,risk_weights,representation);
            const double probability=split_sigmoid(logit,representation);
            const double combined=split_combine(reward,probability,representation);
            reward_errors[sample]=suffixes[step-start]-reward; risk_errors[sample]=label-probability;
            if (!learning[SAMPLES]) {
                examples[0]=game; examples[1]=step;
                const double v[]={suffixes[step-start],label,reward,probability,combined,reward_errors[sample],risk_errors[sample]};
                std::copy(v,v+7,values);
            }
            examples[2]=game; examples[3]=step;
            const double v[]={suffixes[step-start],label,reward,probability,combined,reward_errors[sample],risk_errors[sample]};
            std::copy(v,v+7,values+7);
            ++learning[SAMPLES]; ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS];
            ++learning[RISK_PREDICTIONS]; learning[REWARD_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32;
            learning[REWARD_OCCURRENCES]+=32; ++targets[LABEL_ASSIGNMENTS];
            if (!kind) { learning[RISK_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32; }
        }
        // Accumulate occurrence contributions in sample order. Repeated addresses count repeatedly.
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
                ++normalization[REWARD_GRADIENT_PRODUCTS]; ++normalization[REWARD_GRADIENT_SUMS];
                if (!kind) {
                    risk_gradients[at]+=(next-first)*risk_errors[sample];
                    ++normalization[RISK_GRADIENT_PRODUCTS]; ++normalization[RISK_GRADIENT_SUMS];
                }
                first=next;
            }
            if (kind) for (int j=0; j<20; ++j) {
                const double x=global_features[20*sample+j];
                risk_gradients[j]+=x*risk_errors[sample]; global_denominators[j]+=x;
                ++normalization[RISK_GRADIENT_PRODUCTS]; ++normalization[RISK_GRADIENT_SUMS];
                ++normalization[GLOBAL_DENOMINATOR_SUMS];
            }
        }
        if (!unique.empty()) { ++normalization[GAME_COMMITS]; ++normalization[REWARD_COMMITS]; }
        for (size_t address=0; address<unique.size(); ++address) {
            reward_weights[unique[address]]+=alpha*reward_gradients[address]/denominators[address];
            ++learning[REWARD_WRITES]; ++learning[ALL_WRITES]; ++normalization[REWARD_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        bool risk_committed=false;
        for (size_t address=0; address<risk_gradients.size(); ++address) {
            const double denominator=kind ? global_denominators[address] : denominators[address];
            if (!denominator) { ++normalization[GLOBAL_ZERO_DENOMINATORS]; continue; }
            const size_t index=kind ? address : unique[address];
            risk_weights[index]+=alpha*risk_gradients[address]/denominator;
            risk_committed=true; ++learning[RISK_WRITES]; ++learning[ALL_WRITES];
            ++normalization[RISK_PARAMETER_WRITES]; ++normalization[NORMALIZATION_DIVISIONS];
            ++normalization[UPDATE_PRODUCTS];
        }
        normalization[RISK_COMMITS]+=risk_committed;
        const uint64_t bytes=8*(suffixes.capacity()+reward_errors.capacity()+risk_errors.capacity()+global_features.capacity()+
            reward_gradients.capacity()+risk_gradients.capacity()+global_denominators.capacity()+steps.capacity()+features.capacity()+
            sorted.capacity()+unique.capacity()+denominators.capacity());
        normalization[FEATURE_BUFFER_BYTES_PEAK]=std::max(normalization[FEATURE_BUFFER_BYTES_PEAK],bytes);
        start=end;
    }
}

