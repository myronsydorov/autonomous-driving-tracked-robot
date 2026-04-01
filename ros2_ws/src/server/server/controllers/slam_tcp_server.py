# slam_tcp_server.py – ultra‑simple version **without ACL**
"""Tiny threaded TCP server that starts/stops *slam_toolbox*.

* No access‑control – any client on the network can send commands.
* Commands (newline‑terminated):
    start            → launch SLAM if not running
    stop             → stop it (SIGINT)
    status           → "running" or "stopped"
    save:<filepath>  → call SaveMap service

Drop it into your controller exactly like MotorTCPServer, e.g.::

    self.slam_server = SlamTCPServer(port=6005, launch_cmd=LAUNCH_TUPLE)
    self.slam_server.start()
"""

import os
import signal
import socket
import subprocess
import threading
from typing import Tuple

from utils.logger import logger

DEFAULT_PORT: int = 6005
DEFAULT_LAUNCH: Tuple[str, ...] = (
    "ros2",
    "launch",
    "slam_toolbox.launch.py",
)


class SlamTCPServer:  # noqa: D401 – imperative naming OK here
    def __init__(self, *, port: int = DEFAULT_PORT, launch_cmd: Tuple[str, ...] = DEFAULT_LAUNCH):
        self._port = port
        self._launch_cmd = launch_cmd
        self._proc = None  # subprocess.Popen or None
        self._stop_flag = False
        self._thread = threading.Thread(target=self._serve, daemon=True)

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop_flag = True
        self._stop_slam()
        self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Networking --------------------------------------------------------
    def _serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("", self._port))
            srv.listen(1)
            logger.info(f"[slam_tcp] listening on 0.0.0.0:{self._port}")

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
                    self._start_slam(); conn.sendall(b"ok\n")
                elif cmd == "stop":
                    self._stop_slam(); conn.sendall(b"ok\n")
                elif cmd == "status":
                    status = "running" if self._proc and self._proc.poll() is None else "stopped"
                    conn.sendall((status + "\n").encode())
                elif cmd.startswith("save:"):
                    self._save_map(cmd.split(":", 1)[1]); conn.sendall(b"ok\n")
                else:
                    conn.sendall(b"error:unknown_cmd\n")

    # ------------------------------------------------------------------
    # SLAM process control ---------------------------------------------
    def _start_slam(self):
        if self._proc and self._proc.poll() is None:
            return
        logger.info("[slam_tcp] launching slam_toolbox …")
        # capture output so the user can see errors
        self._proc = subprocess.Popen(
            self._launch_cmd,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        threading.Thread(target=self._pipe_logs, daemon=True).start()

    def _pipe_logs(self):
        """Forward child stdout to our logger for visibility."""
        if not self._proc or self._proc.stdout is None:
            return
        for line in self._proc.stdout:
            logger.info("[slam] " + line.rstrip())
            if self._stop_flag:
                break

    def _stop_slam(self):
        if self._proc and self._proc.poll() is None:
            logger.info("[slam_tcp] stopping slam_toolbox …")
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("[slam_tcp] force-killing slam_toolbox")
                os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
        self._proc = None

    def _save_map(self, path: str):
        if not (self._proc and self._proc.poll() is None):
            return
        logger.info(f"[slam_tcp] saving map → {path}")
        subprocess.run(
            [
                "ros2",
                "service",
                "call",
                "/slam_toolbox/save_map",
                "slam_toolbox/srv/SaveMap",
                f'filename: "{path}"',
            ],
            check=False,
        )

