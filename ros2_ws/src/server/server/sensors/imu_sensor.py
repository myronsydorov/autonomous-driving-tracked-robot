import time
import serial

from packets.imu_packet import IMUPacket
from utils.logger import logger

LOGGER_PREFIX = "IMU"

class IMUSensor:
    def __init__(self, port="/dev/ttyUSB1", baudrate=115200, timeout=1):
        """
        Initialisiert die serielle Verbindung zur OpenMV-Kamera.
        Passe 'port' und 'baudrate' an deine Gegebenheiten an.
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            # Warte kurz, damit sich die Verbindung stabilisieren kann.
            time.sleep(2)
            logger.info(f"IMU connected via {port} with {baudrate} baud.", prefix=LOGGER_PREFIX)
        except Exception as e:
            logger.error(f"Error connecting to IMU: {e}", prefix=LOGGER_PREFIX)
            self.ser = None

    def get_data(self):
        if self.ser is None:
            return "imu: Verbindung nicht hergestellt"

        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline()

                data_without_checksum, checksum = data.decode("utf-8").strip().split('*')
                data_without_checksum = data_without_checksum.lstrip('$')
                values = [float(field) for field in data_without_checksum.split(',')[1:]]

                return IMUPacket(values[0:3], values[3:6], values[6:9], values[9:12]).build()
            else:
                return None
        except Exception as e:
            return f"imu: Fehler beim Lesen: {e}"

