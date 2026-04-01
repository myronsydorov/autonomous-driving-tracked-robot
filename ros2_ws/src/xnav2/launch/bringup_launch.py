from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Pfad zum offiziellen nav2_bringup-Launchfile
    nav2_share = get_package_share_directory('nav2_bringup')
    bringup_file = os.path.join(nav2_share, 'launch', 'bringup_launch.py')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bringup_file),
            launch_arguments={
#                'map': LaunchConfiguration('map'),
                'params_file': LaunchConfiguration('params_file'),
                'use_sim_time': 'false'
            }.items()
        )
    ])

