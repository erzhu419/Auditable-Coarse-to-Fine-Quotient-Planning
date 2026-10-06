# V194：条件化的非负动作对后果迁移

V193把主要优先级指向后果迁移条件与组合。保持SOURCE143/36、完整精确R/F/S和H3固定；新学习器直接迁移同一SOURCE root的动作差。PAIR98沿旧98输入，CONDITIONAL用goal-relative rank分层关系，二者同一局部算法，保留V192全局核及强对照。不是修改U005 Gate。

## Representation and prototype model

ACTIONS DOWN/LEFT/RIGHT/UP，EPS1e-12，query risk1，native_teacher_query goal_1_risk_1，goal_rank11，horizon3。PAIR98只读relation_features；CONDITIONAL从已有layout_features记录用V190静态contract恢复节点/等rank pair/packing/once masks，不执行swipe/spawn/merge世界演化。5个rank bins顺序：positive<=7、8、9、10、>=11；零格不作节点。保留原aggregate6；各bin依次node9 moment和equal_pair33 moment分别无rank权重求和，再/4、/sqrt120；末尾vacancy8，总224维。每SOURCE/TARGET合法动作只新投影一次，root['conditional_features']缓存。不是完整关系对象图或无损表示。

接口：`cache_roots(roots)->counts`；`fit_model(examples, mode, life=0)->{model,selection,costs}`；`choose_action(model, root, counts=None)->decision`。仅选同life；原QUERY/ACTIONS及first reward/映射不变。决策只读observables/caches，不读query标签。

每training design按root_id排序、ACTIONS列中心，各合法动作一个中心；所有同root有序不同action生成prototype，保存center_indices、root/source/actions、完整tail difference=(R-first_reward,F,S)差、root_mass=1/该root有序pair数。forced根保留中心/来源组，不制造prototype。中心按Python sum各维平方差计算所有严格正的两中心距离，用排序median（偶数中间两值均值）作M。每design自己的训练信息和M，无目标数据或标准化。

固定k=(1,8,32)，temperature=(.01,.1,1)，k优先再temperature顺序9候选。query每unordered合法pair(a,b)只算一次：先缓存所有query action到训练中心D；每prototype(i,j)的归一化距离 d=(D(a,i)+D(b,j))/(2M)，按(d,prototype_index)排序。取min(k,nprototypes)项，raw_weight=exp(-(d-d_min)/temperature)*root_mass，按prototype排序后的top-k顺序sum后归一化。向量delta_ab各分量按top-k顺序Python sum(weight*prototype_tail_difference)。所有权重非负、和1；保留neighbors prototype_index/distance/raw_weight/weight，delta_ba由负号获得，不再另选近邻。

直接pair估计可能有环。统一无额外求解的complete-graph投影：n合法动作，theta_a=sum_b(delta_ab)/n，unordered pair按combinations(ACTIONS合法顺序)逐项theta_first+=delta/n、theta_second-=delta/n。相对预测vector_a=[first_reward_a+theta_a[R],theta_a[F],theta_a[S]]，按R-F+S和ACTIONS/EPS选。保存estimated_tail_delta、projected_tail_delta=theta_a-theta_b和三分量projection residual。非负凸组合性质只针对原pair估计；投影后不声称概率校准或保持逐pair凸包。单合法动作theta0，直接选择；fallback=False。所有model结构/prototypes含支持观测，可跨canonical action复用，不新增支持门槛。

## SOURCE-only selection and new target

36来源组排序奇偶两fold各18。每mode2fold library+selected full library共3design，共6（两mode）。每fold query几何距离和prototype排序一次cache，所有9candidate复用；18fold候选预测器+1selected full=19/mode、38合计，属prototype配置实例，零参数线性/特征求解。SOURCE留出按完整实际R/F/S等来源组均值效用选，EPS平局取先k再temperature。selection保留每fold design（中心/prototypes/M/成本）一次；candidate fold_records仅choice action、实际vector/utility与每组统计/成本，不复制训练库或大量neighbor数组。候选choice不看query标签，标签仅事后实际评分。fullSOURCE actual诊断两mode另计成本，不把自近邻拟合当迁移证据。

SOURCE actual诊断为控体积只移除每pair neighbors字段，完整predvec、estimated/projected tail与residual/actual RFS/成本保留；TARGETchoices保留top-k neighbors。两mode SOURCE/TARGET投影摘要统一roots/pairs、max_abs_components3、mean_abs_components3（所有pair残差绝对值均值）、utility_sign_flips（raw与projected tailutility均abs>EPS且异号）。该摘要不作新Gate。

所有新/旧model冻结后才生成4×24 TARGET，seed=1940200+24*replica+index，name=v194_target_r{replica:02d}_{index:02d}。沿V69固定16次randint1..10，24边先水平后垂直，index边两端rank1+index%10，其他格sample(index%3)置零。V184 observable cohort=FRESH；V185 geometry、V190 relation、V194 conditional缓存各一次。arms CONDITIONAL/PAIR98/NONLINEAR/RELATION/LINEAR/INTERACT/RIDGE/LAYOUT/SHARED/OLD_SHARED/ONE/FALLBACK全部选择保存后，才开新labels；ORACLE只labels后。

精确labels沿V184 V69 FULL、goal1risk1教师，96 board各cap200000，compact policy+native/canonical fractions及全成本，无大kernel。主比较CONDITIONAL−PAIR98/LINEAR/NONLINEAR/OLD_SHARED，其他7control差、4replica、RFS、regret、errors增减、gain concentration、原pair projection residual均保留。不新科学Gate，不按TARGET调k/T/bin/投影。

## Inputs, accounting, verification

九输入协议冻结后原字节按序：V193 runtime stage_checks.json→v193_stage_checks.json；V193 run.json→v193_run.json；V193 inputs/inherited/roots.json→v193_roots.json（SOURCE才训练）；V192 model.json→nonlinear_model.json；V192 inputs/inherited/relation_model/expanded_models/baseline_models/learned_rule/dense_models.json（各同名）。输入均phase protocol_frozen。新root文件只保SOURCE及本轮TARGET。

phase protocol_frozen(0reads)→source_selection(9)→models_frozen→target_roots→target_choices_frozen→target_labels→complete（均9reads）。model/selection/source_diagnostics/roots/target_cases/choices/labels/native_labels/label_costs/summary/run/input_manifest/source_manifest留存，teacher_policy小文件；新models/selection/source_diagnostics可按mode字典。记录SOURCE条件投影、6design、38配置实例、centre distances/median、prototype distance/sorting、所有weights/vector/projection、实际validation/source/target成本、原成本链，零新SOURCEgames/environment samples/native updates。失败保留attempt及已付成本，不重新来一遍。

源码/协议/tests/runtime wrappers实际读前冻结。独立auditor从V190已独立验证的静态contract构建其独立分层投影；不调用V194 main feature/fit/choose/summary。独立重建6design/9candidate×2mode的SOURCE选择、full模型及SOURCE actual、FRESH observations/caches/所有新旧choices、exact native/canonical policy成本绑定/summary，零新world积分、旧model fit、linear/eigen/SVD solve。固定比较容差1e-8*(1+abs expected)，行动/weights符号/roster/phase精确，source字节stage一次、九输入audit一次；main/audit各一次，无hash。测试仅合成，覆盖rank bins非混合、label-free heldout决策、同root完整pair标签、root_mass/权重非负归一化/首reward一次、完整graph投影和环残差、forced/EPS、SOURCE-only实际utility选择、冻结/付费失败以及audit对改动weight/action的拒绝。

中途仅reports/v194_runtime_tmp，结果仅reports/controlled_predictive_conditional_pairs_v194。限制集中在结果报告：有限H3/固定教师、矩摘要非无损、prototype插值/投影不是概率校准；一般战略学习仍未解决。H2保持，U005 FAIL，U006未启动。
