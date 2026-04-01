# launch/ekf.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Static TF for IMU
        Node(package='tf2_ros',
             executable='static_transform_publisher',
             name='imu_static_tf',
             arguments=['0','0','0.1','0','0','0','base_link','imu_link']),
        # EKF fuse node
        Node(package='robot_localization',
             executable='ekf_node',
             name='ekf_filter_node',
             output='screen',
             parameters=['config/ekf.yaml']),
    ])
