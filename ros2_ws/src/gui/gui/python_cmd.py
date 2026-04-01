import socket

SLAM_SERVER_IP = "192.168.0.115"
SLAM_SERVER_PORT = 6005

def slam_cmd(cmd):
    try:
        with socket.create_connection((SLAM_SERVER_IP, SLAM_SERVER_PORT), timeout=2) as s:
            s.sendall((cmd + "\n").encode())
            return s.recv(64).decode().strip()
    except OSError as exc:
        print(f"[SLAM-GUI] Could not reach SlamTCPServer: {exc}")
        return "error"

def nav_cmd(cmd):
    try:
        with socket.create_connection((SLAM_SERVER_IP, SLAM_SERVER_PORT), timeout=2) as s:
            s.sendall((cmd + "\n").encode())
            return s.recv(128).decode().strip()
    except OSError as exc:
        print(f"[NAV-GUI] Could not reach NavTCPServer: {exc}")
        return "error"