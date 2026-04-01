# motors/motor.py

import time
import threading
from periphery import PWM
from utils.logger import logger

# PWM settings
FREQ_HZ = 50.0                  # 50 Hz frame (20 ms) – standard for servos/ESCs
FORWARD_PULSE = 2000e-6         # 2000 µs
NEUTRAL_PULSE = 1500e-6         # 1500 µs
REVERSE_PULSE = 1000e-6         # 1000 µs

LOGGER_PREFIX = "Motor"


class Motor:
    def __init__(self, pwm_chip: str, pwm_channel: int):
        """
        pwm_chip: e.g. "/sys/class/pwm/pwmchip2"
        pwm_channel: channel number (0 or 1 for GPIO18/19)
        """
        # Open and start PWM
        self.pwm = PWM(pwm_chip, pwm_channel)
        self.pwm.frequency = FREQ_HZ
        self.pwm.enable()

        # State
        self.current_command = 0.0
        self.target_command = 0.0
        self.lock = threading.Lock()
        self.stop_thread = False

        # Initialize at neutral
        self.pwm.duty_cycle = NEUTRAL_PULSE * FREQ_HZ

        # Start background control loop
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def compute_pulse(self, command: float) -> float:
        """Return the pulse width in seconds for a given –1..1 command."""
        if command > 0:
            return NEUTRAL_PULSE + (FORWARD_PULSE - NEUTRAL_PULSE) * command
        elif command < 0:
            return NEUTRAL_PULSE + (REVERSE_PULSE - NEUTRAL_PULSE) * abs(command)
        else:
            return NEUTRAL_PULSE

    def _double_click_switch(self, new_command: float):
        """Safe polarity flip: neutral → target → neutral → target."""
        target = self.compute_pulse(new_command)
        for pulse in (NEUTRAL_PULSE, target, NEUTRAL_PULSE, target):
            self.pwm.duty_cycle = pulse * FREQ_HZ
            time.sleep(0.1)

    def _run(self):
        """Daemon loop: smooth updates and double-click on direction change."""
        time.sleep(0.5)  # allow hardware to settle
        while not self.stop_thread:
            with self.lock:
                new_cmd = self.target_command
            if new_cmd != self.current_command:
                # detect forward↔reverse transition
                if (new_cmd < 0.0 <= self.current_command) or (new_cmd > 0.0 > self.current_command):
                    logger.debug(
                        f"PWM {self.pwm.chip}:{self.pwm.channel} switching "
                        f"{self.current_command}→{new_cmd} (double-click)",
                        prefix=LOGGER_PREFIX
                    )
                    self._double_click_switch(new_cmd)
                else:
                    pulse = self.compute_pulse(new_cmd)
                    logger.debug(
                        f"PWM {self.pwm.chip}:{self.pwm.channel} set "
                        f"{pulse*1e6:.0f} µs ({new_cmd})",
                        prefix=LOGGER_PREFIX
                    )
                    self.pwm.duty_cycle = pulse * FREQ_HZ
                self.current_command = new_cmd
            time.sleep(0.05)

    def control(self, command: float):
        """Set new target in [−1.0, 1.0]."""
        with self.lock:
            # clamp
            self.target_command = max(-1.0, min(1.0, command))

    def cleanup(self):
        """Stop loop and shut down PWM cleanly."""
        self.stop_thread = True
        self.thread.join()
        self.pwm.duty_cycle = 0.0
        self.pwm.disable()
        self.pwm.close()
