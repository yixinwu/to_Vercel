
广泛的 **LLM Offloading** 技术体系，核心思想是将 MoE 模型中那些当前未被激活的专家权重，按照访问频率和延迟容忍度，分层存放在 GPU VRAM → CPU DDR RAM → NVMe SSD 的存储层级中。

## 技术原理

MoE 模型（如 DeepSeek V3、Mixtral、Qwen3-235B）的特点是：推理时每个 token 只激活少数几个专家（如 671B 参数的 DeepSeek R1 每次只激活约 37B），其余专家处于"休眠"状态。因此：

- **热专家**（高频激活）→ 常驻 GPU VRAM 或 CPU DDR RAM
- **温专家**（中频激活）→ 存放在 CPU DDR RAM，按需加载到 GPU
- **冷专家**（低频激活）→ 存放在 NVMe SSD，需要时再读取

瓶颈在于 **I/O 带宽**：DDR RAM → GPU 约几十 GB/s，NVMe SSD → CPU 约 7–14 GB/s（PCIe 5.0），延迟差距巨大。


## 全球主要进展（2024–2026）

|项目/论文|机构|核心贡献|
|---|---|---|
|**Fiddler**（ICLR 2025）|华盛顿大学|CPU-GPU 协同调度，将专家保留在 CPU RAM，相比朴素方案加速 8–10×[11](https://arxiv.org/html/2402.07033v2)[13](https://openreview.net/forum?id=N5fVv6PZGz)|
|**MoE-Lightning**（ASPLOS 2025）|—|GPU 内存受限场景下吞吐量提升 10.3×，专注 SSD/RAM 分级卸载[15](https://pschafhalter.com/papers/2025-asplos-moe-lightning.pdf)|
|**fMoE**（2025.02）|—|细粒度专家卸载，解决粗粒度方案的碎片化问题[18](https://arxiv.org/html/2502.05370v1)|
|**HOBBIT**（2024.11）|—|混合精度专家卸载，冷专家用更低 bit 量化后存 SSD[23](https://arxiv.org/html/2411.01433v2)|
|**SSD Offloading Harmful?**（2025.08）|—|首次系统分析 SSD 卸载的**能耗代价**，指出频繁 SSD 读取可能带来严重能效问题[1](https://arxiv.org/html/2508.06978v1)|

### 工程落地方向

- **llama.cpp**：目前支持 CPU DDR RAM 卸载（`--n-gpu-layers` 控制），SSD 直接卸载尚不完善，社区正在讨论完整的 NVMe offload 支持[6](https://github.com/ggml-org/llama.cpp/discussions/19163)[24](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide)。
- **vLLM**：2025 年底开始讨论 Expert Offloading 支持，但默认仍要求所有专家在初始化时完整加载[8](https://discuss.vllm.ai/t/enable-expert-offloading/1884)。
- **LMCache**（2026.04）：新架构将 MoE 推理性能提升 10×，支持跨 HBM/DDR/NVMe 的层级调度[9](https://blog.lmcache.ai/en/2026/04/03/lmcaches-new-architecture-boosts-moe-inference-performance-by-10x/)。
- **NVIDIA NCX 方案**（2026.03）：官方文档明确提出 KV Cache 和专家权重跨 HBM → DDR → NVMe 的分层部署方案[4](https://docs.nvidia.com/ncx/ncp-inference-ra/latest/example-workload-large-moe-llm-inference.html)。

## 当前核心挑战

1. **SSD 能耗问题**：频繁随机读取 NVMe 的能耗可能超过节省的 GPU 成本，2025 年的研究已对此提出警告[1](https://arxiv.org/html/2508.06978v1)。
2. **预测精度**：提前预测"下一个 token 会激活哪些专家"是减少 I/O 等待的关键，目前准确率仍有限。
3. **带宽墙**：即使 PCIe 5.0 NVMe 理论带宽达 14 GB/s，在大批量推理时仍是严重瓶颈。
4. **软件生态**：主流框架（vLLM、llama.cpp）对 SSD 层级的原生支持仍不成熟。

总体来看，**DDR RAM 卸载已较为成熟**，**SSD 卸载仍处于研究与工程探索阶段**，能否实用化取决于未来高速 NVMe（如 PCIe 6.0）及更智能的专家预取算法的发展。

---

2026年，MoE（Mixture of Experts）专家卸载算法在本地部署领域取得了显著进展，呈现出**从粗粒度静态策略向细粒度动态协同**的范式转变。以下是核心进展的系统梳理：

## 一、核心算法框架突破

### 1. DALI：工作负载感知的动态卸载框架

中国科学院自动化所提出的 **DALI** 是当前本地PC部署的标杆方案。它针对现有方法的三大低效问题——静态专家分配导致的CPU-GPU负载失衡、预取高负载专家精度低、缓存策略忽视工作负载动态性——提出了三项创新：

- **Greedy Assignment 策略**：将专家分配建模为0-1整数优化问题，按CPU与GPU执行时间差异排序，动态决定每个专家的去向，实现92%的最优解性能，但求解开销仅为最优解的5%。
    
- **Residual-Based Prefetching**：利用相邻MoE层之间的残差信息修正特征，精准预测高负载专家，解决传统预取在混合框架中命中率极低的问题。
    
- **Workload-Aware Cache Replacement**：基于专家工作负载的时间相关性设计缓存替换策略，显著提升缓存命中率。
    

在 DeepSeek-V2-Lite、Qwen3-30B-A3B、Mixtral-8×7B 等模型上的测试表明，DALI 在 prefill 阶段相比 llama.cpp、KTransformers、MoE-Lightning、HybriMoE 分别实现 **7.62×、3.80×、2.45×、2.00×** 加速；decoding 阶段分别实现 **3.97×、2.16×、1.48×、1.32×** 加速。

[](https://arxiv.org/html/2602.03495v1)

### 2. ExpertFlow：预测性专家缓存与Token调度

发表于 DAC 2026 的 **ExpertFlow** 通过"预测-调度-缓存"三位一体设计，解决了传统卸载中专家预测不准确、专家利用率低、缓存策略失效的问题：

- **Routing Path Predictor (RPP)**：采用类T5的Encoder-Decoder架构，在**单次前向传播中预测所有MoE层**的专家激活，实现95%的预测准确率，支持跨领域泛化。
    
- **Token Scheduler (TS)**：基于K-Means聚类对token进行重分组，将路由路径相似的token聚合到同一批次，减少每批次激活的专家数量，提升单专家token负载。
    
- **Expert Cache Engine (ECE)**：结合预测性局部感知缓存（PLEC）和实时纠错机制，实现91.96%的缓存命中率，较LRU提升61.15%。
    

ExpertFlow 在单GPU环境下将GPU内存占用降低 **93.72%**，吞吐量提升最高达 **10×**。

[](https://arxiv.org/html/2410.17954v2)

### 3. LayerScope：预测性跨层调度

针对多批次MoE推理在旧式服务器上的部署瓶颈，**LayerScope** 提出三层协同设计：

- **LLaPor（可学习层感知预测器）**：发现MoE不同层组（输入层、中间层、输出层）具有不同的专家激活模式，据此实现高精度专家选择预测。
    
- **PreSched（预取感知跨层调度）**：量化全局性能收益而非局限于单层局部最优，智能平衡预取成本与按需加载开销。
    
- **AsyncIO（异步I/O优化器）**：解耦I/O与计算，重叠PCIe传输与GPU/CPU内核执行。
    

实验显示，LayerScope 实现 **141%** 的端到端推理吞吐量提升和 **74.6%** 的解码延迟降低。

[](https://arxiv.org/html/2509.23638v2)

### 4. FineMoE：细粒度专家卸载

EuroSys 2026 的 **FineMoE** 提出"专家映射"（Expert Map）数据结构，在迭代级别记录门控网络输出的概率分布，通过比较历史专家轨迹相似性指导卸载决策。同时结合输入提示的语义嵌入增强专家搜索，实现：

- 推理延迟降低 **47%**    
- 专家命中率提升 **39%**     [](https://intellisys.haow.us/assets/pdf/Hanfei_FineMoE_EuroSys26.pdf)
    

### 5. ZipMoE：无损压缩与缓存亲和调度

**ZipMoE** 针对边缘设备，利用MoE参数的统计冗余性，通过缓存-调度协同设计，将on-device MoE推理从I/O瓶颈转变为计算中心型工作流：

- 推理延迟降低 **72.77%**     
- 吞吐量提升 **6.76×** 
    [](https://arxiv.org/abs/2601.21198)


## 二、理论认知深化：并非所有MoE都适合卸载

ICLR 2026 的一项关键研究首次系统量化了MoE模型的**局部路由一致性**（Local Routing Consistency）属性，指出：

- **核心发现**：连续token是否激活相似专家，这种"局部路由一致性"在不同MoE模型间差异巨大。GRIN-MoE等模型展现出强连续路由模式，非常适合专家缓存；而Jamba-Mini-1.6等模型则不具备此特性。
    
- **设计建议**：
    
    - 追求**全局负载均衡**而非局部负载均衡        
    - 若计划支持专家卸载，应**避免或减少共享专家**的使用        
    - 在可行范围内**增加专家数量和激活数量**        
    - 通过预训练数据分布引导**领域专业化专家**         
    - **缓存大小设为活跃专家数量的2倍**，可平衡效果与效率                 [](https://hub.baai.ac.cn/view/52231)


## 三、工程实践与开源生态进展

### 1. 推理引擎原生支持

- **vLLM**（2026年3月，PR #37190）：引入MoE专家CPU卸载，支持GPU LFRU（Least Frequently Recently Used）缓存，在7.6GB VRAM下以缓存大小8运行Nemotron达到15.6 tokens/s，较标准LRU提升5.2%。
    
- **llama.cpp**（2026年3月，Issue #20757）：提出双层GPU+RAM专家缓存，采用SLRU（Segmented LRU）策略，在GPT-OSS-120B上实现8GB VRAM下12-14 tokens/s的稳态性能。同时支持通过 `-ot ".ffn_.*_exps.=CPU"` 将DeepSeek-V3.1的MoE层卸载到CPU，让非MoE层常驻GPU。    [](https://theagenttimes.com/articles/dynamic-expert-caching-delivers-27-faster-moe-inference-on-c-319f3c82)
    

### 2. 动态专家量化（DynaExq）

2026年出现了一种新的精度分级卸载思路：每个专家维护一个三级精度状态机——**热（FP8）、温（INT4）、冷（INT2或CPU卸载）**。通过运行频率计数器触发状态转换，且重量化过程在独立CUDA流上异步执行，不阻塞推理路径。虽然完整的动态运行时精度切换仍属研究级，但基于imatrix的静态混合精度（如ExLlamaV2的EXL2格式）已可通过校准数据自动为热专家分配更高比特率。[](https://www.spheron.network/blog/dynamic-expert-quantization-moe-offloading-gpu-cloud/)

### 3. 专家卸载与KV Cache卸载的协同

2026年的系统开始将专家卸载与KV Cache分层管理结合。vLLM 0.7+ 支持PagedAttention块级别的CPU卸载和磁盘卸载（实验性），配合前缀缓存去重，使得在单卡H100上运行144GB KV工作集成为可能。 [](https://callsphere.ai/blog/kv-cache-offloading-cpu-gpu-nvme-tradeoffs-2026)


## 四、总结：2026年MoE本地部署的技术趋势
| 维度       | 2025年及以前                   | 2026年进展                          |
| :------- | :------------------------- | :------------------------------- |
| **卸载粒度** | 层级别（Layer-wise）或==静态专家分配== | 动态专家级别（Expert-wise），==实时负载均衡==   |
| **预取策略** | 基于统计频率或简单启发式               | 残差修正、跨层路由路径预测、语义感知               |
| **缓存策略** | LRU/LFU                    | 工作负载感知、预测性局部感知、SLRU/LFRU         |
| **卸载目标** | CPU内存/NVMe                 | ==CPU内存 + 动态精度分级 + 与KV Cache协同== |
| **理论指导** | 经验性尝试                      | 局部路由一致性量化、最优缓存大小理论               |

