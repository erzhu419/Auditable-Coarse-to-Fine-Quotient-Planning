# V248冻结：新终态完整区域与R经验中心反例

V247工程执行与独立审计成功，科学条件4/5、返场仍48/72。联合预测557次全采RETRY，S/D未获取新证据；三个同起点同直方图对照证明固定凸切平面预测明显偏松，但尚未证明更好的联合动作。本阶段固定已付终态，区分真实区域阻塞与候选点被其他约束排除，不继续调单批分数。

前置为V247 run.complete=true及analysis.valid=true。从V247 ONE_WAY和JOINT_PREDICTION留存终态枚举goal所选SHORT且对DETOUR_RETRY未获证的全部端点：每臂24、每life8，共48端点，两臂life/index配对身份必须相同。在候选构造前冻结整张名单；不取未来目标、其他臂或混合最终池。读取记录、必要profiles、公共接口、共同前缀/费用及原历史付费批次；不读results、laws、真概率、最优策略，不调用world。

每端点两种预声明候选，共96条状态。RETAINED精确沿用V244：原bad_null_mle或有限leaf上界最大者（精确并列首叶），用原lambda/nu系数恢复并归一化S/D，R采用原解析截断概率；只修复S一次，使goal gap=STRICT_GAP=50001/1000000。R_CENTERED使用同一个原始合法recovered_kernel的D，不使用另一个leaf；将R DELIVERY置为当前已付原生R行DELIVERY/总数，LOST补足，再按相同公式只修复S一次：s=(sc−dc+4Ddelivery+Drecovery*(4q−retry_cost)−STRICT_GAP)/4。

两个候选各自一次修复，不裁剪、不重试、不新优化。原recovery不可用时两种都unknown；原recovery合法但RETAINED修复不可行时，R_CENTERED仍执行其预声明的独立一次修复。R_CENTERED不是MLE坏核证书，须保留原恢复来源/leaf和独立候选标签，不用伪造certificate包装调用旧接口。

每合法严格坏核精确检查同一当前数据的canonical S_D_FULL_R@960、V235全部8个query family@960及原joint_constraints中全部完整分类算子行事件，逐条保留source/pool/member counts、标签和threshold（720/720/8640）。不得用边际外包区间替代完整分类区域；不相乘阈值、不另设覆盖预算。事件和模型仍是每life/arm查询.05与执行.05的完整过程无条件合并上界.10，非整个cohort的.10。

状态沿用V244：unknown（构造不可用或canonical排除）；paid_constraints_reject_candidate（canonical内、其他约束排除此固定点）；full_region_bad_witness（严格坏核位于全部8族和全部原执行区域）。候选排除不能证明整个坏零假设为空。R_CENTERED全域内反例只证明当前S/D歧义在不偏离R经验中心时仍存在，不能把经验中心当成已知真实R。

汇总按臂、候选、life给状态与排除事件，并按配对端点比较。每臂以两候选的全域坏核端点并集计数，给当前区域下获证数上限72−唯一坏核端点数，不能把两个候选重复计算，也不外推到新区域/新数据/任意统计方法。经验行及候选逐算子TV距离仅描述坏核需要改变哪些机制，不参与采样评分。

源码及本方案在分类前留存。独立审计不导入新producer/core：累加已审计历史来源增量，仅重放V245 ONE A/B原生批次，再沿V247真实目标顺序分别更新两臂原生A池；在每个目标自己的末尾冻结计数、member和9个事件。独立复算两候选、严格gap、全部投影及精确M≤T L、费用、索引和行偏移；不重审原已验证随机outcome生成、也不引入真值。来源、历史和新目标费用仍原样引用，新增环境观测/优化/旧目标评分/查询证书均0。

本诊断完成条件为48端点/96状态完整留存且independent valid=true，不要求正结果，不授予算法资格。若R中心全域坏核广泛存在，下一阶段从返场前的共享S/D机制证据获取入手，在完整固定预算与强REBUILD对照上检验跨查询摊销；若候选被排除，只将证明接口尚未利用完整信息作为待检验线索。原V247失败、原科学Gate和U006未启动状态保持不动。
