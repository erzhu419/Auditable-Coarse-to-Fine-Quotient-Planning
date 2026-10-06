// V120 addresses/value summation; whole-game occurrence-normalized MC updates.
#include <algorithm>
#include <cstdint>
#include <vector>

namespace {
enum Learning { UPDATES, PREDICTIONS, LOOKUPS, UNIQUE_WRITES, OCCURRENCES };
enum Target { GOAL_CHECKS, ANALYTIC_TAILS, TERMINAL_TARGETS, NEXT_REWARDS,
    SUFFIX_GAMES, SUFFIX_ASSIGNMENTS, SUFFIX_ADDITIONS, TARGET_SUBTRACTIONS,
    PREDICTION_SHIFTS, SKIPPED_WINNING, BUFFER_DOUBLES_PEAK };
enum Consolidation { GAMES, EXTRACTIONS, FEATURE_OCCURRENCES, DIGIT_READS,
    ADDRESS_MULTIPLY_ADDS, GAME_SORT_CALLS, GAME_SORT_ITEMS, GAME_SORT_COMPARISONS,
    COUNT_VISITS, COUNT_COMPARISONS, SAMPLE_SORT_CALLS, SAMPLE_SORT_ITEMS,
    SAMPLE_SORT_COMPARISONS, DENOM_SEARCHES, DENOM_SEARCH_COMPARISONS,
    SAMPLE_UNIQUE_ADDRESSES, GAME_UNIQUE_ADDRESSES, WEIGHTED_MULTIPLICATIONS,
    WEIGHTED_ACCUMULATIONS, UPDATE_MULTIPLICATIONS, NORMALIZATION_DIVISIONS,
    GAME_COMMITS, SAMPLE_COMMITS, PARAMETER_WRITES, FEATURES_PEAK, SORTED_PEAK,
    STEPS_PEAK, ADDRESSES_PEAK, DENOMINATORS_PEAK, SAMPLE_ADDRESSES_PEAK,
    MULTIPLICITIES_PEAK, SAMPLE_ENDS_PEAK, ERRORS_PEAK, PREDICTIONS_PEAK,
    GRADIENTS_PEAK, BUFFER_BYTES_PEAK };

void addresses(const int32_t* board, const int32_t* patterns, int radix, int64_t* output) {
    int64_t stride=1;
    for (int i=0; i<6; ++i) stride*=radix;
    for (int tuple=0; tuple<32; ++tuple) {
        int64_t address=0;
        for (int cell=0; cell<6; ++cell)
            address=address*radix+board[patterns[tuple*6+cell]];
        output[tuple]=(tuple/8)*stride+address;
    }
}

double prediction(const int64_t* features, const double* weights) {
    double value=0.;
    for (int occurrence=0; occurrence<32; ++occurrence) value+=weights[features[occurrence]];
    return value;
}

void example(int game, int64_t step, double target, double raw_target,
    double error, double value, uint64_t updates, int64_t* indices, double* values) {
    if (!updates) {
        indices[0]=game; indices[1]=step;
        values[0]=target; values[1]=raw_target; values[2]=error; values[3]=value;
    }
    indices[2]=game; indices[3]=step;
    values[4]=target; values[5]=raw_target; values[6]=error; values[7]=value;
}
}

extern "C" void fit_consolidated_v290(const int32_t* afterstates, const double* rewards,
    const int64_t* ends, const int32_t* terminal_codes, int n_fit_games,
    const int32_t* patterns, int radix, double* weights, double goal, double failure,
    double failure_shift, double success_shift, double alpha, int mean_method,
    uint64_t* learning, uint64_t* targets, uint64_t* work,
    int64_t* example_indices, double* example_values) {
    std::vector<double> suffixes, errors, predictions, gradients;
    std::vector<int64_t> steps, features, sorted, unique_addresses, denominators;
    std::vector<int64_t> sample_addresses, multiplicities, sample_ends;
    int64_t start=0;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game];
        suffixes.resize(end-start);
        targets[BUFFER_DOUBLES_PEAK]=std::max(targets[BUFFER_DOUBLES_PEAK],
            static_cast<uint64_t>(suffixes.capacity()));
        double suffix=terminal_codes[game]==1 ? goal : -failure;
        ++targets[SUFFIX_GAMES];
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix;
            suffix+=rewards[step];
            ++targets[SUFFIX_ASSIGNMENTS]; ++targets[SUFFIX_ADDITIONS];
        }
        ++work[GAMES];
        steps.clear(); features.clear();
        for (int64_t step=start; step<end; ++step) {
            ++targets[GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[SKIPPED_WINNING]; continue;
            }
            steps.push_back(step);
            features.resize(features.size()+32);
            addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
            ++work[EXTRACTIONS]; work[FEATURE_OCCURRENCES]+=32;
            work[DIGIT_READS]+=192; work[ADDRESS_MULTIPLY_ADDS]+=192;
        }
        sorted=features;
        ++work[GAME_SORT_CALLS]; work[GAME_SORT_ITEMS]+=sorted.size();
        std::sort(sorted.begin(),sorted.end(),[work](int64_t a,int64_t b) {
            ++work[GAME_SORT_COMPARISONS]; return a<b;
        });
        unique_addresses.clear(); denominators.clear();
        for (size_t index=0; index<sorted.size(); ++index) {
            ++work[COUNT_VISITS];
            if (index) ++work[COUNT_COMPARISONS];
            if (!index || sorted[index]!=sorted[index-1]) {
                unique_addresses.push_back(sorted[index]); denominators.push_back(1);
            } else ++denominators.back();
        }
        work[GAME_UNIQUE_ADDRESSES]+=unique_addresses.size();
        sample_addresses.clear(); multiplicities.clear(); sample_ends.clear();
        for (size_t sample=0; sample<steps.size(); ++sample) {
            int64_t local[32];
            std::copy(features.data()+32*sample,features.data()+32*sample+32,local);
            ++work[SAMPLE_SORT_CALLS]; work[SAMPLE_SORT_ITEMS]+=32;
            std::sort(local,local+32,[work](int64_t a,int64_t b) {
                ++work[SAMPLE_SORT_COMPARISONS]; return a<b;
            });
            for (int first=0; first<32;) {
                int next=first+1;
                while (next<32 && local[next]==local[first]) ++next;
                ++work[DENOM_SEARCHES];
                auto found=std::lower_bound(unique_addresses.begin(),unique_addresses.end(),
                    local[first],[work](int64_t a,int64_t b) {
                        ++work[DENOM_SEARCH_COMPARISONS]; return a<b;
                    });
                sample_addresses.push_back(found-unique_addresses.begin());
                multiplicities.push_back(next-first);
                ++work[SAMPLE_UNIQUE_ADDRESSES]; first=next;
            }
            sample_ends.push_back(sample_addresses.size());
        }
        if (mean_method) {
            errors.resize(steps.size()); predictions.resize(steps.size());
            gradients.assign(unique_addresses.size(),0.);
            // No parameter write occurs until every game-start residual is read.
            for (size_t sample=0; sample<steps.size(); ++sample) {
                const int64_t step=steps[sample];
                const double value=prediction(features.data()+32*sample,weights);
                const double target=suffixes[step-start];
                const double raw_target=target-(failure_shift+success_shift);
                const double error=raw_target-value;
                predictions[sample]=value; errors[sample]=error;
                example(game,step,target,raw_target,error,value,learning[UPDATES],
                    example_indices,example_values);
                ++learning[UPDATES]; ++learning[PREDICTIONS]; learning[LOOKUPS]+=32;
                learning[OCCURRENCES]+=32; ++targets[TARGET_SUBTRACTIONS];
            }
            int64_t begin=0;
            for (size_t sample=0; sample<steps.size(); ++sample) {
                for (int64_t at=begin; at<sample_ends[sample]; ++at) {
                    gradients[sample_addresses[at]]+=multiplicities[at]*errors[sample];
                    ++work[WEIGHTED_MULTIPLICATIONS]; ++work[WEIGHTED_ACCUMULATIONS];
                }
                begin=sample_ends[sample];
            }
            if (!unique_addresses.empty()) ++work[GAME_COMMITS];
            for (size_t address=0; address<unique_addresses.size(); ++address) {
                weights[unique_addresses[address]]+=alpha*gradients[address]/denominators[address];
                ++learning[UNIQUE_WRITES]; ++work[PARAMETER_WRITES];
                ++work[UPDATE_MULTIPLICATIONS]; ++work[NORMALIZATION_DIVISIONS];
            }
        } else {
            int64_t begin=0;
            for (size_t sample=0; sample<steps.size(); ++sample) {
                const int64_t step=steps[sample];
                const double value=prediction(features.data()+32*sample,weights);
                const double target=suffixes[step-start];
                const double raw_target=target-(failure_shift+success_shift);
                const double error=raw_target-value;
                example(game,step,target,raw_target,error,value,learning[UPDATES],
                    example_indices,example_values);
                ++learning[UPDATES]; ++learning[PREDICTIONS]; learning[LOOKUPS]+=32;
                learning[OCCURRENCES]+=32; ++targets[TARGET_SUBTRACTIONS];
                ++work[SAMPLE_COMMITS];
                for (int64_t at=begin; at<sample_ends[sample]; ++at) {
                    const int64_t address=sample_addresses[at];
                    weights[unique_addresses[address]]+=
                        alpha*multiplicities[at]*error/denominators[address];
                    ++learning[UNIQUE_WRITES]; ++work[PARAMETER_WRITES];
                    work[UPDATE_MULTIPLICATIONS]+=2; ++work[NORMALIZATION_DIVISIONS];
                }
                begin=sample_ends[sample];
            }
        }
        const uint64_t capacities[]={features.capacity(),sorted.capacity(),steps.capacity(),
            unique_addresses.capacity(),denominators.capacity(),sample_addresses.capacity(),
            multiplicities.capacity(),sample_ends.capacity(),errors.capacity(),
            predictions.capacity(),gradients.capacity()};
        uint64_t buffer_items=suffixes.capacity();
        for (int index=0; index<11; ++index) {
            work[FEATURES_PEAK+index]=std::max(work[FEATURES_PEAK+index],capacities[index]);
            buffer_items+=capacities[index];
        }
        work[BUFFER_BYTES_PEAK]=std::max(work[BUFFER_BYTES_PEAK],8*buffer_items);
        start=end;
    }
}
