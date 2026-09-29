# 镜像来源说明

本次基准测试使用的隔离容器，其镜像与生产环境正在跑的镜像**完全同一个digest**（不是同一个tag
恰好指向同一版本——是`docker inspect`直接核实过的、字节级相同的镜像ID）：

```
image digest: sha256:4b14c13ef5eadda7f0a9ce34676bfe652db675e885175040dd4b21336e8a65e9
本地tag:      mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt
```

由于这个仓库没有该私有镜像仓库的推送/拉取权限（`docker pull ...@sha256:...`会被拒绝：
"pull access denied"），无法直接提供可下载的镜像归档。复现者需要：

1. 从`asi-alliance/OmegaClaw-Core`（pinned commit
   `642c53676cf795cb7a0030823b36018c029b1416`，见`src_snapshot/`）+ `trueagi-io/PeTTa`
   自行构建等价镜像，或
2. 如果你就是这个项目内部的人、本身有权限访问`mindchildren/omegaclaw-core`镜像仓库，直接用
   上面的tag/digest。

`src_snapshot/benchmark_relevant_omega_files/`里的5个文件（`grounded_reason.py/.metta`、
`grounded_proposition.py`、`observation_memory.py`、`lib_nal.metta`）的SHA256已经和这次真实
调用的容器逐字节核对过——只要你的构建产出这5个文件的哈希一致，就能保证复现出同一套真实推理逻辑。

## 隔离容器启动命令（Level 2/3脚本内部实际调用的）

```bash
docker run -d --name omega_isolated_benchmark_20260928 \
  --network none \
  -v <你自己的scratch目录>:/PeTTa/repos/OmegaClaw-Core/memory/chroma_db \
  --entrypoint sleep \
  mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt \
  infinity
```

关键点：`--network none`（没有网络，不可能触达任何现场系统）；只挂载一个空的scratch目录
（从不挂载生产的`omegaclaw-memory/`）；`--entrypoint sleep infinity`（不启动完整agent
loop/机器人TCP通道/nginx，只用来被`docker exec`调用一次性Python/swipl脚本）。
