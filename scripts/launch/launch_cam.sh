#!/usr/bin/env bash
# start_camera_and_bridge.sh

# 1) Bei Strg-C: sende SIGINT an beide Kinder und beende dich
trap 'echo "Stopping camera_node and rosbridge_websocket…"; \
      kill -SIGINT "$camera_pid" 2>/dev/null; \
      kill -SIGINT "$bridge_pid" 2>/dev/null; \
      exit 0' SIGINT SIGTERM

# 2) Workspace sourcen und Domain setzen
source ~/xtrack-hub-main/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=1

# 3) Kamera-Node im Hintergrund starten und PID merken
ros2 run camera_ros camera_node &
camera_pid=$!

# 4) Rosbridge-Websocket im Hintergrund starten und PID merken
ros2 run rosbridge_server rosbridge_websocket &
bridge_pid=$!

# 5) Warten, bis wir ein Signal bekommen
wait
