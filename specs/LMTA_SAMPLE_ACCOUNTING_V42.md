# V42：LMTA 原任务的采样记账准备

冻结日期：2026-09-10；本阶段只验证原环境可运行及记账口径。U005 FAIL、U006 未启动及 V41 BA 效率分支关闭保持。

目标是最终比较 LMTA、Flat DQN、WS-option 在同一 AIM 分布上的回报—累计环境样本曲线。论文图中的 epoch 和附录 O 的 55,154 true frames 尚不能直接用作三方法的共同采样预算。本阶段不据此选择有利预算或宣称复现性能。

## 本次执行边界

- 参考实现：[Feng 等 ICLR 2025 官方仓库](https://github.com/wmd3i/HRL4SSCO/tree/d6790c4db0bcc475e74aec267c152d0253959fc6)，版本 `d6790c4db0bcc475e74aec267c152d0253959fc6`。源码位于独立目录 `../acfqp-ws-option-reference-v42-source`，保留发布行为。
- AIM：作者的有向 ER 图生成器，N=500、边概率 0.01、T=10、K=70。规模来自 [LMTA 附录 O](https://arxiv.org/html/2605.17058v1#A15)；这是对参考入口参数的明确调整，非逐项复刻 Feng 的默认 N=200/K=20。
- 固定图 seed=42000，初始化与训练 seed=42001，评价 seed=42002。仅运行一次原 `update_q_function(average, agent)`，再执行一次同图 `run_episode(average, agent, epsilon=0, beam_search=False)`。这是原训练前半程策略的计数探针；同图评价仅验证运行，不作为泛化成绩。
- 不调用 Main 的完整训练、调参、beam search 或检查点保存；不更改原网络、奖励重采、动作屏蔽、状态转移。运行日志及小 JSON 留存本地，训练梯度计入开发成本。
- 使用隔离 Python 环境及 NetworkX 2.8.8 运行原 `to_numpy_matrix`，避免为当前 NetworkX 改写作者源码。

本机准备命令：`python3 -m venv --without-pip --system-site-packages .venv-lmta-v42`，随后 `.venv-lmta-v42/bin/python -m pip install --no-deps networkx==2.8.8 torch-geometric==2.6.1`。其余依赖复用当前已安装的 PyTorch、NumPy、TensorBoard；实际版本写入运行结果。

## 计数及验证

分别记录训练轨迹、奖励估计模拟、评价的 `Env.step` 次数、所请求种子数、空动作调用、非法种子请求及环境内随机数调用。一次 `Env.step` 是一天的传播调用；种子请求是节点动作暴露，二者不相加伪称同一单位。前缀重复模拟中的种子暴露完整收费，不能只计训练轨迹中的 70 次选点。记录高低层优化器更新及阶段墙钟时间，图生成与评价开销分列。

在小图上比较插桩与未插桩的动作、回报、状态及 RNG 终态，检测观察器是否改变实验；若不同，修复观察器后才能运行计数探针。另构造作者支持的早期状态奖励重采见证：固定传入 state、action 与随机流，仅改变 `env.state`，检查原 `Env.step` 是否改变结果；若改变，将其列为同环境比较前必须明确的语义差异，本阶段不暗改。

## 后续决策

实际 LMTA 源码、Flat DQN 的日期推进语义和论文重调 WS-option 配置齐备后，才冻结三臂的完整训练协议：图与随机流分割、环境调用及种子暴露双轴预算、评价频率、训练种子数和停止条件；潜在模型 MCTS 调用和 replay 梯度复用另计计算，不算新环境样本。

若公开入口仍未定位到 LMTA 实现，保留本次可运行的原参考探针及缺项，后续明确选择作者实现复现或标注为独立实现的实验。两者结果不混称；不以 WS-option 的公开旧实现替代 LMTA。
