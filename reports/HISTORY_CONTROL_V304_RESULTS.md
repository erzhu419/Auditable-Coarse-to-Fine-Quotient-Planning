# V304：同一 B 事实下的参数历史对照

定位到当前主瓶颈：A1 参数历史导致本次 B 学习负迁移。
同一批 B 数据、目标、顺序、学习率和评价种子，从原 SOURCE 开始的
LOCAL 比继承 A1 高 **+1.546751，95% CI [1.235445, 1.849899]**；
55/64 生命周期改善，四父组均值全部为正。

| B 完整游戏对照 | Δutility | 95% CI |
|---|---:|---:|
| LOCAL fresh − inherited | +1.546751 | [1.235445, 1.849899] |
| LOCAL fresh − SOURCE | +0.374689 | [0.060634, 0.684168] |
| LOCAL inherited − SOURCE | −1.172062 | [−1.538495, −0.810999] |
| MC fresh − inherited | +1.302858 | [0.998708, 1.601097] |
| MC fresh − SOURCE | −1.416541 | [−1.830604, −0.995156] |

LOCAL fresh / inherited / SOURCE 分别获胜 630 / 396 / 529 局，
各 2,048 局；MC 同样受历史损害，但从 SOURCE 重学仍然失败。
继承分支全部 A1/B 拟合、B 留存预测及评价游戏精确复现 V303。
45 项新增有限测试通过，独立审计 PASS、valid=true，stderr 0。
新评价 8,192 局全部自然终止；SOURCE 2,048 局复用，新增训练采样为零。

B 输入 8,419,181 raw，继承臂额外 A1 输入 8,443,043 raw。
计入原 SOURCE/dynamics，SOURCE/fresh 为 19,698,773 raw，继承为
28,141,816 raw；只匹配 B 预算。实际新增 worker CPU 555.15 秒、
compiler 17.02 秒、coordinator 8.04 秒，wall 159.81 秒，分量不重复相加。
LOCAL 参数写入仍是 MC 两倍。

[冻结协议](../specs/HISTORY_CONTROL_V304.md) · [终态与成本](publication/v327_snapshot/history_control_v304/summary.json.gz)
· [独立核验](history_control_v304/audit.json)。

## 局限与下一步

这是四个固定父模型、留存 B 数据和原评价种子的受控诊断，不是新独立确认。
已定位参数历史的因果影响，尚未区分奖励头、风险头及共享地址的具体贡献；
持续学习修复仍未完成，历史总计算成本也未闭合。下一步实现由已观测环境
统计条件化的持久价值/风险参数，直接检验 A→B→A 双任务收益与保留；
用共享参数及只改变规划信念的分支作对照，并计入路由、额外参数和历史成本。
U005 仍为 FAIL，未启动 U006。
