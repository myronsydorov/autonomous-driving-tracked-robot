#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg    import Odometry
from geometry_msgs.msg import Quaternion
import numpy as np
from scipy.spatial import cKDTree

class ScanMatcher(Node):
    def __init__(self):
        super().__init__('scan_matcher')
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.odom_pub = self.create_publisher(Odometry, '/lidar_odom', 10)

        self.prev_pts  = None
        self.prev_time = None
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

    def on_scan(self, scan_msg: LaserScan):
        # 1) build point cloud in robot frame
        ranges = np.array(scan_msg.ranges)
        angles = scan_msg.angle_min + np.arange(ranges.shape[0]) * scan_msg.angle_increment
        valid = np.isfinite(ranges)
        pts = np.vstack((ranges[valid]*np.cos(angles[valid]),
                         ranges[valid]*np.sin(angles[valid]))).T

        # 2) downsample to at most 800 pts
        N = pts.shape[0]
        if N > 800:
            idx = np.random.choice(N, 800, replace=False)
            pts = pts[idx]

        # 3) first scan → initialize
        if self.prev_pts is None:
            self.prev_pts  = pts
            self.prev_time = scan_msg.header.stamp
            return

        # 4) build KD‐Tree on current scan
        tree = cKDTree(pts)

        # 5) iterative point-to-point ICP (with outlier rejection)
        src = self.prev_pts.copy()
        T   = np.eye(3)
        max_corr_dist = 0.4  # reject correspondences beyond 0.4 m
        for _ in range(15):
            dists, idx = tree.query(src, k=1)
            mask = dists < max_corr_dist
            if mask.sum() < 10:
                break
            P = src[mask]
            Q = pts[idx[mask]]

            # centroids
            mu_P = P.mean(axis=0)
            mu_Q = Q.mean(axis=0)
            # zero‐mean
            P0 = P - mu_P
            Q0 = Q - mu_Q
            # covariance
            H = P0.T.dot(Q0)
            U, S, Vt = np.linalg.svd(H)
            R = Vt.T.dot(U.T)
            if np.linalg.det(R) < 0:
                Vt[1,:] *= -1
                R = Vt.T.dot(U.T)
            t = mu_Q - R.dot(mu_P)

            # incremental transform
            inc = np.vstack((np.hstack((R, t[:,None])), [0,0,1]))
            T = inc.dot(T)
            src = (R.dot(src.T) + t[:,None]).T

        # 6) extract dx,dy,yaw
        dx_local  = T[0,2]
        dy_local  = T[1,2]
        yaw_inc   = np.arctan2(T[1,0], T[0,0])

        # 7) rotate into world frame
        c, s = np.cos(self.yaw), np.sin(self.yaw)
        dx = c*dx_local - s*dy_local
        dy = s*dx_local + c*dy_local

        # 8) time delta
        t0 = self.prev_time.sec + self.prev_time.nanosec*1e-9
        t1 = scan_msg.header.stamp.sec + scan_msg.header.stamp.nanosec*1e-9
        dt = max(t1 - t0, 1e-6)

        # 9) update global pose
        self.x  += dx
        self.y  += dy
        self.yaw += yaw_inc

        # 10) publish Odometry
        odom = Odometry()
        odom.header = scan_msg.header
        odom.header.frame_id    = 'odom'
        odom.child_frame_id     = 'base_link'
        odom.pose.pose.position.x = float(self.x)
        odom.pose.pose.position.y = float(self.y)
        odom.pose.pose.position.z = 0.0
        qz = np.sin(self.yaw/2.0); qw = np.cos(self.yaw/2.0)
        odom.pose.pose.orientation = Quaternion(x=0.0,y=0.0,z=float(qz),w=float(qw))
        odom.twist.twist.linear.x  = float(dx/dt)
        odom.twist.twist.linear.y  = float(dy/dt)
        odom.twist.twist.angular.z = float(yaw_inc/dt)

        # 11) simple covariance
        pose_cov = [0.1 if i%7==0 else 0.0 for i in range(36)]
        odom.pose.covariance  = pose_cov
        odom.twist.covariance = pose_cov

        self.odom_pub.publish(odom)

        # 12) store for next
        self.prev_pts  = pts
        self.prev_time = scan_msg.header.stamp

def main():
    rclpy.init()
    node = ScanMatcher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
