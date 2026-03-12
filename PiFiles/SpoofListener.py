import socket
import json
import time
from powerCalc import calculate_power
from spoof_power_ble import BLECyclingPower
import bluetooth

SERVER_IP = "192.168.4.225"
SERVER_PORT = 9000

# --- Initialize BLE ---
ble = bluetooth.BLE()
cps = BLECyclingPower(ble, name="PowerMeter")
def cleanup():
    print("Cleaning up Bluetooth...")
    ble.active(False)
    print("Bluetooth turned off.")
# --- Listener function ---
def listen(weight=75):
    last_point = None
    last_power = 0
    last_send_time = 0

    s = socket.socket()
    s.connect((SERVER_IP, SERVER_PORT))
    buf = b""

    while True:
        # --- Receive data from TCP ---
        data = s.recv(64)
        if not data:
            break
        buf += data

        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue

            try:
                point = json.loads(line.decode())
                print("GPS:", point)

                # --- Calculate power ---
                if last_point:
                    power = calculate_power(weight, last_point, point)
                    last_power = round(power, 1)
                    print("Power:", last_power, "W")

                last_point = point

            except Exception as e:
                print("⚠️ Parse error:", e)

        # --- Broadcast power over BLE at 1 Hz ---
        now = time.time()
        if now - last_send_time >= 1:
            cps.send_spoofed_power(int(last_power))
            last_send_time = now

        time.sleep(0.01)  # small delay to reduce CPU load
