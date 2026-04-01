#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from controllers.controller import Controller
from administration.administration import Administration
from utils.client_access_manager import ClientAccessManager
from utils.logger import logger

def main():
    # Configuration parameters for sensors and motor control:
    motor_pins = [18,19]         # GPIO pins for motors
    target_ip = "0.0.0.0"         # External computer's IP address (if needed for UDP)
    lidar_port = 6000             # UDP port for Lidar sensor
    imu_port = 1000               # UDP port for IMU sensor
    openmv_port = 6002            # UDP port for OpenMV camera
    motor_port = 6003             # TCP port for motor control
    slam_port = 6005
    nav_port = 6006

    # Admin server configuration:
    admin_port = 6004             # Separate port for admin control
    admin_password = "12345"      # Admin password

    # Create a ClientAccessManager instance
    access_manager = ClientAccessManager("client_access.csv")

    controller = Controller(motor_pins, target_ip, lidar_port, imu_port, openmv_port,
                            motor_port, admin_port, admin_password, access_manager=access_manager)
    logger.info("System ready. Awaiting sensor and motor connections...")


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        controller.cleanup()

if __name__ == '__main__':
    main()


