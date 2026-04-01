# motors/motor_tcp_server.py

import socket
import threading
import time
import select

from utils.logger import logger

LOGGER_PREFIX = "Motor"

# Dummy Motor-Klasse für lokalen Test
class DummyMotor:
    def __init__(self, motor_id):
        self.motor_id = motor_id

    def control(self, value):
        print(f"[DUMMY MOTOR {self.motor_id}] Steuerwert gesetzt auf: {value}")


class MotorTCPServer:
    def __init__(self, motors, access_manager, host="0.0.0.0", port=6003):
        """
        TCP server for receiving motor control commands.
        Only one client is allowed at a time.
        Uses a ClientAccessManager to check client permissions by IP and port.
        For the motor server, the client must have "1" in motor_rights.
        """
        self.motors = motors
        self.access_manager = access_manager
        self.host = host
        self.port = port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.running = True

        # Track the active client as (client_socket, addr, client_id)
        self.active_client_lock = threading.Lock()
        self.active_client = None

        # Banned clients: set of IP strings (only the IP is used for banning)
        self.blocked_clients = set()

        # Flag to block commands (for admin override)
        self.block_client = False

        # Override value: if not None, then admin override is active.
        self.override_value = None

    def set_override(self, value):
        """Set an override value that will ignore client commands."""
        self.override_value = value
        self.block_client = True
        # Immediately set motors to override value.
        for motor in self.motors:
            motor.control(value)

    def clear_override(self):
        """Clear any admin override so that client commands are processed."""
        self.override_value = None
        self.block_client = False

    def start(self):
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def _accept_clients(self):
        logger.info(f"Motor TCP Server listening on {self.host}:{self.port}", prefix=LOGGER_PREFIX)
        while self.running:
            try:
                client_socket, addr = self.server.accept()
                client_ip = addr[0]
                client_id, client_info = self.access_manager.get_client(client_ip, addr[1])
                client_info = self.access_manager.get_record_by_id(client_id)
                logger.debug(f"Client record for {client_ip}:{addr[1]} (ID {client_id}): {client_info}", prefix=LOGGER_PREFIX)

                # Banned?
                if client_ip in self.blocked_clients:
                    logger.debug(f"Rejected banned client {client_id} from {addr}", prefix=LOGGER_PREFIX)
                    try:
                        client_socket.sendall("Your connection is banned by the admin.\n".encode("utf-8"))
                    except Exception as e:
                        logger.warning(f"Error sending banned message to {client_id}: {e}", prefix=LOGGER_PREFIX)
                    client_socket.close()
                    continue

                # Rechte prüfen
                if client_info["motor_rights"] != "1":
                    logger.debug(f"Access denied for client {client_id} from {addr} (motor_rights = {client_info['motor_rights']})", prefix=LOGGER_PREFIX)
                    try:
                        client_socket.sendall("Access denied: You do not have permission to control the motors.\n".encode("utf-8"))
                    except Exception as e:
                        logger.warning(f"Error sending access denied message to {client_id}: {e}", prefix=LOGGER_PREFIX)
                    client_socket.close()
                    continue

                # Nur ein Client gleichzeitig
                with self.active_client_lock:
                    if self.active_client is None:
                        logger.debug(f"Accepted motor client {client_id} from {addr}", prefix=LOGGER_PREFIX)
                        self.active_client = (client_socket, addr, client_id)
                        threading.Thread(
                            target=self._handle_client,
                            args=(client_socket, addr, client_id),
                            daemon=True
                        ).start()
                    else:
                        logger.debug(f"Rejected motor client {client_id} from {addr} because another client is active", prefix=LOGGER_PREFIX)
                        try:
                            client_socket.sendall("Server busy. Only one client allowed at a time. Please try later.\n".encode("utf-8"))
                        except Exception as e:
                            logger.warning(f"Error sending busy message to {client_id}: {e}", prefix=LOGGER_PREFIX)
                        client_socket.close()

            except Exception as e:
                if self.running:
                    logger.warning(f"Error accepting motor client: {e}", prefix=LOGGER_PREFIX)

    def _handle_client(self, client_socket, addr, client_id):
        try:
            client_socket.sendall("You are now connected and in control of the motors.\n".encode("utf-8"))
            # Timestamp des letzten erfolgreichen Befehls
            last_recv = time.time()

            while True:
                # Admin-Override?
                if self.override_value is not None:
                    for motor in self.motors:
                        motor.control(self.override_value)
                    time.sleep(0.1)
                    continue

                # Zugriffsrechte aktuell prüfen
                record = self.access_manager.get_record_by_id(client_id)
                if record is None or record["motor_rights"] != "1":
                    try:
                        client_socket.sendall("Your access has been revoked. Disconnecting...\n".encode("utf-8"))
                    except Exception as e:
                        logger.warning(f"Error sending revocation message to {client_id}: {e}", prefix=LOGGER_PREFIX)
                    break

                # Auf Daten warten – Timeout = 1 s
                ready, _, _ = select.select([client_socket], [], [], 1.0)
                if not ready:
                    # Keine Daten in 1 s → Stop-Failsafe
                    for m in self.motors:
                        m.control(0)
                    # bleibt in Loop und wartet weiter
                    continue

                # Daten da → verarbeiten
                data = client_socket.recv(1024)
                if not data:
                    logger.debug(f"Motor client {client_id} disconnected: {addr}", prefix=LOGGER_PREFIX)
                    break

                last_recv = time.time()
                command_str = data.decode("utf-8").strip()
                logger.debug(f"Received motor command from client {client_id} {addr}: {command_str}", prefix=LOGGER_PREFIX)

                if self.block_client:
                    # Admin hat Befehle blockiert
                    continue

                if command_str.lower() == "stop":
                    for motor in self.motors:
                        motor.control(0)
                else:
                    try:
                        parts = command_str[4:].split(",")
                        if len(parts) != 2:
                            raise ValueError("Invalid motor set command format.")
                        left_speed = float(parts[0])
                        right_speed = float(parts[1])
                        self.motors[0].control(left_speed)
                        self.motors[1].control(right_speed)
                    except Exception as e:
                        logger.warning(f"Error processing motor command from client {client_id} {addr}: {e}", prefix=LOGGER_PREFIX)

        except Exception as e:
            logger.warning(f"Error handling motor client {client_id} {addr}: {e}", prefix=LOGGER_PREFIX)

        finally:
            logger.debug(f"Ending motor client session for client {client_id} {addr} and stopping motors.", prefix=LOGGER_PREFIX)
            for motor in self.motors:
                motor.control(0)
            client_socket.close()
            with self.active_client_lock:
                self.active_client = None

    def stop(self):
        self.running = False
        self.server.close()
