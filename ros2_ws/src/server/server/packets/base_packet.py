# base_packet.py

import time
from construct import Struct, Float64b, Int32ub

from packets.packet_meta import PacketMeta

def construct_field(field):
    """
    Decorator that attaches a Construct field to a property.
    """
    def decorator(func):
        func._construct_field = field
        return property(func)
    return decorator

class BasePacket(metaclass=PacketMeta):
    """
    A base class that:
      1) sets a timestamp
      2) requires a packet_type property
      3) automatically generates the Construct schema
    """
    def __init__(self):
        self.timestamp = time.time()

    @property
    def packet_type(self):
        raise NotImplementedError("Subclasses must define packet_type.")

    @classmethod
    def generate_schema(cls):
        # Common header fields first.
        header_fields = [
            ("timestamp", Float64b),
            ("packet_type", Int32ub),
        ]

        # Now add the payload fields in the order recorded by PacketMeta:
        payload_fields = []
        for attr_name in getattr(cls, "__declared_fields_order__", []):
            attr = getattr(cls, attr_name)          # the property
            field = getattr(attr.fget, "_construct_field", None)
            if field:
                payload_fields.append((attr_name, field))

        all_fields = header_fields + payload_fields
        return Struct(*[name / field for name, field in all_fields])

    def to_dict(self):
        # ...
        data = {
            "timestamp": self.timestamp,
            "packet_type": self.packet_type,
        }
        for attr_name in getattr(self.__class__, "__declared_fields_order__", []):
            data[attr_name] = getattr(self, attr_name)
        return data

    def build(self):
        schema = self.generate_schema()
        return schema.build(self.to_dict())

    def parse(self, data):
        schema = self.generate_schema()
        return schema.parse(data)
