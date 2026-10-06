# V321：固定根的奖励目标配对干预

冻结日期：2026-10-06。V320 已发现查询教师奖励目标低估，本轮检验替换奖励目标是否修复行为；不以校准均值加常数。复用已核验 V319 的全部 16 个 FIRST 生命周期、四个 SOURCE、A/B 实际 FIRST v0 与规划信念。U005 FAIL 保留，U006 不运行。

## 干预与成本

四臂为 OLD_FACTUAL、OLD_QUERY、NSTEP_FACTUAL、NSTEP_QUERY。每任务/轮次保留全部原 16,384 根组及四个成员，严格原顺序、alpha=.0025、两轮与原 grouped LOCAL 更新。所有 OLD 头的每轮实际参数增量须与 V319 精确相同；全队列控制成功后才开始新采样，否则 HOLD，无新目标获取。

NSTEP 只替换奖励标签，WIN 标签逐成员保持原 V319 数值。首 spawn 和 DIRECT 动作复用原记录。之后冻结 FIRST H2 在真实环境中行动，预先固定总共最多 **4 个动作**，不做步数搜索。若初始 LOST，目标 R=0；若提前 WIN/观测到 LOST，R 为已执行 score/2048；否则在第四次 swipe 的 **afterstate、尚未 spawn** 处停止，R=score/2048+FIRST_R(afterstate)。不包含进入原 root 的动作奖励。最后一步不产生新的 spawn；此前非 WIN 动作后需要继续时才产生 spawn。这是有效的有限步 bootstrap 目标，不是终局真值；BOOTSTRAPPED 不视为 CUTOFF 或 LOST。

每成员独立 mt19937_64 seed=`321500000000+life*10000000+task_index*1000000+round*100000+group*4+member`，两根分布配对，同一分布的标签对共用数据；流从 DIRECT 后的新 spawn 开始。新获取最多 25,165,824 raw，提前终止的全部保留。不重复首 spawn、来源训练、首次适配、旧 tapes 重构或旧审计。新获取物理生成一次，其实际成本完整归属 NSTEP 臂；OLD 不宣称享有同采样预算。

旧奖励/WIN 及新奖励逐组拟合，当前预测一次更新；各分布的新旧臂风险参数每轮须精确相同，非激活 A/B 头和 FIRST 保持只读。保存版本链、全部新 swipe/可选 spawn、目标、最后 afterstate、真实成本，以及真实调用中每批 first8/last8 成员的首末 H2 探针。无需逐步重复棋盘。

## 终点与推断

仅在两轮完成后，对 SOURCE、FIRST_LOCAL 和四臂各执行任务 A/B 的 32 个全新自然游戏。统一 H2、原库信念、true p_four A=.1/B=.5、max_steps8192。每场 seed=`321900000000+life*1000000+task_index*100000+episode`。6144 场评估，无拟合；自然游戏仍采用原约定，含 WIN 动作后的 spawn。任一自然 CUTOFF 使全队列推断 HOLD，不替换种子或把截断当负终局。

唯一主终点为最终 A/B 等权 utility 的 NSTEP_QUERY−OLD_QUERY。utility=score/2048+8*WIN−4。16 生命周期作为配对统计单位，在四个固定父组内重采样 20,000 次，seed32100001，所有对比共用抽样。CI 下界>0 支持干预收益，上界<0 支持损失，其余未解决。

NSTEP_QUERY−FIRST、−SOURCE、−NSTEP_FACTUAL，NSTEP_FACTUAL−OLD_FACTUAL、两种根分布的干预差之差为 nominal secondary。阶段性修复须主终点与自身 FIRST 比较均支持收益，且最终 A、B 各自 NSTEP_QUERY−FIRST 的 CI 下界>=0；不把相对退化控制的改善称为净学习成功。没有无条件父来源复现或普通在线采样效率结论。

## 核验与范围

独立 reader 重放全部新物理/RNG、逐成员 FIRST 奖励尾项、规定动作及 H2 探针，核对旧头控制、未改的 WIN 参数、评估种子/自然终点、统计单位、成本。核验不重新训练、执行全部新策略或重跑 bootstrap。

完整成本计入控制重放、读取、版本恢复/保存、生成目标、拟合、评估、编译、协调、最终序列化和退出的进程树 CPU。成功 SOURCE/V317/V319 成本引用一次；V320 诊断与独立核验成本单列。所有输出在 reports/reward_targets_v321。历史动力学和失败尝试成本未知。

本轮检验固定根分布下的奖励目标干预，仍有 FIRST 策略与 bootstrap 偏差、共享表示干扰及额外生成器采样成本；不能单独将变化归因于所有目标误差已消除。
