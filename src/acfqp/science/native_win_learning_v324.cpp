// V324: the V319 grouped WIN-logit update, with no reward table input.
#include "native_split_risk_v301.cpp"

namespace {
enum WinLearning { GROUP_UPDATES, CURRENT_PREDICTIONS, TABLE_LOOKUPS, WIN_TABLE_UPDATES,
    UPDATE_OCCURRENCES, REWARD_PREDICTIONS_UNUSED, WIN_PREDICTIONS,
    REWARD_LOOKUPS_UNUSED, WIN_LOOKUPS, REWARD_WRITES_UNUSED, WIN_WRITES };
enum WinTarget { GROUP_TARGETS, REWARD_REPLICA_READS_UNUSED, WIN_REPLICA_READS,
    REWARD_MEAN_SUMS_UNUSED, WIN_MEAN_SUMS, MEAN_DIVISIONS, NOISE_RESIDUALS,
    NOISE_SQUARES, NOISE_SUMS, NOISE_DIVISIONS, NOISE_ROOTS };
enum WinNorm { ROOTGROUPS, GROUP_FEATURES, GROUP_OCCURRENCES, GROUP_DIGITS,
    GROUP_ADDRESS_PRODUCTS, GROUP_SORTS, GROUP_SORT_ITEMS, GROUP_SORT_COMPARISONS,
    GROUP_DENOMINATOR_VISITS, GROUP_UNIQUE_ADDRESSES, REWARD_GRADIENT_UNUSED,
    WIN_GRADIENT_PRODUCTS, GROUP_DIVISIONS, GROUP_UPDATE_PRODUCTS,
    GROUP_COMMITS, REWARD_COMMITS_UNUSED, WIN_COMMITS,
    REWARD_PARAMETER_WRITES_UNUSED, WIN_PARAMETER_WRITES, GROUP_WORKSPACE_BYTES };
}

extern "C" void fit_win_supervision_v324(const int32_t* roots,int n,
    const double* targetwin,int repeats,const int32_t* patterns,int radix,
    double* risk,double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,int64_t* examples,
    double* values,double* noise) {
    double win_noise=0.;
    for (int root=0; root<n; ++root) {
        ++targets[GROUP_TARGETS]; double pt=0.;
        for (int replica=0; replica<repeats; ++replica) {
            pt+=targetwin[root*repeats+replica];
            ++targets[WIN_REPLICA_READS]; ++targets[WIN_MEAN_SUMS];
        }
        pt/=repeats; ++targets[MEAN_DIVISIONS];
        for (int replica=0; replica<repeats; ++replica) {
            const double dp=targetwin[root*repeats+replica]-pt;
            win_noise+=dp*dp;
            ++targets[WIN_REPLICA_READS]; ++targets[NOISE_RESIDUALS];
            ++targets[NOISE_SQUARES]; ++targets[NOISE_SUMS];
        }
        int64_t addresses[32],sorted[32];
        split_addresses(roots+16*root,patterns,radix,addresses);
        std::copy(addresses,addresses+32,sorted); ++normalization[ROOTGROUPS];
        ++normalization[GROUP_FEATURES]; normalization[GROUP_OCCURRENCES]+=32;
        normalization[GROUP_DIGITS]+=192; normalization[GROUP_ADDRESS_PRODUCTS]+=192;
        ++normalization[GROUP_SORTS]; normalization[GROUP_SORT_ITEMS]+=32;
        std::sort(sorted,sorted+32,[normalization](int64_t a,int64_t b) {
            ++normalization[GROUP_SORT_COMPARISONS]; return a<b;
        });
        const double pp=split_sigmoid(split_logit(addresses,nullptr,0,risk,representation),representation);
        const double pe=pt-pp, sample[]={pt,pp,pe};
        if (!root) { examples[0]=root; std::copy(sample,sample+3,values); }
        examples[1]=root; std::copy(sample,sample+3,values+3);
        ++learning[GROUP_UPDATES]; ++learning[CURRENT_PREDICTIONS]; ++learning[WIN_PREDICTIONS];
        learning[TABLE_LOOKUPS]+=32; learning[WIN_LOOKUPS]+=32; learning[UPDATE_OCCURRENCES]+=32;
        for (int first=0; first<32;) {
            int next=first+1; while (next<32 && sorted[next]==sorted[first]) ++next;
            const double multiplicity=next-first;
            normalization[GROUP_DENOMINATOR_VISITS]+=next-first;
            ++normalization[GROUP_UNIQUE_ADDRESSES];
            risk[sorted[first]]+=alpha*(multiplicity*pe)/multiplicity;
            ++normalization[WIN_GRADIENT_PRODUCTS]; ++normalization[GROUP_DIVISIONS];
            ++normalization[GROUP_UPDATE_PRODUCTS]; ++normalization[WIN_PARAMETER_WRITES];
            ++learning[WIN_WRITES]; ++learning[WIN_TABLE_UPDATES];
            first=next;
        }
        ++normalization[GROUP_COMMITS]; ++normalization[WIN_COMMITS];
        normalization[GROUP_WORKSPACE_BYTES]=sizeof(addresses)+sizeof(sorted);
    }
    *noise=n ? std::sqrt(win_noise/(n*repeats)) : 0.;
    if (n) { ++targets[NOISE_DIVISIONS]; ++targets[NOISE_ROOTS]; }
}
