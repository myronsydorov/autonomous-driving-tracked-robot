#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion
from tf_transformations import quaternion_from_euler
import math

class WheelOdomPublisher(Node):
    def __init__(self):
        super().__init__('wheel_odom_publisher')
        # State for dead-reckoning
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.left_encoder = 0.0
        self.right_encoder = 0.0
        self.last_left = None
        self.last_right = None
        self.last_time = self.get_clock().now()

        # Robot parameters
        self.wheel_base = 0.3   # distance between wheels (m)
        self.ticks_per_meter = 1000.0

        # Publisher for odometry
        self.odom_pub = self.create_publisher(Odometry, '/wheel_odom', 10)
        # Timer to compute and publish odometry
        self.timer = self.create_timer(0.02, self.timer_cb)  # 50 Hz

    def timer_cb(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        if dt <= 0.0:
            return
        self.last_time = now

        # TODO: update self.left_encoder and self.right_encoder from your hardware

        # On first run, initialize last counts
        if self.last_left is None or self.last_right is None:
            self.last_left = self.left_encoder
            self.last_right = self.right_encoder
            return

        # Compute encoder deltas (in meters)
        delta_left  = (self.left_encoder  - self.last_left)  / self.ticks_per_meter
        delta_right = (self.right_encoder - self.last_right) / self.ticks_per_meter
        self.last_left  = self.left_encoder
        self.last_right = self.right_encoder

        # Compute linear and angular velocity
        v = (delta_left + delta_right) / 2.0 / dt
        omega = (delta_right - delta_left) / self.wheel_base / dt

        # Integrate pose
        self.yaw += omega * dt
        self.x   += v * math.cos(self.yaw) * dt
        self.y   += v * math.sin(self.yaw) * dt

        # Build and publish Odometry message
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id    = 'odom'
        odom.child_frame_id     = 'base_link'
        odom.pose.pose.position.x    = float(self.x)
        odom.pose.pose.position.y    = float(self.y)
        # Orientation from integrated yaw
        q = quaternion_from_euler(0.0, 0.0, self.yaw)
        odom.pose.pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        odom.twist.twist.linear.x  = float(v)
        odom.twist.twist.angular.z = float(omega)

        self.odom_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = WheelOdomPublisher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
