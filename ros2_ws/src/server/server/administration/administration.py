# administration/administration.py
import socket
import threading

from utils.logger import logger

LOGGER_PREFIX = "Admin"

class Administration:
    def __init__(self, subsystem_servers, motors, access_manager, host="0.0.0.0", port=6000, admin_password="secret"):
        """
        Administration class for managing sensor servers and client access records.

        Parameters:
          - subsystem_servers: dict mapping sensor types (e.g., "motor", "lidar", "imu", "openmv") to their server instances.
          - motors: list of motor objects (for override commands).
          - access_manager: instance of ClientAccessManager (stores records by IP+port in CSV, merged by IP in listings).
          - host, port: admin TCP server host/port.
          - admin_password: password required for admin access.
        """
        self.servers = subsystem_servers
        self.motors = motors
        self.access_manager = access_manager
        self.host = host
        self.port = port
        self.admin_password = admin_password
        self.running = True

        self.admin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.admin_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.admin_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            # SO_REUSEPORT may not be available on all systems.
            pass
        self.admin_socket.bind((self.host, self.port))
        self.admin_socket.listen(5)

        # This will be updated dynamically when listing active connections.
        # Each active connection is stored as a tuple: (server_type, client_addr, server_instance, client_id)
        self.active_connections = []

    def start(self):
        threading.Thread(target=self._admin_loop, daemon=True).start()

    def _admin_loop(self):
        logger.info(f"Admin server listening on {self.host}:{self.port}", prefix=LOGGER_PREFIX)
        while self.running:
            try:
                client_socket, addr = self.admin_socket.accept()
                logger.debug(f"Admin connected from {addr}", prefix=LOGGER_PREFIX)
                threading.Thread(target=self._handle_admin_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    logger.warning(f"Error accepting admin connection: {e}", prefix=LOGGER_PREFIX)

    def _handle_admin_client(self, client_socket, addr):
        try:
            client_socket.sendall("Enter admin password: ".encode("utf-8"))
            password = client_socket.recv(1024).strip().decode("utf-8")
            if password != self.admin_password:
                client_socket.sendall("Incorrect password. Disconnecting.\n".encode("utf-8"))
                logger.warning(f"Admin connection from {addr} rejected due to bad password.", prefix=LOGGER_PREFIX)
                client_socket.close()
                return

            client_socket.sendall("Welcome, admin. Type 'help' for commands.\n".encode("utf-8"))
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                command = data.decode("utf-8").strip()
                response = self._process_admin_command(command)
                client_socket.sendall((response + "\n").encode("utf-8"))
        except Exception as e:
            logger.warning(f"Error handling admin client from {addr}: {e}", prefix=LOGGER_PREFIX)
        finally:
            logger.debug(f"Admin disconnected from {addr}", prefix=LOGGER_PREFIX)
            client_socket.close()

    def _process_admin_command(self, command):
        parts = command.split()
        if not parts:
            return "No command provided."
        cmd = parts[0].lower()

        # Uniform header for table outputs.
        header = f"{'ID':<4} {'IP':<15} {'Motor':<6} {'Lidar':<6} {'IMU':<6} {'OpenMV':<8} {'Banned':<6}"

        if cmd == "help":
            return (
                "Available commands:\n"
                "lista - List active connections (live connections only).\n"
                "block <server_type> - Block commands from the specified sensor and stop it.\n"
                "unblock <server_type> - Unblock commands from the specified sensor.\n"
                "kill <client_id> - Disconnect the active client with the given CSV client ID.\n"
                "ban <client_id> - Ban the client (by CSV client ID) so its IP is blocked and disconnect it if active.\n"
                "unban <client_id> - Unban the client (by CSV client ID).\n"
                "listb <server_type> - List banned IP addresses for the specified server in a table.\n"
                "list - List all client access records (merged by IP) in a table.\n"
                "set <client_id> <sensor> <value> - Set access for the given client on the sensor (1=access, 0=no access).\n"
                "remove <client_id> - Remove the client record entirely from the access list.\n"
                "stop - Stop all motors immediately.\n"
                "override_motors <value> - Override motor commands with the specified value.\n"
                "\nSensor options: motor, lidar, imu, openmv."
            )

        elif cmd == "lista":
            # List live active connections.
            self.active_connections = []
            lines = [header]
            for key, server in self.servers.items():
                if hasattr(server, "active_client_lock"):
                    with server.active_client_lock:
                        if server.active_client is not None:
                            client_socket, client_addr, cid = server.active_client
                            self.active_connections.append((key, client_addr, server, cid))
                            # Display live connection data with dashes for sensor rights.
                            lines.append(f"{cid:<4} {client_addr[0]:<15} {'-':<6} {'-':<6} {'-':<6} {'-':<8} {'No':<6}")
            if len(lines) == 1:
                return header + "\nNo active connections."
            return "\n".join(lines)

        elif cmd == "list":
            # List all client access records merged by IP (from CSV).
            all_records = self.access_manager.list_clients()
            if not all_records:
                return header + "\nNo client records."
            merged = {}
            for rec in all_records:
                ip = rec["ip"]
                if ip not in merged:
                    merged[ip] = {
                        "client_id": rec["client_id"],
                        "ip": ip,
                        "motor": rec["motor_rights"] if rec["motor_rights"] else "0",
                        "lidar": rec["lidar_rights"] if rec["lidar_rights"] else "0",
                        "imu": rec["imu_rights"] if rec["imu_rights"] else "0",
                        "openmv": rec["openmv_rights"] if rec["openmv_rights"] else "0",
                        "banned": rec["banned"]
                    }
                else:
                    for sensor in ["motor_rights", "lidar_rights", "imu_rights", "openmv_rights"]:
                        key_sensor = sensor.split("_")[0]
                        if rec[sensor] == "1" or merged[ip][key_sensor] == "1":
                            merged[ip][key_sensor] = "1"
                    if rec["banned"]:
                        merged[ip]["banned"] = True
            lines = [header]
            sorted_records = sorted(merged.values(), key=lambda r: int(r["client_id"]))
            for rec in sorted_records:
                banned_str = "Yes" if rec["banned"] else "No"
                line = f"{rec['client_id']:<4} {rec['ip']:<15} {rec['motor']:<6} {rec['lidar']:<6} {rec['imu']:<6} {rec['openmv']:<8} {banned_str:<6}"
                lines.append(line)
            return "\n".join(lines)

        elif cmd == "listb":
            # List banned client records (from CSV) merged by IP for a given server.
            if len(parts) < 2:
                return "Usage: listb <server_type>"
            server_type = parts[1].lower()
            if server_type not in self.servers:
                return f"Server type '{server_type}' not found."
            all_records = self.access_manager.list_clients()
            banned_records = [rec for rec in all_records if rec["banned"]]
            if not banned_records:
                return header + "\nNo banned clients."
            merged = {}
            for rec in banned_records:
                ip = rec["ip"]
                if ip not in merged:
                    merged[ip] = {
                        "client_id": rec["client_id"],
                        "ip": ip,
                        "motor": rec["motor_rights"] if rec["motor_rights"] else "0",
                        "lidar": rec["lidar_rights"] if rec["lidar_rights"] else "0",
                        "imu": rec["imu_rights"] if rec["imu_rights"] else "0",
                        "openmv": rec["openmv_rights"] if rec["openmv_rights"] else "0",
                        "banned": True
                    }
                else:
                    for sensor in ["motor_rights", "lidar_rights", "imu_rights", "openmv_rights"]:
                        key_sensor = sensor.split("_")[0]
                        if rec[sensor] == "1" or merged[ip][key_sensor] == "1":
                            merged[ip][key_sensor] = "1"
            lines = [header]
            sorted_records = sorted(merged.values(), key=lambda r: int(r["client_id"]))
            for rec in sorted_records:
                line = f"{rec['client_id']:<4} {rec['ip']:<15} {rec['motor']:<6} {rec['lidar']:<6} {rec['imu']:<6} {rec['openmv']:<8} {'Yes':<6}"
                lines.append(line)
            return "\n".join(lines)

        elif cmd == "block":
            if len(parts) < 2:
                return "Usage: block <server_type>"
            server_type = parts[1].lower()
            if server_type in self.servers:
                self.servers[server_type].block_client = True
                if server_type == "motor":
                    for motor in self.motors:
                        motor.control(0)
                return f"Blocked {server_type} sensor commands."
            else:
                return f"Server type '{server_type}' not found."

        elif cmd == "unblock":
            if len(parts) < 2:
                return "Usage: unblock <server_type>"
            server_type = parts[1].lower()
            if server_type in self.servers:
                self.servers[server_type].block_client = False
                return f"Unblocked {server_type} sensor commands."
            else:
                return f"Server type '{server_type}' not found."

        elif cmd == "kill":
            # Kill an active client by CSV client ID.
            if len(parts) < 2:
                return "Usage: kill <client_id>"
            try:
                target_id = int(parts[1])
            except:
                return "Invalid client ID."
            found = False
            for key, client_addr, server, cid in self.active_connections:
                if cid == target_id:
                    with server.active_client_lock:
                        if server.active_client is not None:
                            client_socket, addr, _ = server.active_client
                            try:
                                client_socket.sendall("You have been disconnected by the admin.\n".encode("utf-8"))
                            except:
                                pass
                            client_socket.close()
                            server.active_client = None
                            found = True
                            if key == "motor":
                                for motor in self.motors:
                                    motor.control(0)
                            return f"Killed active client with ID {target_id}."
            if not found:
                return f"No active client with ID {target_id} found."

        elif cmd == "ban":
            # Ban a client by CSV client ID.
            if len(parts) < 2:
                return "Usage: ban <client_id>"
            try:
                client_id = int(parts[1])
            except:
                return "Invalid client ID."
            record = self.access_manager.get_record_by_id(client_id)
            if not record:
                return f"Client ID {client_id} not found."
            banned_ip = record["ip"]
            if not self.access_manager.ban_client(client_id):
                return f"Failed to ban client ID {client_id}."
            for key, server in self.servers.items():
                server.blocked_clients.add(banned_ip)
                with server.active_client_lock:
                    if server.active_client is not None:
                        client_socket, addr, cid = server.active_client
                        if cid == client_id or addr[0] == banned_ip:
                            try:
                                client_socket.sendall("You have been banned by the admin.\n".encode("utf-8"))
                            except:
                                pass
                            client_socket.close()
                            server.active_client = None
                if key == "motor":
                    for motor in self.motors:
                        motor.control(0)
            return f"Banned client ID {client_id} with IP {banned_ip}."

        elif cmd == "unban":
            # Unban a client by CSV client ID.
            if len(parts) < 2:
                return "Usage: unban <client_id>"
            try:
                client_id = int(parts[1])
            except:
                return "Invalid client ID."
            record = self.access_manager.get_record_by_id(client_id)
            if not record:
                return f"Client ID {client_id} not found."
            ip_to_unban = record["ip"]
            if self.access_manager.unban_client(client_id):
                for key, server in self.servers.items():
                    if ip_to_unban in server.blocked_clients:
                        server.blocked_clients.remove(ip_to_unban)
                return f"Unbanned client ID {client_id} with IP {ip_to_unban}."
            else:
                return f"Failed to unban client ID {client_id}."

        elif cmd == "set":
            # set <client_id> <sensor> <value>
            if len(parts) < 4:
                return "Usage: set <client_id> <sensor> <value>"
            try:
                client_id = int(parts[1])
            except:
                return "Invalid client ID."
            sensor = parts[2].lower()
            value = parts[3]
            if value not in ("0", "1"):
                return "Value must be 0 (no access) or 1 (access)."
            if sensor not in ["motor", "lidar", "imu", "openmv"]:
                return "Sensor must be one of: motor, lidar, imu, openmv."
            if self.access_manager.set_access(client_id, sensor, value):
                return f"Set access for client {client_id} on sensor {sensor} to {value}."
            else:
                return f"Failed to set access for client {client_id}."

        elif cmd == "remove":
            # remove <client_id> removes the entire record.
            if len(parts) < 2:
                return "Usage: remove <client_id>"
            try:
                client_id = int(parts[1])
            except:
                return "Invalid client ID."
            if self.access_manager.remove_client(client_id):
                return f"Removed client record for client {client_id}."
            else:
                return f"Failed to remove client record for client {client_id}."

        elif cmd == "stop":
            for motor in self.motors:
                motor.control(0)
            return "All motors have been stopped (set to neutral/0)."

        elif cmd == "override_motors":
            if len(parts) < 2:
                return "Usage: override_motors <value>"
            try:
                value = float(parts[1])
                for motor in self.motors:
                    motor.control(value)
                return f"Motor commands overridden with value {value}."
            except Exception as e:
                return f"Error parsing value: {e}"
        else:
            return "Unknown command. Type 'help' for a list of commands."

    def stop(self):
        self.running = False
        self.admin_socket.close()
