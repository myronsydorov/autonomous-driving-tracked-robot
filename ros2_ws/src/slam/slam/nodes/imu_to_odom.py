#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion
import math
import time

class ImuToOdom(Node):
    def __init__(self):
        super().__init__('imu_to_odom')
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('child_frame_id', 'odom')
        self.declare_parameter('velocity_decay', 0.99)

        self.frame_id       = self.get_parameter('frame_id').value
        self.child_frame_id = self.get_parameter('child_frame_id').value
        self.decay         = self.get_parameter('velocity_decay').value

        self.sub = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_cb, 10)
        self.pub = self.create_publisher(Odometry, '/odom', 10)

        self.vx = 0.0
        self.vy = 0.0
        self.last_t = None

    def imu_cb(self, msg: Imu):
        now = self.get_clock().now().nanoseconds * 1e-9
        if self.last_t is None:
            self.last_t = now
            return
        dt = now - self.last_t
        self.last_t = now

        # integrate accel to velocity (with a bit of decay to limit drift)
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        self.vx = self.decay * (self.vx + ax * dt)
        self.vy = self.decay * (self.vy + ay * dt)

        odom = Odometry()
        odom.header.stamp    = msg.header.stamp
        odom.header.frame_id = 'map'             # where your odometry is placed
        odom.child_frame_id  = self.frame_id     # usually "base_link"

        # put your fake velocities in
        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.linear.y = self.vy
        # covariances: small but non-zero so EKF fuses them
        cov = 0.2
        odom.twist.covariance = [
            cov, 0,   0, 0, 0, 0,
            0,   cov, 0, 0, 0, 0,
            0,   0,   cov,0, 0, 0,
            0,   0,   0,   1, 0, 0,
            0,   0,   0,   0, 1, 0,
            0,   0,   0,   0, 0, 1
        ]

        self.pub.publish(odom)

def main(args=None):
    rclpy.init(args=args)
    node = ImuToOdom()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
