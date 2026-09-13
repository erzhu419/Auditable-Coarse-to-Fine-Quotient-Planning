# V42：原 WS-option 实际采样计数

2026-09-10，按[冻结探针](../specs/LMTA_SAMPLE_ACCOUNTING_V42.md)完成 AIM N500/T10/K70 一次原训练更新及一次同图评价。3项插桩测试通过，原动作、结果和随机流不变。作者源码版本 `d6790c4db0bcc475e74aec267c152d0253959fc6` 未修改。

| 阶段 | 日传播 Env.step | 请求种子暴露 | 环境 random.uniform |
|---|---:|---:|---:|
| 训练轨迹 | 10 | 70 | 950 |
| 奖励估计的前缀重采 | 1,600 | 5,600 | 77,940 |
| 同图评价 | 10 | 70 | 336 |

训练实际为1,610次日传播调用、5,670次种子暴露，不能只报10天／70选点；两个计量单位不相加。训练含10次高层、10次低层优化器更新，插桩墙钟2.922秒，评价0.106秒。本机RTX4060，不能与论文V100计时直接比较。原训练还发出13次非inactive节点请求，前缀重放含1,260次此类请求。

**已复现一个会改变奖励估计的源码问题**：固定传入state/action/RNG，只把 `env.state` 的节点1设为removed，两节点例子的奖励从2变1。原早期状态奖励重采的邻居筛选读了末态；本探针的1,600次重采均发生传入态与内部态不同。见证另计2次环境调用／3次随机数。原代码行为完整留存，后续独立实现改为只依赖传入状态。

结果：[summary.json](lmta_sample_v42/summary.json)、[逐次调用](lmta_sample_v42/steps.jsonl)。stderr仅一条PyTorch首次cuBLAS上下文初始化警告，进程退出0；没有检查点文件。

## 来源与范围

[Feng等的ICLR 2025论文](https://arxiv.org/abs/2502.05537)及[官方源码](https://github.com/wmd3i/HRL4SSCO/tree/d6790c4db0bcc475e74aec267c152d0253959fc6)可取得，仅12个文本文件100,724字节。仓库README的arXiv编号指向另一篇文章，文献记录采用2502.05537。公开旧实现并不等于LMTA论文调参后的WS-option。

LMTA的[arXiv正文](https://arxiv.org/html/2605.17058v1)、[第一作者](https://vi2enne.github.io/)及[第二作者](https://thwanguk.github.io/)主页所关联GitHub、[ICML入口](https://icml.cc/virtual/2026/poster/60513)及[OpenReview公开记录](https://openreview.net/forum?id=zV5ktcEs8j)尚未定位到作者确认的代码仓库；OpenReview正式PDF及论坛被浏览器验证阻挡。本次没有LMTA作者版本可登记，不能断言作者未公开代码，也不能把旧WS代码的采样计数直接归给论文的55,154 true frames。

用户已选择按论文独立实现。下一步为[明确变体的V43共用环境与三臂训练探针](../specs/LMTA_INDEPENDENT_V43.md)，先计入全部环境与计算开销，再安排正式的多种子样本效率比较。U005 FAIL、U006未启动、V41分支关闭保持。
