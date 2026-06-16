
## KV Cache 卸载算法发展现状（2025–2026）

2025至2026年，KV Cache 卸载从早期的"简单分层搬运"演进为**计算-通信协同设计、预测性调度、与压缩/驱逐深度融合**的精细化系统。以下是当前的核心进展与重点工作。


### 一、技术路线分类

根据2026年3月的==一篇系统综述，当前KV Cache优化可分为五大类：缓存驱逐、缓存压缩、混合内存（卸载）、新型注意力机制、以及组合方法==。其中，**卸载类方法（Hybrid Memory）** 的核心优势在于无损精度，且与模型结构无关，特别适合高并发、多租户的数据中心部署。

[](https://arxiv.org/html/2603.20397v1)


### 二、重点工作详解

#### 1. ScoutAttention：GPU-CPU协同的层前预计算

**ScoutAttention**（2026年3月）提出了一种全新的协同注意力计算范式。传统卸载方法要么频繁进行GPU-CPU数据传输，要么让CPU承担过重计算导致GPU空等。ScoutAttention 引入**层前CPU预计算（layer-ahead CPU pre-computation）** 机制：CPU提前一层启动注意力计算，配合异步周期性召回，将CPU负载降至最低。实验显示，在精度损失不超过2.4%的前提下，相比现有卸载方法实现 **2.1× 加速**。
[](https://arxiv.org/abs/2603.27138)

#### 2. ShadowKV：Key压缩 + Value卸载的混合架构

**ShadowKV** 采用"分而治之"策略：利用 pre-RoPE Key 的强低秩结构，通过SVD压缩后保留在GPU；Value 向量不具备低秩性，则卸载至CPU内存。解码阶段，系统将 post-RoPE Key 分块并计算 landmark 向量，仅从高相似度块对应的CPU内存中检索 Value，同时GPU端解压 Key。这种**选择性检索**避免了全量搬运。
[](https://arxiv.org/html/2603.20397v1)

#### 3. INF2：近存储计算（Computational Storage）

INF2 利用带FPGA加速器的**计算存储设备（CSD）**，将KV Cache直接存放在SSD上，通过私有PCIe Switch将数据加载到存储端加速器进行多头注意力计算，GPU同步处理MLP部分。新产生的KV条目先暂存RAM再批量写入SSD。该方法将注意力计算**迁移到数据所在位置**，从根本上减少PCIe流量。
[](https://arxiv.org/html/2603.20397v1)

#### 4. HeadInfer & InstInfer：极端长上下文卸载

- **HeadInfer**（2025）按注意力头粒度卸载KV Cache，在百万token上下文下实现约 **92% 的KV内存削减**。
    
- **InstInfer** 进一步将KV Cache推入存储类设备（Storage-class Memory），探索比DRAM更低成本的存储层级。    
    [](https://arxiv.org/html/2604.21026v1)
    

#### 5. SuperInfer：面向Grace Hopper架构的调度优化

针对NVIDIA Grace Hopper（GH200）等统一内存架构，**SuperInfer** 配置了400GB Grace DRAM作为KV卸载空间，并设计了 **RotaSched** 调度器，在TTFT（首token时间）和TBT（token间时间）的SLO约束下，实现高吞吐的长上下文服务。
[](https://arxiv.org/html/2601.20309v2)

#### 6. Continuum：多轮Agent场景的TTL机制

在多轮Agent工作负载中，工具调用导致的停顿会使传统"请求结束即驱逐"策略失效。**Continuum** 引入**Time-to-Live（TTL）**机制：对生成工具调用的请求，根据重载成本和排队延迟计算TTL，在GPU中固定KV Cache；TTL到期后自动驱逐。在SWE-Bench、BFCL等真实Agent任务上，平均作业完成时间提升 **8× 以上**。
[](https://arxiv.org/abs/2511.02230)

#### 7. KVP：强化学习驱动的驱逐策略

**KVP（Learning to Evict from Key-Value Cache）** 将驱逐问题重新建模为**排序问题**，使用强化学习训练轻量级的逐头（per-head）策略，预测token的未来效用。其奖励信号设计为"跨所有缓存预算的驱逐误差"，确保策略在不同内存限制下均表现稳健。这与传统启发式方法（如H2O、StreamingLLM）有本质区别。
[](https://arxiv.org/html/2602.10238v1)


### 三、2026年的关键挑战与反思

#### 上下文密集型任务的失效问题

2026年4月的一项研究指出，现有KV卸载方法在**上下文密集型任务**（如从长文本中提取结构化知识的Text2JSON）上表现显著退化。原因在于：

1. **低秩Key投影**破坏了需要精确检索的细粒度信息；    
2. **Landmark向量**在需要大范围信息 lookup 时不可靠。
    

该研究提出了一种更简单的替代策略，在Llama 3和Qwen 3上显著改善了此类任务的精度。这提示社区：卸载算法不能仅在通用基准上验证，必须覆盖"需要提取大量信息"的极端场景。
[](https://arxiv.org/abs/2604.08426)

#### 推理感知的分层内存

另一项工作（2026年5月）提出"并非所有推理步骤都需要HBM"：在CoT（Chain-of-Thought）推理中，不同推理token的重要性差异巨大。通过**推理感知评分**驱动跨层内存放置（HBM→DRAM→SSD），可将关键推理token保留在快速内存，次要token下沉至慢速层级。这是首个将推理语义与分层卸载结合的工作。
[](https://arxiv.org/html/2605.09490v1)

### 四、工程实践与开源生态


| 系统/框架            | 卸载特性                                              | 状态  |
| :--------------- | :------------------------------------------------ | :-- |
| **vLLM**         | PagedAttention块级别CPU卸载、磁盘卸载（实验性）；支持Prefix Caching | 生产级 |
| **SGLang**       | RadixAttention前缀复用；多级缓存层级                         | 生产级 |
| **LMCache**      | 多引擎持久KV存储，支持GPU→CPU→SSD分层卸载                       | 企业级 |
| **TensorRT-LLM** | 集成KV Cache压缩与卸载                                   | 生产级 |
| **Harvest**      | 基于P2P的GPU间KV Cache共享，扩展vLLM的OffloadingHandler     | 研究级 |

当前主流推理栈已形成**三级缓存层次**：GPU HBM（热数据）→ CPU DRAM（温数据）→ NVMe SSD（冷数据），配合Prefix Caching实现3–10×的会话式工作负载吞吐提升。
[](https://callsphere.ai/blog/kv-cache-offloading-cpu-gpu-nvme-tradeoffs-2026)

### 五、总结与趋势

2026年KV Cache卸载算法的核心趋势可概括为：

1. **从"搬运数据"到"搬运计算"**：INF2、ScoutAttention等将计算推向数据所在层级，而非反向搬运KV。    
2. **从统一驱逐到语义感知**：KVP的RL驱动驱逐、Continuum的TTL、推理感知的分层放置，都体现了对KV条目"重要性"的精细化建模。    
3. **从单层优化到系统协同**：卸载不再孤立存在，而是与MoE专家卸载（如DALI）、Prefix Caching、PD分离（Prefill-Decode Disaggregation）深度耦合。    
4. **从通用场景到垂直场景**：Agent多轮对话、长上下文推理、边缘设备等特定场景催生了专门的卸载策略。
    

简言之，==KV Cache卸载已进入**"精准预测 + 异构协同 + 场景定制"**的新阶段==。

