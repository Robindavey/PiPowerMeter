
import time
from powerCalc import calculate_power
from spoof_power_ble import BLECyclingPower
import bluetooth


# --- Initialize BLE ---
# Initialize BLE
ble = bluetooth.BLE()
cps = BLECyclingPower(ble, name="PowerMeter")

print("Starting spoofed power broadcast...")

try:
    while True:
        cps.send_spoofed_power(190)
        time.sleep(1.0)  # 1 Hz
except KeyboardInterrupt:
    print("Stopped broadcasting")
