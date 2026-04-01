from glob import glob
from setuptools import find_packages, setup

package_name = 'lidar_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')), 
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='teamb',
    maintainer_email='teamb@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [       
            'ros2_lidar_node = lidar_pkg.ros2_lidar_node:main',
            'scan_to_cloud   = lidar_pkg.scan_to_cloud:main',
        ],
    },
)
