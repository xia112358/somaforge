# 支撑证据：采集、编辑、训练与预测

统一版本：`newton_contact_load_slip_assessment_v1`，实现于
`somaforge_core.support_semantics`，原始求解器证据读取于
`somaforge_core.newton_support`。

## 分开判断的四件事

| 判断 | 所需证据 | 不能替代它的东西 |
| --- | --- | --- |
| 有效接触 | 当前 Newton/MJWarp 的 `CONSTRAINT` 类型、`dist < includemargin`、实际约束行分配，以及共享主表面筛选 | 裸距离、预测意图、接触力阈值 |
| 承重贡献 | 上述有效接触中的同次求解法向载荷 | 持续接触标签、部位质心速度、编辑后继承的力 |
| 承重接触的滑移运动 | 实际受力作用点相对环境的切向速度；按载荷统计 RMS，保留区域速度分布 | 单个最低运动点、虚拟压力中心、不同 witness 之间的距离 |
| 接触保持意图 | 事件显式声明的 keep 角色 | 对真实承重或固定支撑的断言 |

`load_known` 表示观测完整，`load_bearing` 表示当前有正法向载荷贡献。
完整观测中的零载荷是卸载，缺少观测是未知，两者不能混用。
滑动的接触仍可承重，不能通过取消承重标签把滑动隐藏掉。
正载荷贡献本身也不证明动力学平衡或足够的支撑能力。

脚跟／脚尖切换在足部汇总内处理，但不同环境表面不能合成一个持续接触。
转动时，实际受力点相对环境速度小、未受力点移动大，可以是正常支点转动。
多个受力点的速度不能先做向量平均，避免正反方向运动相互抵消。

没有经过标定的速度预算时，只报告载荷和运动量，不输出“无滑移通过”。
几何 pivot 预算以及原来的端点 6 cm 位移容差均不是物理滑移验收阈值。

## 各阶段的职责

1. **采集**：full recording 保留原始点对、约束分配、同次求解的逐接触载荷、
   受力点局部坐标及相对速度，并通过统一选择器输出 `observed_support_*`。
   采集是被动读取，不改已训练 policy、资产、margin、gap 或运动。
2. **聚合与切分**：持续激活不能自动新增固定支撑角色。
   保留来源 execution、事件映射和原始载荷转移。几何运动诊断不代替承重证据。
   `prepare_predictor_event_paths.py` 的 v3 证书分别保存接触事件验收、几何诊断、
   可选的实际载荷覆盖，旧 v2 证书不能冒充新判断。
   附加实际载荷观测不自动改变事件验收。单帧卸载保留为诊断；只有任务显式启用
   `--require-observed-load-coverage` 时，才要求每个已记录求解样本都有正载荷贡献。
   这个额外要求也不证明无滑移或未记录子步的完整支撑。
3. **编辑与增广**：改姿态、IK、镜像或拼接后，原载荷只能作为 source reference。
   `reference_only_support` 保留审计数据，令输出实际支撑为未知。
   裁剪后的帧需要重新绑定原生录制；拼接和再次编辑保留 keep 意图，不能继承实际支撑。
   有意生成的力参考可以用于目标设计，但其 provenance 必须是 diagnostic，
   不能是输出轨迹实际执行的受力证据。重新静态查询只能验证接触，不能补出动力学载荷。
   增广的阶段运动项改为相对原始轨迹新增的几何运动；不再用整个 keep 段的绝对
   运动量迫使原始卸载、转动和支撑转移变静止。目标版本为 v7，旧优化缓存不可直接复用。
4. **训练监督**：角色 2 表示接触保持意图。
   `support_supervision.py` 只读取绑定 motion hash、原 recording hash、权威资产、
   当前 Newton runtime 和原生帧时序的独立观测文件。
   `reference_start/target_observed_*` 是示范观测；递推生成状态不能继承这些原始载荷。
   缺失证据使用 known mask 和 NaN，不能自动把持续接触填成支撑。
5. **预测与递推**：`endpoint_contact_retention` 仅检查端点接触和材料点运动，
   分组包含部位与环境表面。预测姿态缺少实际执行证据时，支撑及路径滑移为未知。
   `endpoint_failure_reasons(..., require_observed_support=True)` 会拒绝未知或未经验证的实际支撑；
   单独通过端点 gate 不等于通过这项物理验收。
6. **可视化**：几何箭头和实际载荷／受力点速度分开显示。
   最低几何运动点不标成已确认支撑。支持独立观测文件的 hash 校验。

历史 WBT 的 `support_part_mask` 保留为 keep 意图兼容字段；新输入优先读
`contact_keep_intent_mask`。原 reward 中的 net-force／body-origin speed 仍是
历史奖励 shaping，不作为新标签或物理支撑判定。其值保持不变，避免改变原 policy 的执行；
监测项已明确命名为 body-origin speed proxy。

## 原始执行观测的物化

运行 `scripts/materialize_recorded_support.py --motion ... --original-state ... --output ...`。
工具检查原生连续帧、关节顺序、未改动的 root／关节姿态、采样率及原 recording hash，
从保存的真实求解器通道生成独立 support observations。
编辑／变速／事件重采样后的轨迹不能继承这份观测。

当前原始执行示例：
`runtime/current/motions/climb00_contact_dataset/versions/raw_execution_reference_20260930/support_observations.npz`。
932 帧载荷观测均完整。第 23–25 帧左脚无有效主表面接触且载荷为零，右脚仍承重；
第 26 帧左脚重新承重，受力点相对切向 RMS 速度约 10.17 cm/s。
第 125 帧没有有效主表面正载荷贡献，作为原始物理记录保留，不通过修改姿态消除。

观测只有每个记录间隔的最后一次物理求解。受力点速度对应约束求值几何，
保存位姿对应积分后状态。它们不能冒充严格同帧，也不能外推为未记录子步的全程无滑移证明。
旧数据集／训练 manifest 未自动切换；本次没有重训。

## 正式入口与退役边界

- 实际求解样本分析：`scripts/analyze_recorded_support.py`。
- 原始执行观测物化：`scripts/materialize_recorded_support.py`。
- 几何接触区域运动：`scripts/analyze_contact_region_motion.py`，仅作几何诊断。
- 事件切分与证书：`scripts/prepare_predictor_event_paths.py`，接触事件、几何诊断、
  实际载荷分别保存；旧证书必须显式重新物化。

旧几何支撑聚合优化器、专用聚合材料点模块及重复的逐帧审计入口已移到系统回收站。
不能再通过它们改写原始执行或把逐帧接触一致性当成支撑判断。
仓库审计拒绝这些入口和旧模块导入被重新引入。

WBT 历史奖励项及其配置名称保留用于原 checkpoint 的执行兼容，数值计算不变；
它们不能产生新支撑真值。新采集、编辑、切分及观测读取共用上述证据契约。
