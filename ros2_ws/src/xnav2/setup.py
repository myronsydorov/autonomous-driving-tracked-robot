from setuptools import setup
import glob

package_name = 'xnav2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        # package index
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        # package.xml
        ('share/' + package_name, ['package.xml']),
        # launch-Files installieren
        ('share/' + package_name + '/launch', glob.glob('launch/*.py')),
        # Parameter-Dateien installieren
        ('share/' + package_name + '/params', glob.glob('params/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='teamb',
    maintainer_email='teamb@example.com',
    description='Nav2 bringup config for my robot',
    license='Apache 2.0',
    entry_points={
        'launch_py': [
            'bringup = xnav2.launch.bringup_launch:generate_launch_description'
        ],
    },
)
