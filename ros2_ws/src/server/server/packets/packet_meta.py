class PacketMeta(type):
    """
    A metaclass that records @construct_field properties
    in the exact order they were declared in the class body.
    """
    def __new__(mcs, name, bases, namespace):
        # We'll collect property names that have _construct_field in the same order as they are declared
        declared_fields = []
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, property) and hasattr(attr_value.fget, "_construct_field"):
                declared_fields.append(attr_name)

        # Create the class the usual way.
        cls = super().__new__(mcs, name, bases, namespace)

        # Store the ordered property names on the class itself:
        cls.__declared_fields_order__ = declared_fields
        return cls