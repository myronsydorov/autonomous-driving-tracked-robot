#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import socket
import time
import math

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')

        # Parameter deklarieren
        self.declare_parameter('tcp_host', '192.168.0.115')
        self.declare_parameter('tcp_port', 6003)
        self.declare_parameter('linear_scale', 1.0)
        self.declare_parameter('angular_scale', 1.0)
        self.declare_parameter('v_min', 0.2)   # Minimal­speed (deadband)
        self.declare_parameter('v_max', 0.6)   # Maxspeed
        self.declare_parameter('cmd_vel_timeout', 0.5)

        p = self.get_parameter
        self.tcp_host      = p('tcp_host').value
        self.tcp_port      = p('tcp_port').value
        self.linear_scale  = p('linear_scale').value
        self.angular_scale = p('angular_scale').value
        self.v_min         = p('v_min').value
        self.v_max         = p('v_max').value
        self.timeout       = p('cmd_vel_timeout').value

        # Socket aufsetzen
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.get_logger().info(f"Connecting to {self.tcp_host}:{self.tcp_port}…")
        while True:
            try:
                self.sock.connect((self.tcp_host, self.tcp_port))
                self.get_logger().info("Connected to motor server")
                break
            except Exception as e:
                self.get_logger().warn(f"Connection failed: {e}, retrying in 2s")
                time.sleep(2)

        # Subscriber & Watchdog
        self.last_cmd_time = self.get_clock().now()
        self.create_timer(0.1, self._watchdog)
        self.create_subscription(Twist, '/cmd_vel', self._on_cmd_vel, 10)
        self.get_logger().info("MotorNode initialized")

    def _remap(self, x: float) -> float:
        """Remapped: 0→0, (0,1]→[v_min, v_max] linear."""
        if x == 0.0:
            return 0.0
        sign = math.copysign(1.0, x)
        mag = min(1.0, abs(x))
        return sign * (self.v_min + (self.v_max - self.v_min) * mag)

    def _on_cmd_vel(self, msg: Twist):
        self.last_cmd_time = self.get_clock().now()

        v_in = msg.linear.x
        w_in = msg.angular.z
        self.get_logger().debug(f"[RAW CMD_VEL]  v={v_in:.3f}, w={w_in:.3f}")

        # Scale
        v = v_in * self.linear_scale
        w = w_in * self.angular_scale
        self.get_logger().debug(f"[SCALED]     v={v:.3f}, w={w:.3f}")

        # Differential Mixing
        if abs(v) < 1e-6 and abs(w) > 1e-6:
            # reine Drehung auf der Stelle
            left, right = -w, w
        elif abs(w) < 1e-6:
            # rein geradlinig
            left = right = v
        else:
            # Mischbetrieb: Vorwärts + Lenken
            reduction = max(0.0, 1.0 - abs(w))
            if w > 0:
                left, right = v * reduction, v
            else:
                left, right = v, v * reduction

        # Wenn eine Seite 0 und die andere !=0, dann halbe Gegenkraft
        if abs(left) < 1e-6 and abs(right) > 1e-6:
            left = -0.5 * right
        elif abs(right) < 1e-6 and abs(left) > 1e-6:
            right = -0.5 * left

        # Clamp raw mix auf [-1,1]
        left  = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))
        self.get_logger().debug(f"[MIXED]      left={left:.3f}, right={right:.3f}")

        # Remap durch Deadband → [0 oder ±v_min…±v_max]
        left  = self._remap(left)
        right = self._remap(right)
        self.get_logger().debug(f"[REMAP]      left={left:.3f}, right={right:.3f}")

        # Falls durch Remapping beide 0 geworden sind, trotzdem drehen auf Stelle:
        if abs(left) < 1e-6 and abs(right) < 1e-6 and abs(w) > 1e-6:
            left = -math.copysign(self.v_min, w)
            right = math.copysign(self.v_min, w)
            self.get_logger().debug(f"[FALLBACK]   left={left:.3f}, right={right:.3f}")

        # Senden
        cmd = f"set:{left:.3f},{right:.3f}\n"
        try:
            self.sock.sendall(cmd.encode('ascii'))
            self.get_logger().debug(f"[SENT CMD]   {cmd.strip()}")
        except Exception as e:
            self.get_logger().error(f"Send failed: {e}")

    def _watchdog(self):
        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
        if elapsed > self.timeout:
            try:
                self.sock.sendall(b"set:0.000,0.000\n")
            except:
                self.get_logger().error("Failed sending stop cmd")

    def destroy_node(self):
        try:
            self.sock.sendall(b"set:0.000,0.000\n")
        except:
            pass
        self.sock.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()


