# V287：固定自然行为上的 TD / 整局回报拟合

冻结于正式拟合和新评估前。仅复用审核 PASS 的 V286 四来源、16 条 life 的
FROZEN 单 A 历史；不调用 B 后缀、V285 MC动作标签或新的训练环境。
本次检验同一行为数据上的学习目标能否改善新整局决策，不检验最佳动作标签。

## 数据与拟合

重构所有 FROZEN/A 实际 swipe、score 与 raw spawn，核对 chunk 开始/结束棋盘
及完整游戏终态。A 内终局游戏按实际时间排序；前 floor(.8*N) 个用于拟合，
后缀用于固定参数预测检验。跨 A/B 的末尾未完局从两种拟合和预测检验中共同
排除，其已获取/处理成本仍计入。分割不参考奖励、预测或新评估。

三臂 FROZEN、SHADOW_TD、EPISODIC_MC 都从同一原 V120 risk_goal@4096 来源
初始化。两新表 alpha=.0025、一次按时间顺序拟合，每个 nonwinning afterstate
恰一次更新；winning afterstate 为解析 +4，不更新。不搜索 alpha、预算或阈值。

SHADOW_TD：当前 afterstate 的目标为下一实际动作的 score/2048 加更新前
shadow 叶的下一 afterstate 值。下一动作照抄留存行为，不重新选择、不使用
H2 expected value；下一动作 winning 时尾值 +4；LOST 最后 afterstate 目标 -4。
EPISODIC_MC：目标为当前动作之后的实际 score suffix/2048 加最终 ±4，不含
当前 action 的分数。完整游戏结束后构建标签，随后按同样时间顺序更新。
QueryTD 的 offset 在预测加一次、raw target 减一次；保留重复特征的更新重数。

## 分离预测与控制端点

后20%的完整留存游戏用于三张静态表的 bias/MSE/MAE，与事实 after-current-action
回报比较。只统计训练同样的 nonwinning afterstates，先游戏内平均，再游戏
等权→life等权；长游戏不增加 life 权重。heldout 不更新权重/记忆、不用于选择。

每条 life 的三张最终表共用拟合前缀结束时的 LIBRARY 记忆与预测 p，只使用
该前缀及共同 warmup 的 raw ranks（含初始 tile）。各臂固定参数与记忆，在
A(.1) 上执行相同16个新种子、H2、查询(1,4,4)、上限8192的完整游戏。
评估不消费保留训练随机流、不更新权重/记忆；控制器不接真 p。
种子=287500000000+life*1000000+episode，独立于 V286 所有流。

主端点 EPISODIC_MC−FROZEN 的独立整局 utility；次端点 SHADOW_TD−FROZEN、
EPISODIC_MC−SHADOW_TD 及各 heldout 预测误差。utility=score/2048+4WON−4LOST。
16新游戏均重→16life均重；四个固定来源内整条life bootstrap 20000次，
seed28700001。全部负例与cutoff留存；CI仅条件于四个旧来源。

## 成本、解释与留存

经济获取预算每臂相同：原来源价值训练、动力学、共同暖启动，加 V286 FROZEN
的全部 A 观察（包括holdout及被排除尾局）；共享物理成本只计一次。
新训练环境观察为零。另列重构/标签处理、更新/预测/规划、权重复制与驻留、
新评估环境观察、worker/编译/协调CPU和墙钟。不把留存数据视为免费来源。
输出在 `reports/retained_critic_v287/`，仅compact游戏/更新例/统计与账本，不保存
大棋盘CSV或新checkpoint。

固定数据切断 critic→行为→新数据反馈；与 V286 的数据和预算不同，不能直接
将两轮差异归因于行为反馈。MC学习的是留存控制器的后续回报，不是最优Q；
新H2用新表重规划后改变行为，因此更低MSE不保证更高utility。若预测改善未
兑现为收益，不宣称战略学习修复；原U005 Gate仍FAIL，U006不运行。
