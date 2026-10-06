# V319：查询状态监督的有效负结果

本轮实现并跑完了固定 FIRST 教师下的查询状态监督。工程执行完整、独立核验 PASS；唯一自身增长主终点为 **SUPPORTED_LOSS**，当前方案关闭。增加规划查询状态的监督没有解决两任务能力保留问题。

FACTUAL_LOCAL 与 QUERY_LOCAL 共享实际 FIRST 决策锚点、教师、更新规则与配对真实 spawn；只改变接受监督的 afterstate。查询根按实际 H2 预测调用次数随机选取，保留重复调用，不按预测值筛选。

| 最终 A/B 等权整局 utility 差 | 均值 | 95% CI |
|---|---:|---:|
| QUERY−自身 FIRST，唯一主终点 | −1.533998 | [−1.950912, −1.112646] |
| QUERY−FACTUAL，监督位置干预 | −1.622478 | [−2.031787, −1.220476] |
| QUERY−SOURCE | −0.641771 | [−1.117845, −0.183680] |
| FACTUAL−自身 FIRST | +0.088480 | [−0.286783, +0.508665] |
| FACTUAL−SOURCE | +0.980707 | [+0.617755, +1.365912] |
| FIRST−SOURCE | +0.892227 | [+0.609025, +1.193562] |

QUERY 比 FACTUAL 在全部 16 个生命周期里都差，四个父组均值都为负。QUERY 相对自身 FIRST 的 A 为 −1.877758，CI [−2.620885, −1.123829]；B 为 −1.190239，CI [−1.808585, −0.595744]。两个任务均支持下降，保留增长未建立。FACTUAL 对 SOURCE 的优势包含已有首次适配；继续学习的增益未获支持。

每臂严格使用 4,194,304 个新训练 raw、1,048,576 个四样本根组；物理合计 8,388,608 raw。实际参数写入分别为 FACTUAL 65,882,932、QUERY 66,242,056，按状态产生的地址重复不同，因此没有宣称写入量或 CPU 完全相同。共同查询选择工作物理运行一次，经济上计入两臂。

6,144 个新配对自然 H2 游戏全部终局，没有 CUTOFF。42 个不同的新有限检查最终通过；两处 JSON 列表/元组 fixture 比较失败及各自修复日志保留。正式实验与独立核验均 exit 0、stderr 0 字节。

独立核验检查全部新真实 spawn、联合目标/动作、组均值、所有 census 查询路径和 selector draw、128 个私有头版本及 1,024 个 FIRST H2 决策探针，结论 `independent_valid=true`。旧完整审计、全部模型拟合、评估和 bootstrap 没有重跑。

完整实验进程树 CPU **445.878278 秒**、单调墙钟 **143.581986 秒**；生产者组件小计为 442.121108 秒，完整测量另含最终序列化/退出的 3.757170 秒。成功 SOURCE/V317 引用一次后的完整经济 CPU 为 **3,012.968096 秒**。新独立核验另计 CPU **184.102707 秒**、墙钟 **197.573045 秒**。

## 范围

区间条件于四个冻结 SOURCE 与既有 16 个 FIRST 生命周期，使用父组内配对 bootstrap 20,000 次。两臂都有任意 afterstate reset 的生成式访问，标签是冻结 FIRST 的一步 bootstrap；本轮没有新首次适配或独立训练确认。损失不能单独证明整个表示框架无效，也没有拆开教师目标偏差、共享参数干扰与状态分配的贡献。历史动力学及 V317 失败尝试 CPU 仍未知。原 U005 FAIL 保留，U006 未运行。

## 下一条主线

固定本轮根状态及预先声明的共同位置前缀，沿留存的真实首次 spawn 和已选 DIRECT 动作，用冻结 FIRST H2 续跑到自然 WON/LOST。比较保存的一步目标与真实后续奖励/WIN，完整计入续跑样本和计算；任何 CUTOFF 保留为 HOLD。

先检验查询根上的教师目标是否比自然根更偏，再决定是否实施目标语义干预。该诊断不拟合新头、不修改 selector、alpha 或已有终点；它本身也不能证明目标误差造成了本轮行为下降。共享参数干扰留待后续独立干预。

该诊断已在 [V320](TEACHER_CALIBRATION_V320_RESULTS.md) 完成；共同前缀在采样前改为固定等间距位置，原前缀未运行，设计与结果另行留存。

证据：[冻结协议](../specs/QUERY_SUPERVISION_V319.md)、[配置](query_supervision_v319/configuration.json)、[完整结果](publication/v327_snapshot/query_supervision_v319/summary.json.gz)、[独立核验](query_supervision_v319/audit.json)、[执行测量](query_supervision_v319/execution.json)、[核验测量](query_supervision_v319/audit_execution.json)、[完整成本](query_supervision_v319/audit_costs.json)。
