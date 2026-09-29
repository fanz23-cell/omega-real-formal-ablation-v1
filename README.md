# Omega Real-Formal Ablation v1

**这次测的是什么？**

- **B0** — 强结构化、非形式化基线（看到原始证据，没有任何建议块）
- **B1** — B0 + 确定性结构化冲突控制（一个中性的"ADVISORY A"块，明确说明"存在无法调和的冲突"，
  但数值字段被替换成`WITHHELD_CONTROL`占位符，不给真实数字）
- **C**  — B1 + **真实的Omega MeTTa/NAL修订引擎**算出的真实数值（frequency/confidence）

**主对比：C vs B1**

这次实验存在的唯一理由：把"结构化冲突识别本身带来的价值"（B1相对B0的提升）和"真实NAL数学计算
本身在此基础上还能不能带来额外价值"（C相对B1的提升）彻底分开。旧一轮benchmark的"C"其实是一段
手写的Python公式，只是复现了NAL公式的形状，从未真正调用过PeTTa/MeTTa解释器——这次是第一次让
真实的Omega推理引擎参与进来。

## 快速开始

```bash
# Level 1：无需API key，纯校验已有结果
./scripts/verify_package.sh
./scripts/reproduce_analysis.sh

# Level 2：无需付费LLM调用，验证真实MeTTa组件本身没有问题
./scripts/reproduce_component_witness.sh

# Level 3：需要你自己的Anthropic API key，完整重新付费跑一遍
./scripts/reproduce_full_benchmark.sh /path/to/your/key.txt
```

## 目录结构

```
docs/            -- 144-158号文档，完整方法论、审计、验证记录
src_snapshot/     -- 被测的4个真实Omega插件文件快照+哈希（不含完整生产镜像）
harness/          -- 可运行的完整测试台代码
config/           -- benchmark/model/retry/scoring配置
seeds/            -- 校准种子池 vs 确认性种子池（严格分离，从不混用）
frozen_prompts/   -- 每个几何条件抽样的真实prompt原文
data/             -- 原始结果（合成世界、真实provider输出、真实MeTTa痕迹、打分行）
results/          -- 最终统计结果（JSON+CSV）
figures/          -- 图表
docker/           -- 隔离运行时的复现说明
scripts/          -- 三档复现脚本
```

## 生产隔离保证

全程未修改任何生产代码、生产容器、生产Chroma数据库或生产WorldState。真实推理调用发生在一个
从**完全相同镜像digest**启动的、`--network none`、只挂载临时scratch目录的隔离容器里，doc147
逐项验证了这一点（网络模式、挂载点、进程独立性）。

## 已知局限（如实披露，不回避）

- 本轮只测试了`revision`这一个算子（生产Stage-10金丝雀本身也只开放这一个算子）。
- MeTTa求值的真实推理链条只验证了两个具体案例的手工反推数学一致性，不是对任意几何条件的
  完整解析证明——但567次真实确认性调用全部走的是同一条真实代码路径。
- 分几何条件（per-geometry）的细分统计，每个cell只有7个重复样本，功效不足以独立判定小效应
  （已在150号文档里明确说明，不掩盖）。

## 补充：本地小模型试验（doc159）

主确认性结果全程只用了`claude-sonnet-4-5-20250929`一个模型。为了检验"C≈B1这个零结果是不是
被强模型自身能力掩盖了"，另外用本地跑的`qwen3.5:9b`（Q4量化，CPU-only）重测了一档（scale=10,
63案例）。**结果方向完全反过来**：B0=77.8% > B1=69.8% > C=65.1%（C比B0显著更差，
95% CI[-23.81,-3.17]pp）。根因非常具体：这个小模型把advisory文本里"...BETWEEN_OPPOSING_
GROUNDED_CLAIMS"这句话的"opposing"直接误读成"势均力敌"，从而覆盖了它本来能从原始证据数字
正确算出的`relative_historical_support`判断——9个判负案例里9个（100%）都是这一个字段、
这一个机制。不是"小模型用不了数字"，而是"小模型的文字模式匹配会盖过它自己的数字读取"。
范围披露：只测了1个模型、1种量化、scale=10这一档（scale=1000纯CPU单次调用要12-14分钟，
189次要40+小时，不现实）。详见`docs/159_LOCAL_MODEL_PILOT_REPORT.md`。
