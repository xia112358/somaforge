# Generator

Predictor 和 Infiller 的独立实现，以及数据、训练、生成 rollout 工具。
WBT policy、环境、仿真训练与执行仍位于 `src/holosoma/`。

```python
from generator.full1000_position_predictor import Full1000PositionPredictor
from generator.neural_infiller import G1ConstrainedKeypointInfiller, G1ContactAwareQInfiller
from generator.unified_interaction import InteractionQInfiller
```

从仓库根目录 `source scripts/source_somaforge.sh` 后使用新入口，例如
`python -m generator.train_q_infiller --help`。

依赖方向为 `generator → contact_solver → somaforge_core`；共享 FK、预测结果结构、
高度图坐标约定在 core。网络中的几何损失调用 contact_solver。
旧 `climb00_pipeline` 模块是同一实现模块的兼容别名，旧导入和模块 CLI 保留；
本次搬迁没有改变网络参数名或 forward 算法，也不赋予旧错误机器人资产产物有效性。
回归测试按实现归入 `generator/tests`、`contact_solver/tests` 和
`somaforge_core/tests`；`test_package_boundaries.py` 单独验证历史兼容入口。

普通 predictor batch 的可选约束训练入口为
`python -m generator.train_full1000_position --constraint-training ...`。
使用同一 predictor、数据划分和 Newton 查询，每个 batch 一次受约束 AdamW 更新。
默认分支不变；当前先支持固定接触意图的 reference batch，未接入递推 rollout。
使用说明和边界见 [minibatch-training](../contact_solver/docs/minibatch-training.md)。

大批量持续池（`train_full1000_position --parallel-rollouts --gpu-pipeline`）采用验收后提交：
A → B′ 通过现有任务、几何、支持及已启用的进度验证，才将 B′ 放回输入并推进目标。
失败输出仍参与本轮 loss/backprop，但下一轮保留本次预测前的完整 A 和目标 B；
即使 A 来自之前成功的递推，窗口内也原样保留。
严重穿透、无有效接触等失败同样回退，不把失败 B′ 用于 B′ → B 训练。

年龄与前进历史只累计成功提交；连续失败累计 retries/rollbacks。
每槽每次预测均累计 attempts，成功、失败都计数，跨统计轮次保留。
达到 `parallel_episode_limit`（默认64次预测更新）后从训练集重新采样；
完整观测、目标索引一起替换，清空 attempts、重试、成功深度及前进历史，恢复示范监督。
第64次输出仍参与本轮反传，下次输入才切换；成功不会延长窗口。
日志中的 *_rejections 表示候选失败；periodic_resamples 单独统计周期刷新，
resets/timeout_resets 包含该刷新，rollbacks 只统计未到刷新边界的失败保留。
状态 schema 为 bounded_attempt_rollout_v5，保存 attempts、resample_interval 和 allow_post_demo。
完成最后示范目标后仍关闭示范监督并继续自主递推；后继不得进入验证集。
本轮实验使用 `--no-parallel-allow-post-demo`：完成最后示范目标后立即重新采样，
不产生示范外输入；最后目标未通过验收时仍保留A，直至成功或达到64次刷新。
terminal_resets 与 periodic_resamples 分开计数，同时到期只记一次末尾重置。
`parallel_retry_limit` 仍为兼容参数，不单独截断；自主状态同样受64次窗口限制。
接触真值、loss、验收阈值未改；非并行短 rollout 与独立 eval 保留原有终止规则。
此修改不解除 `--constraint-training` 暂只支持 reference batch 的限制。

预测支持保持损失：`predicted_support_weight` 默认1，设为0可关闭。
使用模型原始 `prediction.role == 2`（停止梯度），不使用教师替换后的角色。
只为输入姿态具有实际Newton激活、已分配、主水平面接触的末端建立锚点。
对每个声明保持的末端，跟踪同一材料点的FK位移，末端内取最小值允许接触区域转换；
首端点见证始终保留，末端点见证可补充转动支点，因此输出丢失接触不会关闭损失。
每个启用末端采用 `relu((displacement - support_tolerance_m)/support_tolerance_m)^2`，
末端间取均值。默认容差仍为6 cm，不改变实际接触判定或硬验收。
无初始接触的保持声明计入 `predicted_support_without_initial_contact`，不虚构锚点。
梯度经过预测姿态的FK，不经过角色选择或输入锚点；当前共享编码器仍会接收执行梯度。
日志保存原始/加权支持损失、启用末端数、缺失初始接触数及最大位移。


递推支持保持硬验证（endpoint_region_motion_v2）：按末端 part 汇总实际 Newton 地面/顶面接触，允许足跟、前掌、形状和 witness 切换。通过 link FK 跟踪首尾实际接触区域中的同一材料点，取末端内最小位移，至少一个保留接触的末端须不超过 6 cm。容差来自训练集 P90=5.512 cm 向上取整，覆盖 1157/1258 个持续接触区间。失败时独立 eval 终止；持续训练池拒绝该候选并保留输入，不增加 loss 项。仅验证端点位移，不证明路径全程持续接触、无滑移或承重。统计见 `tmp/support_tolerance_training_20260926/endpoint_statistics.json`。
