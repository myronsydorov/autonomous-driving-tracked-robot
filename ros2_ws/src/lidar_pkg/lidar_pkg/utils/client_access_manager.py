import csv
import os

class ClientAccessManager:
    def __init__(self, filename="client_access.csv"):
        self.filename = filename
        self.clients = {}  # key: client_id (int), value: record (dict)
        self.next_id = 1
        # If file does not exist, create it with a header.
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["client_id", "ip", "port", "motor_rights", "lidar_rights", "imu_rights", "openmv_rights", "banned"])
        self.load_data()

    def load_data(self):
        """Load client records from the CSV file."""
        self.clients = {}
        with open(self.filename, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    client_id = int(row["client_id"])
                except ValueError:
                    continue
                self.clients[client_id] = {
                    "client_id": client_id,
                    "ip": row["ip"],
                    "port": row["port"],  # Stored as string for consistency
                    "motor_rights": row["motor_rights"],
                    "lidar_rights": row["lidar_rights"],
                    "imu_rights": row["imu_rights"],
                    "openmv_rights": row["openmv_rights"],
                    "banned": row["banned"].strip().lower() == "true"
                }
                if client_id >= self.next_id:
                    self.next_id = client_id + 1

    def save_data(self):
        """Write all client records to the CSV file."""
        with open(self.filename, "w", newline="") as csvfile:
            fieldnames = ["client_id", "ip", "port", "motor_rights", "lidar_rights", "imu_rights", "openmv_rights", "banned"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for client_id in sorted(self.clients.keys()):
                record = self.clients[client_id]
                writer.writerow({
                    "client_id": record["client_id"],
                    "ip": record["ip"],
                    "port": record["port"],
                    "motor_rights": record["motor_rights"],
                    "lidar_rights": record["lidar_rights"],
                    "imu_rights": record["imu_rights"],
                    "openmv_rights": record["openmv_rights"],
                    "banned": "True" if record["banned"] else "False"
                })

    def get_client(self, ip, port):
        # Look for an existing record by IP only.
        for cid, rec in self.clients.items():
            if rec["ip"] == ip:
                return cid, rec
        # No record found, so create a new one with default rights granted ("1").
        client_id = self.next_id
        self.next_id += 1
        new_record = {
            "client_id": client_id,
            "ip": ip,
            "port": str(port),  # record the first port used (for reference)
            "motor_rights": "1",   # default granted
            "lidar_rights": "1",
            "imu_rights": "1",
            "openmv_rights": "1",
            "banned": False
        }
        self.clients[client_id] = new_record
        self.save_data()
        return client_id, new_record

    def list_clients(self):
        """Return a list of all client records (as dictionaries). Reloads CSV to include latest changes."""
        self.load_data()
        return list(self.clients.values())

    def get_record_by_id(self, client_id):
        """Return the record for a given client_id, or None if not found."""
        try:
            client_id = int(client_id)
        except ValueError:
            return None
        self.load_data()
        return self.clients.get(client_id)

    def set_access(self, client_id, sensor, value):
        """
        Set access for a given client by client_id on the specified sensor.
        Sensor should be one of: "motor", "lidar", "imu", "openmv".
        Value should be "1" (allowed) or "0" (not allowed).
        """
        try:
            client_id = int(client_id)
        except ValueError:
            return False
        sensor_field = sensor.lower() + "_rights"
        if sensor_field not in ["motor_rights", "lidar_rights", "imu_rights", "openmv_rights"]:
            return False
        if client_id not in self.clients:
            return False
        self.clients[client_id][sensor_field] = value
        self.save_data()
        return True

    def remove_client(self, client_id):
        """Remove the entire client record from the CSV."""
        try:
            client_id = int(client_id)
        except ValueError:
            return False
        if client_id in self.clients:
            del self.clients[client_id]
            self.save_data()
            return True
        return False

    def ban_client(self, client_id):
        """Mark the client as banned in the CSV."""
        try:
            client_id = int(client_id)
        except ValueError:
            return False
        if client_id in self.clients:
            self.clients[client_id]["banned"] = True
            self.save_data()
            return True
        return False

    def unban_client(self, client_id):
        """Mark the client as not banned in the CSV."""
        try:
            client_id = int(client_id)
        except ValueError:
            return False
        if client_id in self.clients:
            self.clients[client_id]["banned"] = False
            self.save_data()
            return True
        return False
