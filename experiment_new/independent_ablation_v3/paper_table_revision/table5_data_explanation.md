# Table 5 Data Explanation

独立消融实验基于3个TUM RGB-D动态序列进行，每个序列对5种配置分别独立运行3次，并采用相同的轨迹评价脚本和统计协议。结果显示，Semantic Mask相较Baseline降低了ATE，但RPE改善有限，说明单帧语义掩膜能够减少部分动态目标干扰，但对相邻位姿估计稳定性的提升并不充分。

Temporal Consistency取得最低ATE（0.2424 ± 0.2317 m），同时RPE降至0.0296 ± 0.0105 m，动态状态切换频率也低于Semantic Mask和Object-level Semantic Map，说明时间一致性建模有助于降低动态判断抖动并改善轨迹估计。Full Model取得最低RPE（0.0244 ± 0.0074 m）和最低Switching Frequency（0.0216 ± 0.0217），表明完整配置在相对轨迹稳定性和动态判别连续性方面表现较好。

需要注意的是，Full Model的Pose Missing Ratio最高（0.4615 ± 0.4045），说明更严格的动态信息抑制降低了轨迹输出完整性。Object-level Semantic Map的主要作用在于增强对象级环境表达与动态目标管理能力，不宜仅用ATE或RPE评价其贡献。综合来看，时间一致性相关模块能够改善动态判别连续性和相对轨迹稳定性，但会带来一定的轨迹完整性代价。
