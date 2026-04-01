# lidar_packet.py
from packets.base_packet import BasePacket, construct_field
from construct import Int32ub, Float32b, Array, Struct, this

# Define the structure for a single Lidar measurement.
Measurement = Struct(
    "angle" / Float32b,
    "distance" / Float32b,
    "quality" / Float32b
)

class LidarPacket(BasePacket):
    """
    Lidar packet storing ~1200 measurements.
    Each measurement is a dict with keys: angle, distance, quality.
    """
    def __init__(self, measurements=None):
        super().__init__()
        # Internally store a list of dicts: [{"angle":..., "distance":..., "quality":...}, ...]
        self._measurements = measurements if measurements is not None else []

    @property
    def packet_type(self):
        return 1  # e.g., 1 for Lidar

    @construct_field(Int32ub)
    def num_measurements(self):
        """
        Returns the number of measurements.
        """
        return len(self._measurements)

    @construct_field(Array(this.num_measurements, Measurement))
    def measurements(self):
        """
        Returns the measurements in the format expected by Construct.
        """
        return [
            {
                "angle": float(m["angle"]),
                "distance": float(m["distance"]),
                "quality": float(m["quality"])
            }
            for m in self._measurements
        ]
