from packets.base_packet import BasePacket, construct_field
from construct import Array, Float32b

class IMUPacket(BasePacket):

    def __init__(self, position=None, magnetometer=None, acceleration=None, gyroscope=None):
        super().__init__()
        self._position = position if position is not None else [0.0, 0.0, 0.0]
        self._magnetometer = magnetometer if magnetometer is not None else [0.0, 0.0, 0.0]
        self._acceleration = acceleration if acceleration is not None else [0.0, 0.0, 0.0]
        self._gyroscope = gyroscope if gyroscope is not None else [0.0, 0.0, 0.0]

    @property
    def packet_type(self):
        return 0  # IMU packet type

    @construct_field(Array(3, Float32b))
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if not (isinstance(value, list) and len(value) == 3):
            raise ValueError("Position must be a list of three numbers.")
        self._position = value

    @construct_field(Array(3, Float32b))
    def magnetometer(self):
        return self._magnetometer

    @magnetometer.setter
    def magnetometer(self, value):
        if not (isinstance(value, list) and len(value) == 3):
            raise ValueError("Magnetometer must be a list of three numbers.")
        self._magnetometer = value

    @construct_field(Array(3, Float32b))
    def acceleration(self):
        return self._acceleration

    @acceleration.setter
    def acceleration(self, value):
        if not (isinstance(value, list) and len(value) == 3):
            raise ValueError("Acceleration must be a list of three numbers.")
        self._acceleration = value

    @construct_field(Array(3, Float32b))
    def gyroscope(self):
        return self._gyroscope

    @gyroscope.setter
    def gyroscope(self, value):
        if not (isinstance(value, list) and len(value) == 3):
            raise ValueError("Gyroscope must be a list of three numbers.")
        self._gyroscope = value
