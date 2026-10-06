// Batch-start sampled SARSA targets; unchanged LOCAL current-game residual commits.
#include "native_split_risk_v301.cpp"
#include <chrono>
#include <ctime>

namespace {
enum LocalTarget { TD_GAME_LABELS, TD_GOAL_CHECKS, TD_WINNING_SKIPS,
    NEXT_REWARD_READS, REWARD_TARGET_ASSIGNMENTS, WIN_TARGET_ASSIGNMENTS,
    BOOTSTRAP_TARGETS, ANALYTIC_NEXT_WIN_TARGETS, LAST_LOST_TARGETS,
    NEXT_GOAL_CHECKS, TARGET_KIND_READS };
enum BootstrapWork { BOOTSTRAP_PREDICTIONS, BOOTSTRAP_REWARD_READS,
    BOOTSTRAP_RISK_READS, BOOTSTRAP_FEATURES, BOOTSTRAP_OCCURRENCES,
    BOOTSTRAP_DIGIT_READS, BOOTSTRAP_ADDRESS_PRODUCTS };
}

extern "C" void fit_local_targets_v314(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,int n_fit_games,
    const int32_t* patterns,int radix,double* reward_weights,double* risk_weights,
    const double* bootstrap_reward,const double* bootstrap_risk,double alpha,
    double* targetreward,double* targetwin,int32_t* targetkind,uint64_t* learning,
    uint64_t* targets,uint64_t* normalization,uint64_t* representation,
    uint64_t* bootstrap,uint64_t* bootstrap_representation,int64_t* examples,
    double* values,double* timings) {
    const auto target_wall=std::chrono::steady_clock::now();
    const std::clock_t target_cpu=std::clock();
    int64_t start=0;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game]; const bool lost=terminal_codes[game]==-1;
        ++targets[TD_GAME_LABELS];
        for (int64_t step=start; step<end; ++step) {
            targetreward[step]=targetwin[step]=0.; targetkind[step]=0;
            ++targets[TD_GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[TD_WINNING_SKIPS]; continue;
            }
            ++targets[REWARD_TARGET_ASSIGNMENTS]; ++targets[WIN_TARGET_ASSIGNMENTS];
            if (step+1==end && lost) {
                // A nonwinning final factual afterstate ends in LOST.
                targetkind[step]=3; ++targets[LAST_LOST_TARGETS];
                continue;
            }
            const int32_t* next=afterstates+16*(step+1);
            targetreward[step]=rewards[step+1]; ++targets[NEXT_REWARD_READS];
            ++targets[NEXT_GOAL_CHECKS];
            if (*std::max_element(next,next+16)>=radix) {
                targetwin[step]=1.; targetkind[step]=2;
                ++targets[ANALYTIC_NEXT_WIN_TARGETS];
            } else {
                int64_t addresses[32]; split_addresses(next,patterns,radix,addresses);
                targetreward[step]+=split_ntuple(addresses,bootstrap_reward);
                const double logit=split_logit(addresses,nullptr,0,bootstrap_risk,bootstrap_representation);
                targetwin[step]=split_sigmoid(logit,bootstrap_representation);
                targetkind[step]=1; ++targets[BOOTSTRAP_TARGETS];
                ++bootstrap[BOOTSTRAP_PREDICTIONS]; bootstrap[BOOTSTRAP_REWARD_READS]+=32;
                bootstrap[BOOTSTRAP_RISK_READS]+=32; ++bootstrap[BOOTSTRAP_FEATURES];
                bootstrap[BOOTSTRAP_OCCURRENCES]+=32; bootstrap[BOOTSTRAP_DIGIT_READS]+=192;
                bootstrap[BOOTSTRAP_ADDRESS_PRODUCTS]+=192;
            }
        }
        start=end;
    }
    timings[0]=double(std::clock()-target_cpu)/CLOCKS_PER_SEC;
    timings[1]=std::chrono::duration<double>(std::chrono::steady_clock::now()-target_wall).count();

    start=0;
    std::vector<double> reward_errors,risk_errors,reward_gradients,risk_gradients;
    std::vector<int64_t> steps,features,sorted,unique,denominators;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game]; ++normalization[FIT_GAMES];
        steps.clear(); features.clear();
        for (int64_t step=start; step<end; ++step) {
            ++targets[TARGET_KIND_READS];
            if (!targetkind[step]) continue;
            steps.push_back(step); features.resize(features.size()+32);
            split_addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
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
        reward_errors.resize(steps.size()); risk_errors.resize(steps.size());
        reward_gradients.assign(unique.size(),0.); risk_gradients.assign(unique.size(),0.);
        // Current predictions remain at game start; bootstrap arrays remain at batch start.
        for (size_t sample=0; sample<steps.size(); ++sample) {
            const int64_t step=steps[sample]; const int64_t* row=features.data()+32*sample;
            const double reward=split_ntuple(row,reward_weights);
            const double logit=split_logit(row,nullptr,0,risk_weights,representation);
            const double probability=split_sigmoid(logit,representation);
            const double combined=split_combine(reward,probability,representation);
            reward_errors[sample]=targetreward[step]-reward;
            risk_errors[sample]=targetwin[step]-probability;
            const double v[]={targetreward[step],targetwin[step],reward,probability,combined,
                reward_errors[sample],risk_errors[sample]};
            if (!learning[SAMPLES]) { examples[0]=game; examples[1]=step; std::copy(v,v+7,values); }
            examples[2]=game; examples[3]=step; std::copy(v,v+7,values+7);
            ++learning[SAMPLES]; ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS];
            ++learning[RISK_PREDICTIONS]; learning[REWARD_LOOKUPS]+=32;
            learning[RISK_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=64; learning[REWARD_OCCURRENCES]+=32;
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
                const auto at=std::lower_bound(unique.begin(),unique.end(),local[first],
                    [normalization](int64_t a,int64_t b) {
                        ++normalization[ADDRESS_DENOMINATOR_COMPARISONS]; return a<b;
                    })-unique.begin();
                reward_gradients[at]+=(next-first)*reward_errors[sample];
                risk_gradients[at]+=(next-first)*risk_errors[sample];
                ++normalization[REWARD_GRADIENT_PRODUCTS]; ++normalization[REWARD_GRADIENT_SUMS];
                ++normalization[RISK_GRADIENT_PRODUCTS]; ++normalization[RISK_GRADIENT_SUMS];
                first=next;
            }
        }
        if (!unique.empty()) {
            ++normalization[GAME_COMMITS]; ++normalization[REWARD_COMMITS]; ++normalization[RISK_COMMITS];
        }
        for (size_t address=0; address<unique.size(); ++address) {
            reward_weights[unique[address]]+=alpha*reward_gradients[address]/denominators[address];
            ++learning[REWARD_WRITES]; ++learning[ALL_WRITES]; ++normalization[REWARD_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        for (size_t address=0; address<unique.size(); ++address) {
            risk_weights[unique[address]]+=alpha*risk_gradients[address]/denominators[address];
            ++learning[RISK_WRITES]; ++learning[ALL_WRITES]; ++normalization[RISK_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        const uint64_t bytes=8*(reward_errors.capacity()+risk_errors.capacity()+reward_gradients.capacity()+
            risk_gradients.capacity()+steps.capacity()+features.capacity()+sorted.capacity()+unique.capacity()+denominators.capacity());
        normalization[FEATURE_BUFFER_BYTES_PEAK]=std::max(normalization[FEATURE_BUFFER_BYTES_PEAK],bytes);
        start=end;
    }
}
