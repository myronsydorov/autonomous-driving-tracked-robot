import os
import signal
import socket
import subprocess
import threading
from typing import Tuple

from utils.logger import logger

# Default command launches Nav2 bringup **and** motor_node in one shell.
DEFAULT_LAUNCH_STR = (
    "bash -c '"
    # Source ROS and overlay
    "source /opt/ros/jazzy/setup.bash && "
    "source /home/teamb/xtrack-hub-main/ros2_ws/install/setup.bash && "
    "export ROS_DOMAIN_ID=1 && "
    # Launch Nav2 bringup in background
    "ros2 launch nav2_bringup bringup_launch.py "
    "params_file:=/home/teamb/xtrack-hub-main/ros2_ws/src/xnav2/params/nav2_params.yaml & "
    # Run motor_node (foreground so Ctrl‑C stops all)
    "ros2 run robot_control motor_node --ros-args "
    "--params-file /home/teamb/xtrack-hub-main/ros2_ws/src/robot_control/robot_control/motor_node.yaml "
    "--log-level motor_node:=debug'"
)
DEFAULT_LAUNCH: Tuple[str, ...] = tuple(DEFAULT_LAUNCH_STR.split())

class Nav2TCPServer:
    """Threaded TCP control for Nav2 launch."""

    def __init__(self, *, port: int = 6006, launch_cmd: Tuple[str, ...] = DEFAULT_LAUNCH):
        self._port = port
        self._launch_cmd = launch_cmd
        self._proc = None
        self._stop_flag = False
        self._thread = threading.Thread(target=self._serve, daemon=True)

    # Public API
    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop_flag = True
        self._stop_nav()
        self._thread.join(timeout=5)

    # Networking
    def _serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("", self._port))
            srv.listen(1)
            logger.info(f"[nav_tcp] listening on 0.0.0.0:{self._port}")

            while not self._stop_flag:
                srv.settimeout(1.0)
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket):
        with conn, conn.makefile("r") as reader:
            for line in reader:
                cmd = line.strip()
                if not cmd:
                    continue
                if cmd == "start":
                    self._start_nav(); conn.sendall(b"ok\n")
                elif cmd == "stop":
                    self._stop_nav(); conn.sendall(b"ok\n")
                elif cmd == "status":
                    status = "running" if self._proc and self._proc.poll() is None else "stopped"
                    conn.sendall((status + "\n").encode())
                else:
                    conn.sendall(b"error:unknown_cmd\n")

    # Launch control
    def _start_nav(self):
        if self._proc and self._proc.poll() is None:
            return
        logger.info("[nav_tcp] launching Nav2 bringup …")
        self._proc = subprocess.Popen(
            self._launch_cmd,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        threading.Thread(target=self._pipe_logs, daemon=True).start()

    def _stop_nav(self):
        if self._proc and self._proc.poll() is None:
            logger.info("[nav_tcp] stopping Nav2 …")
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
        self._proc = None

    def _pipe_logs(self):
        if not self._proc or self._proc.stdout is None:
            return
        for line in self._proc.stdout:
            logger.info("[nav] " + line.rstrip())
            if self._stop_flag:
                break
