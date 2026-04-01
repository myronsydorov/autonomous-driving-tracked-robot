import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
import numpy as np
from slam.nodes.lidar_sensor import LidarSensor

class LidarPublisher(Node):
    def __init__(self):
        super().__init__('lidar_publisher')
        self.publisher_ = self.create_publisher(LaserScan, '/scan', 10)
        self.lidar = LidarSensor(ip="192.168.11.2", port=8089)
        self.timer = self.create_timer(0.1, self.publish_scan)

    def publish_scan(self):
        print("[ROS2] Timer tick — checking for LiDAR data...")

        data = self.lidar.get_data()

        if not data:
            print("[ROS2] No data received from lidar_sensor.")
            return

        print(f"[ROS2] Received {len(data)} points from lidar_sensor.")

        msg = LaserScan()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser'

        ranges = [float('inf')] * 360
        intensities = [0.0] * 360

        for point in data:
            raw_ang = point['angle']
            fixed_ang = - raw_ang
            angle_deg = int(np.degrees(fixed_ang)) % 360
            ranges[angle_deg] = float(point['distance'])
            intensities[angle_deg] = float(point['quality'])
        max_range = 12.0
        ranges = [r if np.isfinite(r) else max_range for r in ranges]

        print(f"[ROS2] Publishing scan with {sum(1 for r in ranges if r < float('inf'))} valid points")

        msg.angle_min = 0.0
        msg.angle_max = 2 * np.pi
        msg.angle_increment = np.pi / 180
        msg.time_increment = 0.0
        msg.scan_time = 0.1
        msg.range_min = 0.05
        msg.range_max = 12.0
        msg.ranges = ranges
        msg.intensities = intensities

        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LidarPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()