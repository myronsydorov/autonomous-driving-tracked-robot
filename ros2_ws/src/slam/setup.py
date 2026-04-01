from setuptools import setup
from glob import glob
package_name = 'slam'

setup(
    name=package_name,
    version='0.1.0',
    packages=[
        package_name,
        f'{package_name}.nodes',
        f'{package_name}.packets',
        f'{package_name}.utils',
    ],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', ['config/mapper_params_online_async.yaml']),
        ('share/' + package_name + '/config', ['config/ekf.yaml']),
        ('share/slam/config', glob('config/*.yaml')),
        
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='teamb',
    maintainer_email='teamb@example.com',
    description='Custom SLAM nodes using Lidar and IMU',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'imu_node_publisher = slam.nodes.imu_node_publisher:main',
            'ros2_lidar_node = slam.nodes.ros2_lidar_node:main',
            'imu_to_odom = slam.nodes.imu_to_odom:main',
            'odom_to_tf = slam.nodes.odom_to_tf:main',
            'tf_republisher = slam.nodes.tf_republisher:main',
            'lidar_odom = slam.nodes.lidar_odom:main',             
        ],
    },
)

