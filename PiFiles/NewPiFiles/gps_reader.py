import time
from machine import UART
from utils import nmea_to_decimal, calculate_power
from config import UART_PORT, UART_BAUDRATE, UART_TX, UART_RX, WEIGHT

class GPSReader:
    def __init__(self, cps):
        self.cps = cps
        self.last_point = None
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        uart = UART(UART_PORT, baudrate=UART_BAUDRATE, tx=UART_TX, rx=UART_RX, timeout=1000)
        print("GPS thread started...")
        while self._running:
            power = 0  # Default power if GPS fix is unavailable
            line = uart.readline()
            if line:
                try:
                    decoded = line.decode('ascii').strip()
                    if decoded.startswith("$GNRMC"):
                        parts = decoded.split(',')
                        if len(parts) > 6 and parts[2] == 'A':  # valid fix
                            p = {
                                "lat": nmea_to_decimal(parts[3], parts[4]),
                                "lon": nmea_to_decimal(parts[5], parts[6]),
                                "elevation": 0,
                                "dt": 1
                            }
                            if self.last_point:
                                power = calculate_power(WEIGHT, self.last_point, p)
                            self.last_point = p
                except Exception:
                    pass

            # Always send power (0 if no valid GPS fix)
            self.cps.send_power(power)
            time.sleep(1)  # Send every second
