# 环境记录

- OS: Linux（宿主机内核 7.0.0-31-generic）
- Docker: 用于隔离容器（`omega_isolated_benchmark_20260928`，见docker/IMAGE_PROVENANCE.md）
- Python: 3.11（宿主机harness运行环境），容器内也是Python 3.11
- 不需要ROS——这次基准测试的真实推理调用完全绕开ROS2/DDS，直接在隔离容器内用`docker exec`
  跑一次性`python3`/`swipl`脚本
- PeTTa/MeTTa运行时：SWI-Prolog（`swipl`），非典型的MeTTa-in-Python(hyperon)实现；具体调用
  方式见`docs/149_real_metta_end_to_end_witness.md`
- Omega源码commit：`642c53676cf795cb7a0030823b36018c029b1416`（`asi-alliance/OmegaClaw-Core`，
  见docker/IMAGE_PROVENANCE.md）
- 容器镜像digest：`sha256:4b14c13ef5eadda7f0a9ce34676bfe652db675e885175040dd4b21336e8a65e9`
- Provider/模型配置：见`config/model.yaml`
