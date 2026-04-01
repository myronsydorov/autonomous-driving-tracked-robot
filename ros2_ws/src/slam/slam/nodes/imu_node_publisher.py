#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import serial
from tf_transformations import quaternion_from_euler

# ---- re-use your old IMUPacket builder here: ----
class IMUPacket:
    def __init__(self, acc, gyro, mag, euler):
        self.acc   = acc
        self.gyro  = gyro
        self.mag   = mag
        self.euler = euler

    def build(self):
        # returns exactly (acc, gyro, mag, euler) as floats
        return self.acc, self.gyro, self.mag, self.euler

# --------------------------------------------------
class IMUNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('publish_rate', 50.0)

        port      = self.get_parameter('port').get_parameter_value().string_value
        baud      = self.get_parameter('baudrate').get_parameter_value().integer_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        rate_hz   = self.get_parameter('publish_rate').get_parameter_value().double_value

        self.ser = serial.Serial(port, baud, timeout=1)
        self.get_logger().info(f'Opened serial port {port} at {baud} baud')

        self.imu_pub = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.timer   = self.create_timer(1.0/rate_hz, self.timer_callback)

    def timer_callback(self):
        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            return

        # suppose your old code treated every line as a 12-value CSV
        # acc (0–2), gyro (3–5), mag (6–8), euler (9–11)
        parts = line.split('*')[0].split(',')
        if len(parts) < 13:
            return

        # drop the leading sentence name, convert next 12 fields to float
        try:
            values = [float(x) for x in parts[1:13]]
        except ValueError:
            return

        acc, gyro, mag, euler = values[0:3], values[3:6], values[6:9], values[9:12]

        # build the single IMU message with all fields set
        msg = Imu()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        # orientation from Euler → quaternion
        q = quaternion_from_euler(euler[0], euler[1], euler[2])
        msg.orientation.x = q[0]
        msg.orientation.y = q[1]
        msg.orientation.z = q[2]
        msg.orientation.w = q[3]
        # small positive covariance so EKF will fuse orientation
        oc = 0.01
        msg.orientation_covariance = [
            oc, 0.0, 0.0,
            0.0, oc, 0.0,
            0.0, 0.0, oc
        ]

        # angular velocity from gyro
        msg.angular_velocity.x = gyro[0]
        msg.angular_velocity.y = gyro[1]
        msg.angular_velocity.z = gyro[2]
        # small positive covariance so EKF will fuse gyro
        gc = 0.05
        msg.angular_velocity_covariance = [
            gc, 0.0, 0.0,
            0.0, gc, 0.0,
            0.0, 0.0, gc
        ]

        # linear acceleration from acc
        msg.linear_acceleration.x = acc[0]
        msg.linear_acceleration.y = acc[1]
        msg.linear_acceleration.z = acc[2]
        # small positive covariance so EKF will fuse accel
        ac = 0.1
        msg.linear_acceleration_covariance = [
            ac, 0.0, 0.0,
            0.0, ac, 0.0,
            0.0, 0.0, ac
        ]

        self.imu_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = IMUNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Shutting down IMU node')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
