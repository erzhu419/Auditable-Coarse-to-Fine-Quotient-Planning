# V321：四步奖励目标未证实修复查询学习退化

实验完成，独立核验 PASS；科学修复条件未成立。唯一主终点 NSTEP_QUERY−OLD_QUERY 为 **+0.134449，95% CI [−0.139427, +0.417099]**，UNRESOLVED，10 个生命周期正、6 个负，四个父组均值两正两负。

| 最终 A/B 等权 utility 对比 | 均值 | 95% CI |
|---|---:|---:|
| 新 QUERY 奖励目标−旧 QUERY，唯一主终点 | +0.134449 | [−0.139427, +0.417099] |
| 新 QUERY−自身 FIRST，nominal secondary | −1.714714 | [−2.188809, −1.239140] |
| 新 QUERY−新 FACTUAL，nominal secondary | −2.274265 | [−2.714496, −1.853250] |
| 新 FACTUAL−旧 FACTUAL，nominal secondary | +0.328756 | [−0.074436, +0.706032] |

新 QUERY−FIRST 在 A 为 −1.810215，CI [−2.342247, −1.208121]；B 为 −1.619213，CI [−2.237143, −1.013051]，均支持损失。新 QUERY−FIRST 的 15/16 生命周期为负，新 QUERY−新 FACTUAL 全部 16 个为负。`repaired_query_supported=false`，不是净学习收益。

全部原 16,384 根组/四成员保留。128 个旧标签版本在任何新采样前精确重现 V319；只替换奖励标签，WIN 标签及每轮风险参数与对应旧臂精确相同。固定总计四个动作：原 DIRECT 首动作后执行冻结 FIRST H2，第四次 swipe 后、spawn 前用 FIRST_R 补尾项。

8,388,608 条目标续跑中 20,165 WIN、77,436 LOST、8,291,007 BOOTSTRAPPED，后者占 **98.84%**。新 QUERY 的奖励标签平均变化仅 +0.044752，FACTUAL 为 −0.186703。新训练采样 **24,978,516 raw**，另 6,144 局自然评估获取 4,953,025 raw，全部自然终局。OLD 臂没有本轮新目标采样，NSTEP 臂完整承担获取成本。

54 个不同有限案例通过。独立 reader 核对全部 33,289,688 次新 swipe、49,957,032 次目标 RNG draw、逐成员 FIRST_R 尾项、128 个旧头控制/风险参数一致性及 3,308 个 FIRST H2 探针。实验与核验均 exit 0、stderr 0 字节。

完整实验进程树 CPU **1,160.003667 秒**、单调墙钟 **320.329988 秒**；组件小计 1,155.607016 秒，最终序列化/退出另 4.396651 秒。成功 SOURCE/V317/V319 引用一次后经济 CPU **4,172.971763 秒**。V320 诊断 425.578459 秒单列；本轮核验 CPU **599.469688 秒**、墙钟 **165.174266 秒**另计。新 trace/目标压缩文件分别约 179.2/385.4 MB。

## 范围与下一主线

后续 [V322 保存头组件交叉](COMPONENT_HEADS_V322_RESULTS.md) 已完成并核验 PASS：当前奖励更新在两种 WIN 头下均造成退化，WIN-only 是待新执行流验证的开发候选。

本轮未证实该四步干预改善行为，仍不能断言奖励偏差已消除或不是原因：绝大部分目标仍使用同一 FIRST bootstrap。统计条件于既有 16 个 FIRST 生命周期/四个父来源，以生命周期配对重采样；secondary 为 nominal，不建立独立确认、普通在线采样效率或一般战略学习结论。历史动力学及失败尝试成本未知。U005 FAIL 保留，U006 未运行。

下一主线将已保存的奖励头 FIRST/NSTEP_QUERY 与 WIN 头 FIRST/UPDATED_QUERY 交叉。复用 V321 已支付的 FIRST、NSTEP_QUERY 及配对流，只新增“新奖励+FIRST WIN”和“FIRST 奖励+更新 WIN”两臂，2048 局，零新训练样本和零拟合。预先以恢复 FIRST WIN 后相对 NSTEP_QUERY 的收益为主检验，纯奖励、纯 WIN、交互与 A/B 为次级；机制诊断不充作独立确认。自然评估 raw 硬上限 16,781,312，当前观察估计评估 CPU 约 53.18 秒，恢复/存储成本另计；本轮没有启动该实验。

证据：[协议](../specs/REWARD_TARGETS_V321.md)、[配置](reward_targets_v321/configuration.json)、[完整结果](publication/v327_snapshot/reward_targets_v321/summary.json.gz)、[全队列控制](reward_targets_v321/control_phase.json)、[核验](reward_targets_v321/audit.json)、[完整成本](reward_targets_v321/audit_costs.json)。
