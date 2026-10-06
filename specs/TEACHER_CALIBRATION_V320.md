# V320：固定根与首动作的教师终局校准

冻结日期：2026-10-06。V319 查询状态监督有效退化，本轮检验其冻结一步教师标签与真实后续回报的差距。没有新拟合、表示修改或学习效果试验；U005 FAIL 保留，U006 不运行。

复用独立核验 PASS 的 V319 全部 16 个 FIRST 生命周期、四个 SOURCE、A/B 独立实际 FIRST v0 和不可变规划信念。读原 group NPZ，不重构旧 tapes、重复旧审计或再采首次 spawn。

## 固定位置与策略

每个任务/轮次从原 16,384 个组取 `np.linspace(0,16383,64,dtype=int64)`，两臂共用相同 64 个位置及其全部四个成员。共 32,768 条续跑。此前 V319 结果文件提出的共同前缀在采样前改为等间距位置；前缀没有运行或择优比较。位置不依目标、终局、预测值或续跑长度挑选。

从保存的 root 恢复其实际 V319 spawn_cell/rank，不消耗新随机数或新 raw。若此棋盘 LOST，则 R=W=0；否则先按记录的 DIRECT 动作实际 swipe，并保留这次即时奖励。禁止让 H2 在此重新选动作。

随后每次真实 swipe 都产生新的 ground spawn，包含产生 WIN 的动作之后的 spawn，与既有整局执行约定一致。FIRST 双头始终只读。后续动作使用相同 FIRST H2 与实际库信念，true p_four 为 A=.1、B=.5；每条最多 8192 个动作，包含规定的首次 DIRECT。

终局实际 R 为此次 DIRECT 及全部后续动作 score 总和/2048，不含产生 root 的进入动作奖励；W 为实际终局 WIN 0/1。单步目标保持原 V319 保存的 R/W，不重新选择分支或改标签。比较对象是规定首次动作后由 FIRST H2 执行的实际回报，不是最优策略真值。

每条独立 mt19937_64 seed 为 `320500000000+life*10000000+task_index*1000000+round*100000+original_group_index*4+member`，两臂相同。流从首次 DIRECT 后的新 spawn 开始；旧首次 spawn 是留存观察，不收费为新采样。新采样数随真实终局变化，完整计数，不宣称两臂 raw/CPU 相同。

## 终点

唯一主终点为 QUERY−FACTUAL 的 signed combined teacher error：`teacher_R+8*teacher_W-(actual_R+8*actual_W)`，常数 −4 相消。下界 >0 为 SUPPORTED_MORE_OPTIMISTIC，上界 <0 为 SUPPORTED_MORE_PESSIMISTIC，其余 UNRESOLVED；均不表示学习改善或因果解释。

先在成员、组、两轮、两任务内等权求生命周期均值，再在四个固定父组内配对重采样生命周期，20,000 次，seed32000001。统计单位为 16 个生命周期，不把 32,768 条续跑当独立生命周期。

R/W 分量、各臂偏差、每任务轮次、平方误差及四成员中心化离散程度为描述性/nominal secondary。任何 CUTOFF 保留全样本并使整个校准结论 HOLD，不替换位置、种子或策略，不将未结束的 WIN 记为真实负例。位置、步数、策略、主终点和区间不据结果调整。

## 留存、核验与成本

所有输出位于 `reports/teacher_calibration_v320`。每条新动作存 action、score、spawn cell/rank 和状态，棋盘由原 root 与首 spawn 重建；不逐步重复保存棋盘。保存每条最终棋盘、score、动作/raw 数、终局、seed、组位置，以及 FIRST 参数版本和原 group 文件引用。

采集在真实 H2 调用中保存每批 first8/last8 条续跑的首/末 H2 决策探针，无额外重查；即刻终局的 FIRST DIRECT 没有 H2 探针。

独立核验全部新 physics/RNG/回报/终局/位置与配对关系，核对规定动作、实际 FIRST 版本和固定 H2 探针及统计/成本。旧 V319 审计直接复用，不重跑旧获取、全部新续跑、模型拟合或 bootstrap。

计入源文件读取、FIRST 恢复、真实续跑、规划、trace 压缩/保存、编译、协调及最终写盘的完整进程树 CPU，核验另计；成功 SOURCE/V317/V319 完整成本引用一次。历史动力学和失败尝试成本未知，不宣称历史总成本闭合。

结论条件于固定 64 位置、既有 FIRST 生命周期/来源、任意 afterstate reset 和规定的续跑策略。本轮可识别教师目标校准差异，不能单独证明该差异造成 V319 的下降；共享参数干扰和状态分配机制仍需独立干预。
