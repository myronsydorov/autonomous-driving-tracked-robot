import socket
import threading
import time

from utils.logger import logger

LOGGER_PREFIX = "UDP"

class UDPSensorServer(threading.Thread):
    def __init__(self, sensor_name, sensor, access_manager, host, port, rights_key, interval=0.1):
        threading.Thread.__init__(self, daemon=True)
        self.sensor_name = sensor_name
        self.sensor = sensor
        self.access_manager = access_manager
        self.host = host
        self.port = port
        self.rights_key = rights_key
        self.interval = interval

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        self.running = True
        self.clients = set()
        self.block_client = False

        threading.Thread(target=self._listen_for_registration, daemon=True).start()

    def _listen_for_registration(self):
        while self.running:
            try:
                self.sock.settimeout(1.0)
                data, addr = self.sock.recvfrom(1024)
                ip, port = addr
                client_id, record = self.access_manager.get_client(ip, port)

                if not record.get("banned", False) and record.get(self.rights_key, "1") == "1":
                    self.clients.add((ip, port))

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error while listening for registration: {e}", prefix=LOGGER_PREFIX)

    def run(self):
        logger.info(f"{self.sensor_name} UDP Server started on port {self.port}", prefix=LOGGER_PREFIX)
        while self.running:
            if self.block_client:
                time.sleep(self.interval)
                continue

            data = self.sensor.get_data()

            if data is None:
                time.sleep(self.interval)
                continue

            if isinstance(data, str):
                data = data.encode("utf-8")

            for client_addr in list(self.clients):
                try:
                    self.sock.sendto(data, client_addr)
                except Exception as e:
                    logger.warning(f"Error sending data to {client_addr}: {e}", prefix=LOGGER_PREFIX)
                    self.clients.discard(client_addr)

            time.sleep(self.interval)

    def stop(self):
        self.running = False
        self.sock.close()
