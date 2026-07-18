# 26-Light 竞品分析与核心优势

> 夜间疲劳驾驶光电预警系统 —— 基于近红外 rPPG 的非接触式生理监测方案

---

## 一句话定位

在国家新规（GA/T 2372-2026）强化"夜间 + 生理状态"判定的趋势下，26-Light 用低成本的近红外 rPPG 非接触方案，把车企只能白天看"行为"的 DMS，升级为**夜间也能看"生理"的超前预警系统**。

---

## 一、国家层面的措施（监管与法规）

### 1. 基础法规：什么算"疲劳驾驶"

《道路交通安全法实施条例》第62条：连续驾驶机动车**超过4小时未停车休息，或停车休息时间少于20分钟**，即构成疲劳驾驶。

### 2. 最新规则：GA/T 2372-2026（2026年6月1日全国实施）

公安部《机动车驾驶人疲劳驾驶认定规则》，采用 **"驾驶行为 + 生理状态 + 生活轨迹"三维判定**，满足任一即认定疲劳：

- 通用：连续驾驶超4小时未休息（或休息＜20分钟）；
- 客运驾驶人：**22:00—次日6:00 连续驾驶超2小时**未休息，或24小时内累计驾驶超8小时（网约车、出租车、客车司机均适用）；
- 事故调查：监测设备发现事故前10分钟内出现**疲劳闭眼（双眼完全闭合持续2秒以上）**或脑电疲劳特征，也可认定。

### 3. 处罚标准

| 车辆类型 | 处罚 |
|---------|------|
| 中型以上载客 / 危险品运输车 | 扣 12 分 + 罚款 200 元 |
| 货运车 | 扣 3 分 + 罚款 200 元 |
| 其他机动车 | 扣 6 分 + 罚款 200 元 |
| 造成重大事故 | 依《刑法》第133条以交通肇事罪追究刑责 |

### 4. 营运车辆强制技术管控

国家推行"道路运输车辆主动安全智能防控系统"，强制安装前向碰撞预警、车道偏离、**疲劳驾驶预警**、分心/接打电话/抽烟预警等功能，数据实时上传监管平台。

> **小结**：国家手段以"时间管控 + 处罚 + 营运车强制装设备 + 平台监管"为主，**主要靠事后认定与时长限制**，对私家车、夜间个体驾驶的实时生理监测覆盖不足。

---

## 二、车企/行业的技术应对（DMS）

主流方案是 **DMS（Driver Monitoring System，驾驶员监测系统）**，属于 ADAS 重要组成：

- **技术路线**：主动式（**红外摄像头**面部识别）已成主流，通过面部关键点提取头姿和眼部区域，识别闭眼、分心；
- **摄像头位置**：仪表台、A柱、方向盘、车灯附近；
- **检测内容**：闭眼、打哈欠、点头、视线偏移，检测到即分级提醒；
- **法规驱动**：欧盟已要求**2024 年起所有新车型强制配备 DMS**，Euro NCAP 将其纳入五星评级；DDAW 需在驾驶员困倦达到 **KSS（卡罗林斯卡嗜睡量表）≥8 级**时报警（来源：Aptiv、Seeing Machines 官网）；
- **市场体量**：仅 Smart Eye 一家的 DMS 软件已装载于全球超 **400 万辆**汽车（来源：Smart Eye 官网）。

**车企方案的局限：**

1. 以**可见光摄像头 + 行为特征**为主，**夜间/弱光成像差**；
2. 只看"行为表象"（已经闭眼/打哈欠＝疲劳已发生），**缺少超前的生理信号预警**；
3. 整车选配/高配功能，**成本高、不可移植**到老旧车与私家车。

---

## 三、关于"脑电（EEG）怎么测"的补充

新规用"包括但不限于"列举了视频监控、脑电测量等手段，**脑电并非强制或日常标配**，仅在专业场景（货运、长途客运、矿用车、佩戴疲劳监测设备的司机）才可能存在。

行驶中测脑电的实际方式：

| 方式 | 原理 | 应用阶段 |
|------|------|---------|
| 疲劳监测帽 / 头带（干电极） | 帽檐/头带内嵌干电极采集头皮脑电 | 最现实，如 SmartCap LifeBand，干电极临床级 EEG、宣称 94.7% 准确率，用于矿山/货运/客运（来源：SmartCap 官网） |
| 入耳式脑电（ear-EEG） | 电极做进耳塞 | 研究/早期产品 |
| 头枕电容电极（cEEG） | 隔头发非接触感应 | 实验室阶段 |
| 传统湿电极脑电帽 | 涂导电膏、多通道 | 仅科研，不适合真实驾驶 |

**疲劳指数算法**：疲劳时 θ波(4–8Hz)上升、α波(8–13Hz)下降，常用 **(α+θ)/β** 比值；"数值小于30"通常是把疲劳指数归一化到 0–100 的警觉度评分，低于阈值即判重度疲劳。

> EEG 是金标准之一，但**必须佩戴、信号易受颠簸干扰、难普及**——这恰恰反衬出 rPPG 非接触方案的落地优势。

---

## 四、三方对比一览

| 维度 | 国家监管措施 | 主流车企 DMS | **26-Light（本项目）** |
|------|------------|-------------|----------------------|
| 手段 | 时长限制+处罚+营运车强制装备 | 可见光摄像头看行为 | **近红外 rPPG 生理信号 + 行为多模态融合** |
| 夜间可用 | — | ❌ 弱光失效 | ✅ **850nm 近红外，全黑可用、人眼不可见** |
| 预警时机 | 事后认定 | 行为已发生才报警 | ✅ **心率/HRV 变化早于行为，超前预警** |
| 是否接触 | — | 非接触 | ✅ **非接触，无需佩戴** |
| 误报控制 | — | 单一行为易误报 | ✅ **多模态融合降误报** |
| 成本/普及 | 营运车设备贵 | 整车高配选装 | ✅ **STM32+相机+灯带，低成本可后装** |

---

## 五、五大核心优势

**1. 攻"夜间"这个真痛点**
疲劳事故高发于深夜，新规也特别盯紧 22:00–6:00。主流可见光 DMS 夜间失效，而 850nm 主动近红外在**全黑环境清晰成像、且人眼不可见不干扰驾驶**——直接补位车企方案的盲区。

**2. 从"行为表象"升级到"生理本质"**
车企 DMS 看的是"已经闭眼/打哈欠"——疲劳已发生；本项目用 **rPPG 心率 + HRV**（自主神经指标）捕捉**更早的生理信号**，实现超前预警，与新规"生理状态"判定维度一致。

**3. 非接触，碾压 EEG 的落地性**
法规认可脑电代表认可"生理信号"方向，但 EEG 必须佩戴、信号易受干扰、难普及。本项目同属"生理状态"维度，却**完全非接触、零佩戴**，私家车可直接加装。

**4. 多模态融合，更稳更准**
HRV + PERCLOS + 哈欠 + 头姿 按权重融合，相比单一行为检测**显著降低误报漏报**，鲁棒性更强。

**5. 低成本、可后装，填补市场空白**
国家强制方案集中在昂贵营运车设备、车企 DMS 是高配选装。本项目用 STM32 + 近红外相机 + LED 灯带，**成本低、可加装到私家车和老旧车**——精准切入"个体/私家车夜间疲劳监测"这块覆盖不足的空白。

---

## 六、竞争壁垒

> **"夜间 + 非接触 + 生理信号 + 低成本可后装"四点同时满足** ——国家措施做不到实时生理监测，车企 DMS 夜间失效且只看行为，EEG 方案必须佩戴难普及。26-Light 是这几条交集里唯一的低成本落地方案。

---

## 参考资料（均为政府官网 / 企业官网 / 学术数据库）

**国家法规 / 措施（政府官网）**

- 公安部官网 ·《机动车驾驶人疲劳驾驶认定规则》起草负责人权威解读：<https://www.mps.gov.cn/n6557563/c10480727/content.html>
- 公安部 · 公安标准化信息服务平台（GA/T 2372-2026 标准计划/检索）：<https://ywtb.mps.gov.cn/gabzh/portal/planDetail/313685> ｜ 标准检索：<https://ywtb.mps.gov.cn/gabzh/portal/xxcx/std>
- 北京市公安局 · 行政处罚清单（连续驾驶超4小时未休息处罚依据）：<https://gaj.beijing.gov.cn/wsgs/zqxx/xzcfqd/202004/t20200407_1795617.html>
- 江苏省人民检察院 · 疲劳驾驶新规6月1日实施（官方解读）：<https://www.jsjc.gov.cn/yaowen/202605/t20260529_1333929.shtml>
- 重庆市人民政府网 · 6月1日起疲劳驾驶新规全国落地：<https://www.cq.gov.cn/ywdt/bmts/202604/t20260407_15594290.html>
- 国家市场监督管理总局 · 全国标准信息公共服务平台（标准检索）：<https://std.samr.gov.cn/>
- 山东省交通运输厅 ·《道路运输车辆主动安全智能防控系统 终端技术规范》（PDF）：<http://jtt.shandong.gov.cn/module/download/downfile.jsp?classid=0&filename=2e242e4af317466fa9ce34d12cd0104e.pdf>

**车企 / 行业 DMS 技术（企业官网）**

- Aptiv（安波福）官网 · What Is a Driver-Monitoring System（含欧盟2024强制、Euro NCAP、KSS≥8）：<https://www.aptiv.com/en/insights/article/what-is-a-driver-monitoring-system>
- Valeo（法雷奥）官网 · Driver Monitoring System：<https://www.valeo.com/en/catalogue/cda/driver-monitoring-system/>
- Smart Eye 官网 · Driver Monitoring System（已装载超400万辆）：<https://smarteye.se/solutions/automotive/driver-monitoring-system/>
- Seeing Machines 官网 · Understanding Driver Drowsiness and Attention Warning (DDAW)：<https://seeingmachines.com/understanding-driver-drowsiness-and-attention-warning-ddaw-systems/>

**脑电（EEG）疲劳监测（企业官网 / 学术库）**

- SmartCap 官网 · LifeBand 干电极脑电疲劳监测：<https://www.smartcaptech.com/>
- SmartCap 官方支持中心 · The Science behind SmartCap：<https://support.smartcaptech.com/hc/en-us/articles/204164340-Background-of-the-Science-behind-SmartCap>
- PubMed Central · EEG brain signals to detect the sleep health of a driver（深度学习框架）：<https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9453302/>

**rPPG 非接触生理监测（企业官网 / 学术库）**

- Philips（飞利浦）官网 · Biosensing by rPPG（rPPG 技术原创方之一）：<https://www.philips.com/a-w/about/innovation/ips/ip-licensing/programs/biosensing-by-rppg.html>
- PubMed Central · Robust Heart Rate Variability Measurement from Facial Videos（人脸视频测 HRV）：<https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10376629/>
- PubMed Central · Contactless Camera-Based Heart Rate and Respiratory Rate Monitoring Using AI：<https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10181491/>
- IEEE Xplore · ReViSe: Remote Vital Signs Measurement Using Smartphone Camera：<https://ieeexplore.ieee.org/document/9989351/>

---

*文档生成日期：2026-05-31*
