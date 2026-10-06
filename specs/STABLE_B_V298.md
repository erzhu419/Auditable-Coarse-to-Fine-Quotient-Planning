# V298：稳定 B 单任务学习与新整局收益

冻结于新获取、拟合与评价之前。主问题是 V291 已确认的完整棋局学习器
在 B(.5) 单独运行能否获得价值更新收益。本轮保持 V290/V291 方法、
alpha=.0025、131,072 raw/life、H2 depth2 与80/20完整游戏分割不变。
64条新 life 0..63，parent=life%4，四个原 V120 来源各16条。
三臂 FROZEN、NORMALIZED_SEQUENTIAL_MC、EPISODE_MEAN_MC，不搜索参数。

## 纯 B 获取和学习

每条历史从原 SOURCE 初始化；没有先行 A 阶段的新价值更新，不载入
V291/V292 目标价值表或目标经历。原 SOURCE 预训练本身仍来自 A。
从空 LIBRARY Beta(1,1) memory 开始，在真实 B 下执行 DIRECT 完整暖启动
直到已观察 raw>=256，初始两块及所有动作后生成块均 observe、全部计费。
随后只读 SOURCE H2 actor 在 B 获取恰131,072 raw，64观察边界提交 memory。
生成规律只使用已观察前缀预测；真实 .5 仅供环境执行和实验记录。
三臂共享这一次物理获取和 memory，SOURCE 始终零新价值更新。

只取预算内自然完整 WON/LOST 游戏，按时间前 floor(4N/5) 拟合，其余
留出。末未完成游戏不补未来后缀、不拟合，但其初始块、动作与 raw 全付费。
两学习臂从原 SOURCE 各复制一张私有表，拟合同样 nonwinning afterstates，
winning 解析处理；MC 后缀、offset、32特征重数与地址归一化原样用 V290。
真实 cutoff 留存后中止获取，不能伪造完整终态训练标签。

## 新评价与判定

每臂/life32个新完整配对 B 棋局，共6,144局；固定当前价值表及
fit-prefix memory 预测 p（不是预算末 memory，也不输入真实 .5）。
评价不更新价值或 memory，不改变获取 stream。MAX_STEPS=8192，
全部 WON/LOST/CUTOFF 明确留存，cutoff 不能支持完整整局收益。

主端点 EPISODE_MEAN_MC−FROZEN utility=score/2048±4；先游戏均重、
再 life 均重，四固定来源内各重采16条完整 life，20,000次bootstrap，
seed29800001。下界严格>0且获取/评价无cutoff才支持稳定 B 价值学习收益。
NSEQ−FROZEN、MEAN−NSEQ、完整 heldout MSE/MAE/bias 为预定次端点，
预测改善或次端点不能替代主收益；全部有符号差与退化历史保留。

暖启动seed298100000000+life×1000000+game；连续获取seed
298200000000+life×10000000；评价seed298900000000+life×1000000+game。
三个新流家族与旧实验分开，不筛历史、不追加样本、不中途调整算法。

## 成本与后续

经济训练费用含原 SOURCE价值训练、动力学，以及全部新 B 暖启动和
获取；共享物理费用付一次，各臂处理/写表/预测/规划/评价按实际工作留存。
V291 原 target 获取与评价是既有开发费用，不作为新拟合输入，也不二次
计入 SOURCE 预训练。记录源码/私有表复制、缓冲峰值、编译、worker、
协调 CPU及墙钟。canonical gzip 与中途产物只放 reports/stable_b_v298/；
不存新 checkpoint 或大棋盘 CSV。

若主收益成立，下一阶段做同预算 fresh B 与 A 后 B 的配对干预，
定位先行 A 更新的影响，再设计持续迁移与保留；本轮正结果本身不证明
此前连续失败由 A 干扰造成。若未成立，保留失败，转向 B 学习目标与
决策接口诊断，不调 alpha、预算或种子追正。无论结果如何，本轮仍是
离线单任务确认，不证明在线持续学习、结构学习或一般战略。
原 U005 Gate保持FAIL，U006不启动；本轮不是原正式 Gate。
