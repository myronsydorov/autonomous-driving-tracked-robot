# controllers/controller.py

from administration.administration import Administration
from communication.udp_sensor_server import UDPSensorServer
from motors.motor import Motor
from motors.motor_tcp_server import MotorTCPServer
from sensors.lidar_sensor import LidarSensor
from sensors.imu_sensor import IMUSensor
from controllers.slam_tcp_server import SlamTCPServer
from controllers.nav2_tcp_server import Nav2TCPServer
from sensors.openmv_camera import OpenMVCamera
from utils.logger import logger

import shlex

# Map BCM GPIO → (sysfs PWM chip, channel)
PIN_TO_PWM = {
    18: (0, 2),
    19: (0, 3),
}


class Controller:
    def __init__(
        self,
        motor_pins: list[int],
        target_ip: str,
        lidar_port: int,
        imu_port: int,
        openmv_port: int,

        motor_port: int,
        admin_port: int,
        admin_password: str,
        access_manager
    ):
        # Initialize motors on specified GPIO pins
        self.motors = []
        for pin in motor_pins:
            try:
                chip, chan = PIN_TO_PWM[pin]
            except KeyError:
                raise ValueError(f"GPIO pin {pin} not PWM-configured (see PIN_TO_PWM)")
            m = Motor(chip, chan)
            self.motors.append(m)

        # Sensor instances
        lidar_sensor_instance = LidarSensor()
        imu_sensor_instance   = IMUSensor()
        openmv_sensor_instance = OpenMVCamera()

        # Motor TCP control
        self.motor_server = MotorTCPServer(self.motors,access_manager, port=motor_port)
        self.motor_server.start()

        # UDP sensor servers
        self.lidar_server = UDPSensorServer(
            "Lidar", lidar_sensor_instance, access_manager,
            target_ip, port=lidar_port, rights_key="lidar_rights", interval=0.05
        )
        self.imu_server = UDPSensorServer(
            "IMU", imu_sensor_instance, access_manager,
            target_ip, port=imu_port, rights_key="imu_rights", interval=0.001
        )
        self.openmv_server = UDPSensorServer(
            "OpenMV", openmv_sensor_instance, access_manager,
            target_ip, port=openmv_port, rights_key="openmv_rights", interval=0.02
        )

        slam_cmd = shlex.split(
            "bash -c '"
            "source /opt/ros/jazzy/setup.bash && "
            "source /home/teamb/xtrack-hub-main/ros2_ws/install/setup.bash && "
            "export ROS_DOMAIN_ID=1 && "
            "ros2 launch /home/teamb/xtrack-hub-main/ros2_ws/src/slam/launch/slam_toolbox.launch.py "
            "use_sim_time:=false'"
        )
        nav2_cmd = shlex.split(
            "bash -c '"
            "source /opt/ros/jazzy/setup.bash && "
            "source /home/teamb/xtrack-hub-main/ros2_ws/install/setup.bash && "
            "export ROS_DOMAIN_ID=1 && "
            "ros2 launch nav2_bringup bringup_launch.py "
            "params_file:=/home/teamb/xtrack-hub-main/ros2_ws/src/xnav2/params/nav2_params.yaml & "
            "ros2 run robot_control motor_node --ros-args "
            "--params-file /home/teamb/xtrack-hub-main/ros2_ws/src/robot_control/robot_control/motor_node.yaml "
            "--log-level motor_node:=debug'"
        )
        self.slam_server = SlamTCPServer(
            port=6005,
            launch_cmd=tuple(slam_cmd),  # pass tuple -- no need to modify the class
        )
        self.slam_server.start()

        self.nav_server = Nav2TCPServer(
            port=6006,
            launch_cmd=tuple(nav2_cmd),  # or omit launch_cmd if you use the default
        )
        self.nav_server.start()        # Start all servers
        for srv in (
            self.lidar_server,
            self.imu_server,
            self.openmv_server,
        # Create and start the admin server.
        ):
            srv.start()

        # Administration server
        self.admin_server = Administration(
            {
                "motor": self.motor_server,
                "lidar": self.lidar_server,
                "imu": self.imu_server,
                "openmv": self.openmv_server,
            },
            self.motors,
            access_manager,
            port=admin_port,
            admin_password=admin_password
        )
        self.admin_server.start()

    def cleanup(self):
        logger.info("Cleaning up...")

        # Stop all comms
        self.motor_server.stop()
        self.lidar_server.stop()
        self.imu_server.stop()
        self.slam_server.stop()
        self.nav_server.stop()
        self.openmv_server.stop()

        # Shutdown motors
        for motor in self.motors:
            motor.cleanup()

        # Stop admin
        self.admin_server.stop()
