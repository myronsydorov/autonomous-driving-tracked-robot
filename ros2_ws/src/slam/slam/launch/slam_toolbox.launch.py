from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():
    config_path = os.path.join(
        os.getenv('HOME'), 'ros2_ws', 'src', 'slam', 'config', 'slam_toolbox_params.yaml'
    )

    return LaunchDescription([
        Node(
            package='slam_toolbox',
            executable='sync_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[config_path],
        ),
    ])
