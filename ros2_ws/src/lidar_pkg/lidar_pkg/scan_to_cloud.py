#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, PointCloud2
from laser_geometry import LaserProjection       # pip install laser_geometry

class ScanToCloud(Node):
    def __init__(self):
        super().__init__("scan_to_cloud")
        self.lp  = LaserProjection()
        self.pub = self.create_publisher(PointCloud2, "/scan_cloud", 10)
        self.create_subscription(LaserScan, "/scan", self.cb, 10)

    def cb(self, scan: LaserScan):
        cloud = self.lp.projectLaser(scan)     # z = 0 points
        cloud.header.frame_id = scan.header.frame_id
        self.pub.publish(cloud)

def main():
    rclpy.init()
    rclpy.spin(ScanToCloud())
    rclpy.shutdown()

if __name__ == "__main__":
    main()
