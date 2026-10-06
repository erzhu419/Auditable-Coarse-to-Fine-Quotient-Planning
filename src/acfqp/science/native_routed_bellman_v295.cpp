// V294 mathematics with observed-module routing and one GLOBAL game denominator.
#include "native_conditional_bellman_v294.cpp"

namespace {
constexpr int V294_COUNT=46;
enum RoutedCount { EXPERT_READS=V294_COUNT, ROUTED_GRADIENT_VISITS,
    EXPERT_ADDRESS_PAIRS, EXPERT_COMMITS, POINTER_VIEWS };
}

extern "C" void fit_routed_bellman_v295(const int32_t* boards, int n,
    const double* probabilities, const int32_t* expert_indices,
    const int32_t* patterns, int radix, const double* source,
    double* const* expert_residuals, int n_experts,
    const int32_t* table, const int64_t* scores, const int32_t* cells,
    double goal, double failure, double failure_shift, double success_shift,
    double alpha, uint64_t* counts, uint64_t* module_work,
    int64_t* example_indices, double* example_values,
    int64_t* module_indices, double* module_examples) {
    std::vector<int64_t> features, steps, sorted, unique, denominators;
    std::vector<double> coefficients, errors, gradients;
    std::vector<uint8_t> touched;
    counts[POINTER_VIEWS]+=n_experts;
    for (int step=0; step<n; ++step) {
        if (won(boards+16*step,radix)) { ++counts[SKIPPED_WINNING]; continue; }
        const int expert=expert_indices[step]; ++counts[EXPERT_READS];
        const auto p=parameters(patterns,radix,source,expert_residuals[expert],2,
            table,scores,cells,goal,failure,failure_shift,success_shift);
        steps.push_back(step); features.resize(features.size()+32);
        addresses(boards+16*step,p,features.data()+features.size()-32,counts);
        double b[2]; basis(probabilities[step],2,b,counts);
        coefficients.push_back(b[0]); coefficients.push_back(b[1]);
        const double before=prediction(features.data()+features.size()-32,p,b,counts);
        const double target=expected_control(boards+16*step,probabilities[step],p,b,counts);
        ++counts[CONTROL_TARGETS];
        const double error=target-before; ++counts[ERROR_SUBTRACTIONS];
        errors.push_back(error);
        example(step,target,before,error,probabilities[step],counts[UPDATES],
            example_indices,example_values);
        example(step,target,before,error,probabilities[step],module_work[3*expert],
            module_indices+2*expert,module_examples+8*expert);
        ++module_work[3*expert]; ++counts[UPDATES]; counts[UPDATE_OCCURRENCES]+=64;
    }
    // Every target reads its routed expert before any expert receives a write.
    sorted=features; counts[SORT_ITEMS]+=sorted.size();
    std::sort(sorted.begin(),sorted.end(),[counts](int64_t a,int64_t b) {
        ++counts[SORT_COMPARISONS]; return a<b;
    });
    for (int64_t a:sorted) {
        ++counts[COUNT_VISITS];
        if (unique.empty() || unique.back()!=a) {
            unique.push_back(a); denominators.push_back(1);
        } else ++denominators.back();
    }
    counts[UNIQUE_ADDRESSES]+=unique.size();
    gradients.assign(n_experts*2*unique.size(),0.);
    touched.assign(n_experts*unique.size(),0);
    for (size_t sample=0; sample<steps.size(); ++sample) {
        const int expert=expert_indices[steps[sample]];
        for (int occurrence=0; occurrence<32; ++occurrence) {
            const int64_t address=features[32*sample+occurrence];
            const auto found=std::lower_bound(unique.begin(),unique.end(),address,
                [counts](int64_t a,int64_t b) { ++counts[DENOM_COMPARISONS]; return a<b; });
            const size_t at=found-unique.begin();
            ++counts[ROUTED_GRADIENT_VISITS];
            touched[expert*unique.size()+at]=1;
            for (int bank=0; bank<2; ++bank) {
                gradients[(2*expert+bank)*unique.size()+at]+=coefficients[2*sample+bank]*errors[sample];
                ++counts[GRADIENT_ADDS];
            }
        }
    }
    int64_t parameter_count=4;
    for (int i=0; i<6; ++i) parameter_count*=radix;
    if (!unique.empty()) ++counts[GAME_COMMITS];
    for (int expert=0; expert<n_experts; ++expert) {
        bool committed=false;
        for (int bank=0; bank<2; ++bank) for (size_t at=0; at<unique.size(); ++at) {
            if (!touched[expert*unique.size()+at]) continue;
            if (bank==0) { ++counts[EXPERT_ADDRESS_PAIRS]; ++module_work[3*expert+2]; }
            expert_residuals[expert][bank*parameter_count+unique[at]]+=
                alpha*gradients[(2*expert+bank)*unique.size()+at]/denominators[at];
            ++module_work[3*expert+1]; ++counts[WRITES]; ++counts[DIVISIONS];
            ++counts[UPDATE_MULTIPLICATIONS]; committed=true;
        }
        counts[EXPERT_COMMITS]+=committed;
    }
    counts[BUFFER_BYTES_PEAK]=8*(features.capacity()+steps.capacity()+sorted.capacity()
        +unique.capacity()+denominators.capacity()+coefficients.capacity()+errors.capacity()
        +gradients.capacity())+touched.capacity();
}
