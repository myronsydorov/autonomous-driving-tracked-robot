# sensors/lidar_sensor.py
import socket
import threading
import time
import numpy as np
from queue import Empty, Queue

# Optional logger
try:
    from slam.utils.logger import logger
except:
    def logger(*args, **kwargs): print(*args)

LOGGER_PREFIX = "Lidar"

class LidarSensor:
    def __init__(self, ip="192.168.11.2", port=8089):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.is_running = False
        self.data_queue = Queue(maxsize=3)
        self.scan_thread = None
        self.start_scan()

    def start_scan(self):
        try:
            self.sock.sendto(bytearray([0xA5, 0x20]), (self.ip, self.port))
            data, _ = self.sock.recvfrom(1024)
            if len(data) >= 7 and data[0] == 0xA5 and data[1] == 0x5A:
                self.is_running = True
                self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
                self.scan_thread.start()
                logger.info(f"[LIDAR] Scan started", prefix=LOGGER_PREFIX)
                return True
        except Exception as e:
            logger.error(f"Error starting lidar scan: {e}", prefix=LOGGER_PREFIX)
        return False

    def stop_scan(self):
        self.is_running = False
        try:
            self.sock.sendto(bytearray([0xA5, 0x25]), (self.ip, self.port))
            time.sleep(0.1)
            self.sock.close()
        except:
            pass

    def get_data(self):
        try:
            return self.data_queue.get_nowait()
        except Empty:
            return None

    def parse_measurement(self, data):
        if len(data) < 5:
            return None
        try:
            quality = data[0] & 0x3F
            angle_q6 = ((data[2] << 7) | (data[1] >> 1))
            angle = (angle_q6 / 64.0) % 360.0
            distance = ((data[3] | (data[4] << 8)) / 4.0)

            if distance > 0:
                return {
                    'angle': np.radians(angle),
                    'distance': distance / 1000.0,
                    'quality': quality
                }
        except Exception as e:
            logger.error(f"Error parsing measurement: {e}", prefix=LOGGER_PREFIX)
        return None

    def _scan_loop(self):
        current_scan = []
        last_angle = 0.0

        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(1024)
                measurement = self.parse_measurement(data)
                if measurement:
                    angle = measurement['angle']
                    if angle < last_angle and len(current_scan) > 50:
                        if not self.data_queue.full():
                            self.data_queue.put_nowait(current_scan.copy())
                        current_scan = []
                    current_scan.append(measurement)
                    last_angle = angle
            except socket.timeout:
                continue
            except Exception as e:
                logger.info(f"Error in scan loop: {e}", prefix=LOGGER_PREFIX)

    def start(self):
        return self.start_scan()

    def stop(self):
        self.stop_scan()


def main():
    lidar = LidarSensor(ip="192.168.11.2", port=8089)

    try:
        while True:
            data = lidar.get_data()
            if data:
                print(f"Got {len(data)} points")
            else:
                print("No data")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        lidar.stop()


if __name__ == "__main__":
    main()
