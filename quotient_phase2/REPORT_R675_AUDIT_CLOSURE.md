# R675 审计独立决断与收口报告（SISC 文字定稿 + Phase-III `v4` 数值契约加固、线性算子基线与四层误差分解）

> **基线提交**：`67532c91d6c43a32d0f4d0277ad28cd059e5a28b`（`feat/green-kriging-control-1a`）  
> **审计输入**：[GPT_diagnosis_R675.md](../markdown/R675_Audit_Evidence/GPT_diagnosis_R675.md)、[R675_FULL_AUDIT_ZH.md](../markdown/R675_Audit_Evidence/R675_FULL_AUDIT_ZH.md) 及 `markdown/R675_Audit_Evidence/checks/` 全部复现探针  
> **历史归档 100% 字节冻结（共 46 个历史代码与 JSON 文件零改动）**：
> - Phase-I `green_response/*.py`：`271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d`
> - Phase-II `quotient_phase2/*.py`：`e6ea565b8a4e87e7298c93bf01351ee5c2787fed3a91fc6a7caebcfe4b44e9c6`（含全部 13 个历史 JSON，其中 `m233_sisc_unlock_results.json` `339e723f...`、`m233_clean_isolation_replication.json` `73101638...`）
> - Phase-III `v1` `p3_neurips_benchmark_results.json`：`0e2c76ea204ba7ad66341d243ee0d992e23158d16573a430d0ab602d6f98e161`
> - Phase-III `v2` `p3_v2_verified_benchmark_results.json`：`6167bd5f3e27218d7d7d0bb8f0986a79f020765daaeabf4adb8a18c9ab7d0dd3`
> - Phase-III `v3` `p3_v3_r747_delivery_verified_results.json`：`0ffd1d3a0a22a25c6c1a9a70413c64ed267864905e7c78a478cb7f85b77847a8`
> - **Phase-III `v4` 新增验证台账** [p3_v4_r675_verified_results.json](../learned_portal_phase3/p3_v4_r675_verified_results.json)：`798a9e2b300a1d3898b55a91f00b771f4d3487c9b5322abfbddb61417cbd6580`（`phase3_package_py_sha256: a2bb98b4...`）

---

## 1. 对 GPT6 `R675` 审计的独立评估：采纳哪些、拒绝哪些

GPT6 在 `R675` 中首先独立确认了 `67532c9` 的实质进展：官方 `18/18` 契约门零警告通过、`166/166` 项 SISC 与溯源检查及 `592/592` 项 Phase-III 逐事件归约零差异，`R747-P0-01`（`E2` `192/192` 策略交付）与 `R747-P0-02`（`E3` `96/96` 零静默回退、`100.0%` 到达率、`1.521` 代价逆转 `v2` 假阴性）均已真正闭环。在此基础上，我们对 GPT6 提出的后续清单作出如下独立裁定：

### 1.1 全量采纳并落地的核心技术与文本项
1. **Track A（Phase-II SISC 论文线，`SISC-D01..D05`）：100% 采纳纯文本/引文微调，零代码改动、零重跑实验**：
   - 修正 `REPORT_R747_AUDIT_CLOSURE.md` 中 `0.0649` 的统计检验标签（明确其为 lifecycle 双侧配对 $t$ 检验 $p$ 值，精确符号翻转/Wilcoxon 为 `0.15625 / 0.09375`）；
   - 移除 `MANUSCRIPT_CORE_DRAFT.md` 第 6.2 节单线程段落中残留的旧 3-worker `M2.3.1` `4.74x` 从句；
   - 在 `Table 1` 内存渐近式中区分房间下标 $c$ 与轮次下标 $\ell$，并补齐缓存房间内部向量 $y_c$ 的 $\mathcal{O}(\sum_{c=1}^C n_{\mathrm{cache},c} N_c)$ 项与离线摊销说明；
   - 在摘要补入 $W_{\mathrm{lo}} > 0$，将 `Theorem 2` 写明为“不离开 $I_{\mathrm{reach}} \cup G$”；
   - 修正 `Ringstrom & Schrater (2019, arXiv:1901.10405)`、`Rasmussen & Williams (2006)`，并将第 6.3 节 SVD/DWR 负结果严格限定于所测构造。
2. **Track B（Phase-III SPQL `v4` 线，`R675-01..11` + Work Package D 四层分解）：100% 采纳契约闭合、基线公平化与科学分解**：
   - **`R675-01 (P0)` Tier-3 外向舍入与 $2^{-1074}$ 渐进下溢闭合**：移除 `higham_verify_upper_subsolution` 与 `higham_verify_lower_supersolution` 中未声明的 `max(..., 1e-12)` 地板（恢复严格的代价量纲等变性），在下界验证器中补齐 $(d_i + 1)2^{-1074}$ 乘积下溢项，采用 `-math.expm1(-x_dn)` 下向舍入计算收缩裕度，并对比值与终端 `log` 读数全面执行 `np.nextafter` 外向舍入。
   - **`R675-02 (P0)` 对数空间逐行归一化 `CSR` 策略与证书 SHA-256 绑定**：移除 `max(w_sum, 1e-300)` 分母地板，改为逐行最大对数权重平移 $\log w_{ij} - \max_k \log w_{ik}$（直至 $2^{-1074}$ 均严格行随机），并新增 `verify_and_bind_deployed_policy_csr` 直接在交付的 `Pi_csr` 对象上核验行和、观测支撑、前向可达恰当性、外向 Bellman-KL 步漂移上界及规范化 `policy_sha256`。
   - **`R675-03 & R675-04 (P1)` 严格线性 `MatrixFree` 算子与原生局部 LU 分账**：移除 `MatrixFreeSpectralSchurPACPlanner._apply_K_ext` 内部的 `np.maximum(..., 0.0)` 截断使传给 `bicgstab` 的 `LinearOperator` 满足精确线性性（`oddness_err = 0.0`），记录 `bicgstab_info / rel_res`；为 `Uncompressed` 传入 `build_initial_l0_cache=False` 消除构造器无效 `L0` 求解与计数器清零；将**原生局部房间 LU 回代列数**、**目标侵入房间重分解次数**与**全局外部回退 LU 调用次数**彻底分列。
   - **`R675-05 (P1)` 完整逐任务事件导出**：在保持 `v1/v2/v3` JSON 字节不动的前提下，于 `p3_v4_r675_verified_results.json` 完整导出 `E1 240k`（`512` 事件）、`E2`（`768` 事件）与 `E3`（`672` 事件）共 **`1,952` 条逐任务记录**，同时报告 `uncapped_regret` 与 `capped_score_80`。
   - **`Work Package D`（同数据四层分解 + 后验变分对偶命题 `Proposition 5`）**：在不新增任何地图或随机种子的前提下，精确量化 `V*_true`、`PlugIn_CE`（及其同置信集后验 PAC 上界 $\overline{J}_{\underline{M}}(\hat{\pi}_{\mathrm{CE}})$）、`Full_PAC` 与 `Coarse_SPQL` 的四层代价与证书宽度分解。
   - **`R675-06..11` 理论与文献对齐**：统一 `Theorem 4` 正文与附录的 $3\times(\delta/3)$ 事件预算及平移不变条件 $V^*_{\mathrm{true}} - \phi_{\mathrm{goal}} \le V_{\max}$；删去普适 $\Theta(1)$ Doob 缩放声明（指出深度 $d$ 二叉 DAG 上 $u_{s_0} = 2^d$）；在正文显式增补 **Infante, Jonsson, & Gómez (AAAI 2022)** 的分层 LMDP 对比定位。

### 1.2 明确拒绝的保守扩围倾向
- **拒绝新增确认集种子或扩展新环境**：严格在既有 `seeds 4000..6007` 上完成受限审计复核，并在正文与 JSON 台账中诚实声明其为固定种子修复台账（而非新抽样确认队列）；
- **拒绝在策略未变时重跑 `E3` 连续轨迹采样**：遵循 `R675` 第 9.3 节准则，先核验全部 `96 × 7 = 672` 个离散地标策略指纹，确认 `max ||Pi_v4 - Pi_v3||_inf = 8.77e-15 <= 1e-12` 且状态完全一致后，**零次重跑连续轨迹**，杜绝随机重采样刷统计量；
- **拒绝对 `sp_beta.ppf` 本身套用区间算术包装器**：直接将 Tier-3 精确界定为“在 $\mathcal{E}_{\mathrm{valid}}$ 成立前提下，对内存中存储的 `float64` 包络算子与实际交付的 `CSR` 策略对象执行 IEEE-754 外向舍入验证”，边界清晰且无过度声称。

---

## 2. 独立反例探针与 `20 / 20` 确定性契约门复核结果

在 `-B -W error` 单线程环境下，GPT6 的全部 `R675` 独立反例探针与扩展后的 `P3-C01..P3-C20` 契约套件（`11.77s`）全部一次通过：

| 反例探针 / 契约门 | `67532c9`（修复前）表现 | `v4`（修复后）实测结果 | 状态 |
| :--- | :--- | :--- | :---: |
| `7`-态 $2^{-1074}$ 渐进下溢下界探针 (`P3-C19a`) | `L = 744.440 > V* = 743.852`（假阳性） | `L = 739.845 <= V* = 743.852`（`false_accept = False`） | **CLOSED** |
| `q_min ~ 1e-15` 上界地板探针 (`P3-C19b`) | 因 `max(q_min, 1e-12)` 静默放行 | Fail-closed 拒绝（`accepted = False`） | **CLOSED** |
| `(lam, q_min)` 乘 `1e-15` 量纲等变探针 (`P3-C19c`) | 常尺度拒绝、缩放后错误接受 | 常尺度与缩放尺度一致拒绝（严格等变） | **CLOSED** |
| `q_min ~ 1e-15` 收缩裕度下界探针 (`P3-C19d`) | `L = 2.3026 > V* = 0.6923`（假阳性） | `L = 7.77e-16 <= V* = 0.6923`（`false_accept = False`） | **CLOSED** |
| `q = 0.1` 终端读数外向舍入探针 (`P3-C19e`) | `L - 0.1 = +1.39e-17`（1-ULP 上漂） | `L - 0.1 = -3.61e-16 <= 0.0` | **CLOSED** |
| `1e-310` 策略行归一化与篡改拒绝 (`P3-C19f`) | `row_sum = 1.25e-10`（非行随机） | `Pi = [0.2, 0.8]`，`row_sum = 1.0`，篡改 `CSR` 被拒绝 | **CLOSED** |
| `MatrixFree._apply_K_ext` 线性性探针 (`P3-C20a`) | `||K(1) + K(-1)||_inf = 0.961`（非线性） | `oddness_err = 0.0`，`linearity_err = 6.94e-18` | **CLOSED** |
| `Uncompressed` 构造器计数清零探针 (`P3-C20b`) | 丢弃初始 `L0` 求解并重置计数器 | `build_initial_l0_cache=False`，`discarded_rhs = 0` | **CLOSED** |

---

## 3. 核心科学发现：同数据四层代价与后验证书分解（回应 `R675` 第 10 节核心之问）

GPT6 在第 10 节提出了一个极为关键的审稿人问题：*既然 `PlugIn_CE` 经验遗憾更低，如果用确定性等价策略做控制、再用后验 PAC 包络给它出证书会怎样？为什么悲观 PAC 规划的经验代价更高？*  
我们在 `Proposition 5`（变分对偶引理）与同数据四层分解（表 1）中给出了精确的数学与实证回答：在 $\mathcal{E}_{\mathrm{valid}}$ 下，$U_{\mathrm{PAC,full}} = \min_\pi \overline{J}_{\underline{M}}(\pi) \le \overline{J}_{\underline{M}}(\hat{\pi}_{\mathrm{CE}})$ **恒成立**；一旦 $\hat{\pi}_{\mathrm{CE}}$ 把概率权重押在低计数捷径边上（$\underline{p}_{ij} \ll \hat{p}_{ij}$），其后验最坏情况界就会急剧膨胀：

| 数据集（任务数，零新种子） | `V*_true`（真值最优） | Level 1: `PlugIn_CE` 实际代价 $J$（估计遗憾） | `PlugIn_CE` 的后验 PAC 上界 $\overline{J}_{\underline{M}}(\hat{\pi}_{\mathrm{CE}})$ | Level 2: `Full_PAC` 实际代价 $J$（保守性代价） | `Full_PAC` 证书上界 $U_{\mathrm{PAC,full}}$ | Level 3: `Coarse_SPQL` 实际代价 $J$（门户粗化代价） | `SPQL` 证书上界 $U_{\mathrm{SPQL}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **E1 2D 旋转九宫格 (`128`, 240k)** | `14.27` | **`16.46`** (`+2.19`) | **`159.36`** (`128/128` $\ge U_{\mathrm{PAC}}$) | `24.907` (`+8.44` vs CE) | **`67.73`**（较 CE 后验界收紧 **`57.5%`**） | `24.905` (**`-0.002`**，粗化损失 `0.0%`) | `69.25` |
| **E2 3D 弯曲洞穴 (`192`, 460k)** | `19.48` | **`37.01`** (`+17.54`) | **`973.30`** (`192/192` $\ge U_{\mathrm{PAC}}$) | `63.30` (`+26.28` vs CE) | **`218.44`**（较 CE 后验界收紧 **`77.6%`**） | `63.76` (**`+0.466`**, $p_{2s}=0.00255$) | `234.02` |

- **结论极其清晰**：悲观规划多付出的经验代价（2D `+8.44`、3D `+26.28`）并非门户抽象的损失，而是**换取最坏情况 PAC 证书收紧 `57.5%–77.6%`（`973.30 -> 218.44`）并消除 `94.5%–100%` 乐观低估违约的固有统计代价**；而 `SPQL` 将活跃门户自由度压缩 `83.3%`（`577.25 -> 96.26`）所引入的门户粗化代价在 2D 为 **`0.00%`**，在 3D 仅为 **`+0.466`（占总遗憾的 `1.05%`、部署代价的 `+0.74%`）**。同时，在 `E1 240k` 上，`SPQL_Active` 主动瓶颈探索在全部 `8/8` 个种子上一致降低无截断遗憾（`7.81` vs. `10.63`，$p_{2s} = 8.48\times 10^{-6}$，精确符号翻转 $p_{2s} = 0.00781$）与证书宽度（`47.44` vs. `69.18`，$p_{2s} = 9.28\times 10^{-7}$）。

---

## 4. `E2` 线性化 `MatrixFree` 基线与 `E3` 策略指纹核验汇总

1. **Block E2（3D 弯曲洞穴，`192 / 192` 策略交付，`0` 零容差 PAC 违约）**：
   - 恢复 `_apply_K_ext` 严格线性性后，`Linear MatrixFree_SpectralSchur_PAC` 在 `192/192` 任务上 `bicgstab` 全部正常收敛（`nonzero_info = 0`），消耗 **`8,798.8`** 次原生局部房间 LU 回代与 **`16,627.4 ms`** 全生命周期耗时（纯界在线耗时 `3,073.2 ms`）。
   - **`SPQL` 对比 `Linear MatrixFree`**：原生局部房间 LU 回代减少 **`68.7%`**（`2,756.8` 次 + 每图 `1.5` 次全局外部回退 LU；即便按平均房间大小折算 `16.8` 等效 RHS 仍减少 `68.5%`），纯界在线查询提速 **`34.2%`**（`2,023.2` vs. `3,073.2 ms`），含 Python 层 `CSR` 策略逐边绑定验证的全生命周期耗时减少 **`577.6 ms`（`-3.47%`，`16,049.8` vs. `16,627.4 ms`，`6/8` 图更快，配对 $t$ $p_{2s} = 0.0392$，精确符号翻转 $p_{2s} = 0.0625$）**。
   - **`SPQL` 对比零构造浪费 `Uncompressed_SpectralSchur_PAC`**：原生局部房间 LU 回代减少 **`17.7%`**（`2,756.8` vs. `3,351.4`），初始数组内存减少 **`35.2%`**（`55.71` vs. `85.97 MB`，24 次查询后随二叉树缓存增长至 `100.09 MB`）；在中等门户规模 $n_\Gamma = 577.25$ 下，预批处理 `Uncompressed` 快 **`7.09%`**（等价地 `SPQL` 慢 **`+7.63%`**：`16,049.8` vs. `14,912.0 ms`，$p_{2s} = 8.46\times 10^{-4}$）。
2. **Block E3（连续代理控制，`672 / 672` 策略指纹一致，`0` 静默控制回退）**：
   - 全部 `96 × 7 = 672` 个地标策略满足 `max ||Pi_v4 - Pi_v3||_inf = 8.77e-15 <= 1e-12`，**`0` 次重跑连续轨迹**；`SPQL`（`89` 粗门户 + `7` 数值回退，`0` 静默零控制回退，`0` 已接受步弦穿墙）保持 **`100.0%` 成功率（`1.521` 代价）**，与 `Uncompressed_PAC`（`1.520`，$p_{2s} = 0.779$）未检出显著代价差异，并在 `8/8` 种子上显著优于 `Scalar_Portal`（`6.801`）与 `SVD_Resolvent`（`8.958`）。
3. **离线逐事件独立重算闭环**：独立脚本对 `p3_v4_r675_verified_results.json` 中全部 **`1,952` 条逐任务记录**（`512` E1 + `768` E2 + `672` E3）及全部 46 个冻结文件哈希完成离线重算，**差异数为 `0`**。
