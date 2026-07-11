新添加/删除/改动代码前永远先计划好问我，除非要求连续诊断。

除非用户明确要求停止/重启训练，禁止擅自停止正在运行的训练进程；需要释放 GPU 做 eval/visualization 时必须先说明原因并等待用户确认。

Isaac Sim / CUDA 初始化失败通常是 sandbox 限制，到本机环境可以跑。

SomaForge 的 G1 机器人唯一权威资产是
`src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf`。
禁止绕过 `somaforge_core.robot_assets` 使用其他 G1 URDF/XML；缺少
`robot_asset_json` 的 motion、GMVQ 数据和 checkpoint 均视为旧错误资产产物。

读文件、查看配置、搜索文本、查看数据/日志/CSV/YAML/JSON、复述文件内容、汇总简单指标等基本任务，如果不需要明显推理，优先调用使用 spark 模型的 subagent 来完成。

像更新 AGENTS.md、补一条简单说明、调整少量文案这类低风险、低推理的简单修改任务，也优先调用使用 spark 模型的 subagent 来完成；仍需遵守“改代码/文件前先计划并问我”的规则。

项目相关临时脚本、图、CSV、分析产物统一放到项目根目录 `tmp/`，不要放系统 `/tmp`。

CLI 标准：

- train/eval/replay/run_sim 主入口统一先由 IsaacLab AppLauncher 解析官方参数，再由 tyro 解析项目配置。
- 可视化只使用一个开关：`--visualizer kit`。
- 不写 `--visualizer` 时默认 headless。
- `--headless` 优先级最高，强制无窗口。
- `training.headless=False` 不再作为打开 Kit 窗口的 CLI 入口，只接受最终 AppLauncher/CLI 状态同步。
- `--enable_cameras`、`--device`、`--experience`、`--kit_args` 等官方 AppLauncher 参数归 AppLauncher 解析，不让 tyro 当成项目配置吞掉。
