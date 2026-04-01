import serial
import time

from utils.logger import logger

LOGGER_PREFIX = "OpenMV Cam"

class OpenMVCamera:
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, timeout=1):
        """
        Initialisiert die serielle Verbindung zur OpenMV-Kamera.
        Passe 'port' und 'baudrate' an deine Gegebenheiten an.
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(1)
            logger.info(f"OpenMV camera connected via {port} with {baudrate} baud.", prefix=LOGGER_PREFIX)
        except Exception as e:
            logger.error(f"Error connecting to OpenMV camera: {e}", prefix=LOGGER_PREFIX)
            self.ser = None

    def get_data(self):
        if self.ser is None:
            return "openmv: Connection not established"

        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline()
                return data.decode("utf-8").strip() + "\n"
            else:
                return None
        except Exception as e:
            return f"openmv: Error reading data: {e}"
