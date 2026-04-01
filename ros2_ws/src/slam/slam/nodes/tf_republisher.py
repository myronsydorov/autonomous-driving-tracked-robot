#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import tf_transformations

class StaticRepublisher(Node):
    def __init__(self):
        super().__init__('static_republisher')
        self.br = TransformBroadcaster(self)
        # Broadcast at 10 Hz
        self.create_timer(0.1, self.broadcast)

    def broadcast(self):
        now = self.get_clock().now().to_msg()

        # 1) laser -> base_link
        t1 = TransformStamped()
        t1.header.stamp = now
        t1.header.frame_id = 'base_link'
        t1.child_frame_id = 'laser'
        # TODO: set these to your actual laser mounting offsets:
        t1.transform.translation.x = 0.0
        t1.transform.translation.y = 0.0
        t1.transform.translation.z = 0.0
        # Rotate the laser frame +90° about Z so its "forward" points along +X
        q1 = tf_transformations.quaternion_from_euler(0.0, 0.0, 0.0)
        t1.transform.rotation.x = q1[0]
        t1.transform.rotation.y = q1[1]
        t1.transform.rotation.z = q1[2]
        t1.transform.rotation.w = q1[3]
        self.br.sendTransform(t1)

        # 2) imu_link -> base_link
        t2 = TransformStamped()
        t2.header.stamp = now
        t2.header.frame_id = 'base_link'
        t2.child_frame_id = 'imu_link'
        # TODO: set these to your actual IMU mounting offsets:
        t2.transform.translation.x = 0.0
        t2.transform.translation.y = 0.0
        t2.transform.translation.z = 0.0 #90 degree passst nicht
        q2 = tf_transformations.quaternion_from_euler(0.0, 0.0, 0.0)
        t2.transform.rotation.x = q2[0]
        t2.transform.rotation.y = q2[1]
        t2.transform.rotation.z = q2[2]
        t2.transform.rotation.w = q2[3]
        self.br.sendTransform(t2)


def main():
    rclpy.init()
    node = StaticRepublisher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
