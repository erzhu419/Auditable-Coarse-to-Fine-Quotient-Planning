# V319：固定 FIRST 教师下的规划查询状态监督

冻结日期：2026-10-06。V318 未建立目标冻结或支持外回退的修复收益。
本轮只干预监督根状态的位置，不把低精确 FIT 命中率认定为失败根因。
复用 V317 全部 16 个生命周期、四个 SOURCE、实际 FIRST A/B 独立库及不可变规划信念。
仅单次过滤读取四份 tape 的 A/B 两轮事实；无新首次适配或来源训练，不构成独立训练确认。

## 根状态与真实观察

每阶段从原完整游戏 FIT 前缀取非 WIN afterstate 的位置 i，排除每个游戏首动作。
其实际决策 preboard 为 postspawn[i−1]，自然根为 afterstate[i]。
按位置等距取 32,768 个锚点，使用冻结 FIRST 实际 H2 选择，并核对选中 afterstate 等于自然根。
在同一次 H2 计算中保留所有实际调用双头预测器的非 WIN 第二层 afterstate，保留重复次数和遍历顺序。
每锚点消耗一次独立 selector uniform（空池也消耗），按 floor(u×pool_size) 选一个查询根，不依预测值筛选。
从非空池锚点中等距取 16,384 组，两臂共享位置及顺序；不足则整队列停止，不替换种子或补根。
记录选中调用序号、池大小及路径 outer_action/spawn_cell/spawn_rank/inner_action。

FACTUAL_LOCAL 监督自然根；QUERY_LOCAL 监督实际 H2 查询根。
两臂都拥有任意 afterstate reset 的生成式访问，并各采四次新的真实 ground spawn；旧观测不进入目标。
每臂每任务每轮恰为 16,384 根组、65,536 个新训练 raw；A_R1、B_R1、A_R2、B_R2。
两臂使用同一 paired physical RNG 流：每 member 的 cell/rank 各一次 uniform，selector RNG 独立。
共 8,388,608 个新训练 raw，根组数及原生当前预测/更新规则匹配；参数地址不同，实际写入量可不同。
共同锚点选择/查询工作物理执行一次，经济上计入两臂；模型分支查询及实际采样分别计数。

## 同一冻结教师与组更新

FIRST v0 在采样、选分支及两轮目标中始终不变。对每次实际 post-spawn 棋盘，
按 score/2048+FIRST 联合奖励/WIN 尾值选择同一个 DIRECT 分支，动作顺序和平局规则沿用 V317。
非 WIN 分支目标 R=next_score/2048+FIRST_R(after)，W=FIRST_P(after)；
分支立即 WIN 则 R=next_score/2048、W=1；post-spawn LOST 则 R=W=0。
不加入产生根的动作奖励，不分别最大化 R/W，不读取正在更新的学习头。
四样本均值估计的是该根上的冻结一步教师算子，含其 bootstrap 偏差，不是整局终局真值或精确 H2 最优算子。

两臂私有复制同一个 FIRST；alpha=.0025。每个 sampling group 读一次当前双头预测，
用四个 R/W 目标均值计算残差，按该根的 32 个 tuple occurrence 归一化并提交一次双头更新。
等价于每个 distinct 地址加 alpha×组均值残差；组间当前预测随各学习头独立变化。
这些是 sampling groups，不写成完整自然游戏，不使用 suffix 或伪 terminal label。
保存根、四个真实 cell/rank、四个目标/选中动作及种类、实际组均值；记录重复间 R/W 方差及实际计算/写入量。

## 评估与唯一主终点

SOURCE/FIRST 初始化，两臂每轮后，A/B 各 32 个新配对自然 H2 游戏，最多 8192 步，共 6,144 局。
唯一主终点：最终 QUERY_LOCAL−自身 FIRST_LOCAL，A/B 等权，95% CI 下界 >0。
保留增长还要求 A、B 各自最终−FIRST 的 95% CI 下界 ≥0。
QUERY−FACTUAL 监督位置干预、净 SOURCE、FACTUAL 自身收益、FIRST−SOURCE 分别报告，不替代主终点。
20,000 次四父组内配对生命周期 bootstrap，seed31900001；保留全部生命周期与负结果。
任何自然评估 CUTOFF 则科学结论 HOLD，不删除或替换；不调整种子、表示、步长、组数、重复数或区间。

selector seed=319100000000+life×10000000+task_index×1000000+round×100000；
ground seed=319500000000+同上增量，两个臂相同；
eval seed=319900000000+life×1000000+B×100000+episode。
配置写入后才开始新采样。所有文件位于 reports/query_supervision_v319。

## 核验、成本与范围

独立核验新根的原 FIT 归属/锚点、查询路径、全部新 ground RNG/目标/均值、实际头版本与预定动作探针、配对判定和成本。
不重跑旧完整审计、全部模型拟合、评估或 bootstrap；来源与 V317 审计读取复用。
计入旧事实重建、池选择、两个臂的真实采样、teacher 查询、组更新、复制/保存、评估、编译与协调 CPU；核验另列。
引用成功 SOURCE/V317 经济成本一次；历史动力学及 V317 失败尝试 CPU 未知，不宣称历史总成本闭合。
结果条件于固定 FIRST 覆盖、16 个既有目标生命周期、四个来源及生成式访问；
不能建立普通在线采样效率、结构学习、完整独立确认或一般战略优势。U005 FAIL 保留，U006 不运行。
