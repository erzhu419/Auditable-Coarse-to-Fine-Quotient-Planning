# V292：自然连续整局学习、修正与能力保留

在正式获取前冻结。沿用通过V291确认的V290学习实现，alpha=.0025，
四个原V120 risk_goal@4096来源，16条新life，parent=life%4；每来源4条。
本轮不调方法、阈值、来源或预算，不筛除退化历史，不按结果追加样本。

## 连续执行与控制

五臂FROZEN_H2、NSEQ_H2、MEAN_H2、FROZEN_DIRECT、MEAN_DIRECT。
NSEQ使用NORMALIZED_SEQUENTIAL_MC，MEAN使用EPISODE_MEAN_MC；每个学习臂
只有一张从来源初始化的持续价值表，不新加持久价值模块。
同life做一次共享DIRECT完整暖启动直到所有raw观察>=256，导入LIBRARY
memory后克隆给五臂；价值不更新。每臂连续获取A(.1)→B(.5)→A_prime(.1)，
每阶段恰131,072 raw，包括initial，合计每臂6,291,456 raw、物理31,457,280。
共同连续随机流每raw取cell/rank两次draw；同raw位置的rank与memory
在五臂相同，棋盘、游戏长度、训练样本数允许因策略而不同。
H2用depth2，DIRECT用真实depth1选择；模型只使用已观测prefix概率，
阶段标签与真实p仅用于环境执行及留存，不能供价值拟合或控制器选择。

## 当局反馈与提交时序

native在raw预算边界、64raw memory边界或首个真实游戏终态立即返回，
动作执行期间价值表只读，不触发旧SARSA。host提交全部已发生raw反馈，
重构实际afterstate与奖励；真实完整WON/LOST游戏才调用冻结V290整局拟合，
之后才能执行下一游戏的初始化和动作。拟合只用实际suffix，排除winning
afterstate，offset扣一次，32次特征重数/地址归一化完全沿用V290。
阶段边界不重置棋盘、RNG或未完成游戏；跨阶段完整游戏使用实际混合轨迹，
按其终态所在阶段留存拟合，不能标成纯阶段标签或补未来后缀。
最后未完成游戏不拟合但全部付费。MAX_STEPS8192；真实cutoff显式保留，
不当成LOSS标签、不拟合；出现cutoff不能声明自然完整连续学习确认。

## 独立完整棋局与端点

每阶段末每臂32局同life/phase种子配对评价，固定当前head与memory预测p，
真实环境使用该阶段规律，无价值/memory反馈，也不改变训练stream。
主端点MEAN_H2−FROZEN_H2的三阶段等权utility，游戏→阶段→life等权，
95%CI下界>0且训练/评价无cutoff才支持在线净收益。
各阶段差、NSEQ_H2−FROZEN_H2、MEAN_H2−NSEQ_H2以及两DIRECT控制为预定
次比较；FROZEN_H2−FROZEN_DIRECT隔离固定知识下规划，MEAN_H2与MEAN_DIRECT
因训练轨迹不同仅比较完整闭环方案，不能称为同叶规划贡献。

为识别B期间价值修正，保存MEAN_H2的只读A末head，在B末使用同一当前
B belief、B真实规律和B评价种子与当前head配对评价，不新增训练臂。
修正端点theta_B−theta_A_on_B，CI下界>0才确认B价值更新带来收益。
另保存A末预测p和A评价种子，在B末/A_prime末全部五臂固定这两项做
A规律探针；A末当前评价共享为原A探针，只物理计费一次。
分别报告after_B−after_A、after_A_prime−after_B、after_A_prime−after_A。
区间跨0不能当作保留已证明；不引入任意非劣界。共13,312个完整评价。
四个固定来源内各重采4整life、20,000次、seed29200001；全部有符号
差与退化例保留，区间条件于旧来源，不声称一般战略或结构学习解决。

## 种子、成本与留存

warmup=292100000000+life×1000000+game；连续training=
292200000000+life×10000000；eval=292900000000+life×1000000+
phase_index×100000+episode。三个新家族分离。A探针复用本轮A评价流，
theta_A_on_B复用本轮B评价流，其余无复用旧实验目标数据。
逐臂经济成本含四来源价值训练/动力学、共享暖启动与该臂全部新raw；
物理暖启动与来源取得一次，五条训练轨迹分别计费，评价另列实际成本。
保留样本、suffix构造、真实写表、聚合/归一化、缓冲峰值、head复制
（包括A参考head）、环境、memory、规划和CPU/墙钟；不宣称相同样本或CPU。
所有文件在reports/natural_episode_v292/；compact gzip留actual raw/动作/
得分、整局拟合和评价收据，不存新checkpoint或大棋盘CSV。

若在线收益、B修正或A保留失败，完整报告哪项成立，不以其他端点替代。
若观察到真实价值遗忘，再针对这一机制设计下一阶段，而不预先添加模块。
原U005科学Gate仍FAIL，U006不启动，本轮不是原正式Gate。
