import numpy as np
import matplotlib.pyplot as plt

# === 修改这里的路径为你的文件 ===
est_file = "/home/zt/ORB_SLAM2_AddSemantic/TUM_fr3_walking_xyz_results/CameraTrajectory_YOLO_xyz.txt"
gt_file  = "/home/zt/ORB_SLAM2_AddSemantic/dataset/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt"

# === 加载数据：TUM 格式 txt：timestamp tx ty tz qx qy qz qw ===
est = np.loadtxt(est_file)
gt = np.loadtxt(gt_file)

# === 只取位置部分 ===
est_xyz = est[:, 1:4]
gt_xyz = gt[:, 1:4]

# === 可视化轨迹在 XY 平面 ===
plt.figure(figsize=(8,6))
plt.plot(gt_xyz[:,0], gt_xyz[:,1], 'k--', label='Groundtruth', linewidth=1.5)
plt.plot(est_xyz[:,0], est_xyz[:,1], 'r-', label='Estimated', linewidth=2.0)
plt.xlabel('X (m)')
plt.ylabel('Y (m)')
plt.legend()
plt.axis('equal')
plt.grid(True)
plt.title('ATE Trajectory Comparison - fr3_walking_xyz')
plt.tight_layout()
plt.savefig("ate_trajectory_orbslam2_fr3.pdf", dpi=300)
plt.show()
