# R7A（`green_kriging_v14`）审计独立决断与收口报告：SISC 投稿封版、SPQL 理论收窄、跨版本 672 策略补证与 Bauer 单纯形松弛诊断

> 主体记录 `5be3f35` 时的修订，第 2.2 节的解释已按后续复核更新。完整复现结果见[项目复核](../GREEN_PLANNING_REVIEW.md)。

> **基线提交**：`7a09d59f1876c7e68696f856c2a069b2ccd20dd7`（`feat/green-kriging-control-1a`）  
> **审计输入**：[GPT_diagnosis_v14.md](../markdown/green_kriging_v14/GPT_diagnosis_v14.md)、[R7A_FULL_AUDIT_ZH.md](../markdown/green_kriging_v14/R7A_FULL_AUDIT_ZH.md)、[R7A_PATCH_PLAN.md](../markdown/green_kriging_v14/R7A_PATCH_PLAN.md) 及 `checks/` 全部复核脚本  
> **历史归档 100% 字节冻结（共 47 个历史 `.py`/`.json` 文件零改动）**：
> - Phase-I `green_response/*.py`（`271ac8df...`）、Phase-II `quotient_phase2/*.py`（`e6ea565b...`）及全部 13 个 Phase-II JSON（含 `m233_clean_isolation_replication.json` `73101638...`）
> - Phase-III `v1`（`0e2c76ea...`）、`v2`（`6167bd5f...`）、`v3`（`0ffd1d3a...`）及 **`v4` `p3_v4_r675_verified_results.json`（`798a9e2b300a1d3898b55a91f00b771f4d3487c9b5322abfbddb61417cbd6580`）**
> - **本轮新增非破坏性旁路诊断台账** [p3_v4_r7a_sidecar_diagnostics.json](../learned_portal_phase3/p3_v4_r7a_sidecar_diagnostics.json)：`6bbedca9750fab0de0beeb63b110da26a4ad19f19936faf39501dab5e79d2b09`（`phase3_package_py_sha256: 45b76718...`）

---

## 1. 对 GPT6 `green_kriging_v14 / R7A` 的独立战略裁定

GPT6 在 `v14 / R7A` 中独立确认了上一轮 `7a09d59` 的全部核心工程与数值修复：72 个 100 位 `mpmath` 小模型（`216/216` 零越界）及 400 位次正规数/`1e-310` 策略复核全部通过、官方 `20/20` 契约门零警告通过、SISC `126/126` 统计与 SPQL `v4` `9,394/9,394` 项事件归约全部零差异，并明确宣布 **SISC 线可转入正式投稿准备**。在此基础上，我们的独立取舍与超额执行如下：

1. **SISC 线（`quotient_phase2/`）：采纳唯一一处 1 行文稿收窄，即刻封版转投稿**：
   - 将 [MANUSCRIPT_CORE_DRAFT.md](MANUSCRIPT_CORE_DRAFT.md) 第 69 行的泛化主语改为 `The global SVD/POD port constructions tested in Exp 5 generate...`，零代码改动、零重跑实验，SISC 证据链彻底封版。
2. **SPQL 线（`learned_portal_phase3/`）：100% 采纳 `R7A-01..07` 理论与溯源收口（不重跑 SISC/E1/E2/E3 主基准，保持 `p3_v4` JSON 字节冻结）**：
   - **`R7A-01`（`Proposition 5` 精确边界修正）**：承认并接纳两态归一化单纯形反例——将 `Proposition 5` 严格改写为**逐坐标（次随机核）保守代理上界 $\overline{J}_{\underline{M}}(\pi) \ge \sup_{(P,q)\in\mathcal{C}_n} J^\pi_{P,q}$ 及其在该代理族内的变分最优性**，删去“归一化置信集精确最坏值”“任何 CE 后验证书不可能更紧”“任何安全方法不可避免的固有代价”等过度推断，并将两个两态反例直接固化进第 21 项契约门 `P3-C21`。
   - **`R7A-02`（`Theorem 4` 充分上界 vs. 必要性区分）**：删去由充分界中的 $z_{\min}^{-2}$ 推断“亚单位宽度普遍需要 $n \gg 10^{12}$ 样本”的表述，将 200 步（$q=14.3, z_{\min}^{-2}=2.64\times 10^{12}$）即达到认证宽度 `0.1539 < 0.18` 的合同允许特例写入正文与 `P3-C21`。
   - **`R7A-03`（真正的跨提交 `672` 策略重建与 fail-closed 比较器）**：修复 `run_phase3_r675_targeted_audit.py` 使缺旧策略时返回 `comparison_unavailable_without_prior_csr` 而非默认 `0.0`；并在 `run_phase3_r7a_sidecar_audit.py` 中通过 `git archive 67532c9` 独立进程重建全部 `672` 个新旧 `CSR` 策略（`max_abs_entry_diff = 8.77e-15`、`max_matrix_infinity_norm_diff = 1.75e-14 <= 1e-12`、`672/672` 回退一致、`0/672` 原始字节哈希相同——精确表述为**声明容差内数值等价，零次重跑连续轨迹**）。
   - **`R7A-04..07`（计时阶段命名、`320` 条 CE `pred_val` 旁路账本、CE 全域 RHS 拆列、图件与引文修正）**：补充显式 `interface_candidate_stage_ms` 并修复 `SPQL` 在 `materialize_policy=False` 时的完整认证纯界计时；在旁路 JSON 完整导出 `128 + 192 = 320` 条 `PlugIn_CE` 的 `pred_val`、`deployed_policy_J`、差值与 `global_lu_rhs = 257.75`（`native_room_lu_rhs = 0`）；更新图 1A/1B 版本与事件区分标签及图 2A `258 global RHS`；将后验评估器标明为 `high_precision_numerical_diagnostic`（非 Tier-3）；补充 Tier-3 的 IEEE-754 RN-even / 禁 FTZ / 忠实 `libm` 假设；将 Saxe (2017) 第三作者修正为 **Benjamin Rosman**；严格拆分 `1,952 = 960 离散 PAC + 320 CE 对照 + 672 Tier-4 连续经验事件`。
3. **超额提前完成的科研诊断（直接落地 GPT6 第 10 节 `Decision C Step 1`！）**：
   - 利用凸函数 $-\sum_j \pi_{ij}\log p_{ij}$ 在概率单纯形切片上的 **Bauer 极值点定理**，我们在 `baselines_and_contracts.py` 推导出精确闭式单纯形最坏步代价公式 $c^{\pi,\mathrm{simplex}}_i = \overline{c}^\pi_i - \lambda \min_k \pi_{ik}\log(1 + \rho_i/\underline{p}_{ik})$，并在不改动任何已有实验的前提下，直接在固定 `E1 240k` 与 `E2 460k` 数据与策略上完成了“逐坐标松弛 vs. 行随机单纯形约束”的定量拆解！

---

## 2. 核心新增诊断结果（`P3-C21` 与 `Decision C Step 1` 实测发现）

### 2.1 `Gate P3-C21` 与跨提交溯源核验（`21 / 21` 门 `13.15s` 全过）
- **两态 `Proposition 5` 反例（`P3-C21a`）**：$\pi = (0.5, 0.5)$ 时精确单纯形最坏值 `3.021651 < Full-PAC 代理最优 3.265103 < 逐坐标代理 5.218876`；可实现经验模型 $\hat{P}_s = (0.2e, 1-0.2e)$ 诱导的 $\hat{\pi}_{\mathrm{CE}} = (0.2, 0.8)$ 满足 **`2.953422 < 3.265103 < 3.502728`**。
- **两态 `Theorem 4` 充分性区分例（`P3-C21b`）**：$q = 14.3, \lambda = 1$（$z_{\min}^{-2} = 2.635\times 10^{12}$），仅 `200` 步被动观测即通过全部 Tier-3 上下界与 `CSR` 策略绑定核验，认证宽度 **`0.15394 < 0.18`**。
- **`320` 条 `PlugIn_CE` 原始预测值独立重判（`R7A-05`）**：由保存的 `pred_val < deployed_policy_J - 1e-9` 直接离线重算出 E1 `121/128`（均值预测 `14.35` vs. 实际 `16.46`）与 E2 `192/192`（均值预测 `19.57` vs. 实际 `37.01`），与冻结 `v4` 100% 吻合。

### 2.2 回答 `Decision C Step 1`：为什么仅靠行和为 1 不能收紧多房间 PAC 证书？

| 固定数据集（任务数，零新采样） | `PlugIn_CE` 逐坐标代理 $\overline{J}_{\underline{M}}$ | `PlugIn_CE` 未知支撑 ($d_{\max}=8$) 单纯形最坏值 | `PlugIn_CE` 已知观测支撑 Bauer 单纯形最坏值 | `Full_PAC` 逐坐标代理 $U_{\mathrm{PAC,full}}$ | `Full_PAC` 已知观测支撑 Bauer 单纯形最坏值 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **E1 2D 旋转九宫格 (`128`, 240k)** | `159.3573` | `159.3573`（精确相等） | `136.5280`（`-14.3%`） | `67.7262` | **`67.4841`（仅收紧 `-0.36%`）** |
| **E2 3D 弯曲洞穴 (`192`, 460k)** | `973.2995` | `973.2995`（精确相等） | `856.8749`（`-12.0%`） | `218.4366` | **`218.4355`（仅收紧 `-0.0005%`）** |

**机理洞察（直接指导下一阶段研究方向）**：
1. 在未知支撑 $d_{\max}=8$ 下，2D（度 $\le 5$）与 3D（度 $\le 7$）每个状态均留有零策略权重的外部空槽吸收 $\rho_i$，故两种上界在精确算术下相等；浮点比较以数值容差核对。
2. **即便假定图拓扑已知（禁止向未观测边漏出质量）**，在多邻接状态上，朝向目标的策略对“背离目标的后退邻居 $k_{\min}$”赋予极小的概率权重 $\pi_{i k_{\min}} \ll 1$；此时单纯形对手只需把全部剩余不确定质量 $\rho_i$ 堆到 $k_{\min}$ 上，Bauer 修正项 $\lambda \pi_{i k_{\min}}\log(1 + \rho_i/\underline{p}_{i k_{\min}})$ 几乎为零（3D 仅 `0.0011`）！
3. 在固定数据和已部署的 Full-PAC 策略上，单加行和约束带来的上界收紧很小。观测支撑作为已知支撑是额外假设。`+26.28` 是更换规划策略时测得的部署代价差。下一轮可比较整行多项分布置信集或 KL 球对上界、部署代价、计算成本各自的影响；这张表尚未检验它们的效果。
