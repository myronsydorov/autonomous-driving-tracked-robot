#!/usr/bin/env bash
# launch_xnav2.sh

# 1) Workspace sourcen
source ~/xtrack-hub-main/ros2_ws/install/setup.bash

# 2) ROS Domain setzen
export ROS_DOMAIN_ID=1

# 3) Nav2 starten und PID speichern
ros2 launch nav2_bringup bringup_launch.py \
  params_file:=/home/teamb/xtrack-hub-main/ros2_ws/src/xnav2/params/nav2_params.yaml &
echo $! > /tmp/nav2.pid
