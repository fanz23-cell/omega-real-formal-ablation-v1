# 复现说明

## 三个复现级别

### Level 1 — 验证已有结果（不需要API key）

```bash
./scripts/verify_package.sh       # 核对MANIFEST.sha256，证明包内容没被篡改
./scripts/reproduce_analysis.sh   # 从原始行数据重新计算全部分数/CI/符号检验/结论
```

预期：逐字节或数值完全一致地重新得到`results/summary.json`里的每一个数字。

### Level 2 — 验证真实组件本身（不需要付费LLM调用，需要Docker）

```bash
./scripts/reproduce_component_witness.sh
```

会重新跑一遍9个真实拒绝控制测试（negative controls）+ 一次真实MeTTa求值witness。这证明整套
"真实Omega推理链条"本身是可运行、可信的，不是靠伪造的数学公式撑起来的。

### Level 3 — 完整重新付费跑一遍（需要你自己的Anthropic API key）

```bash
./scripts/reproduce_full_benchmark.sh /path/to/your/key.txt calibration
./scripts/reproduce_full_benchmark.sh /path/to/your/key.txt confirmatory
```

预计花费：校准阶段约27次调用，确认性阶段约567次调用，总计约1.5-2.5美元（与本次实际花费同一
数量级）。**从不会把key写进任何代码或日志。**

## 预期运行时间

- Level 1：几秒钟
- Level 2：约1-2分钟（198个案例的负控制+witness自检）
- Level 3：校准阶段约1分钟，确认性阶段约10-15分钟（567次真实API调用+对应的567次真实Omega
  推理调用）

## 已知限制

见`docs/155_failure_analysis.md`与`docs/156_real_omega_formal_math_verdict.md`（结果生成后
补全）"WHAT THIS DOES NOT PROVE"章节。
