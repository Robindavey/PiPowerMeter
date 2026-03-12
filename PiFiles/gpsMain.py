from machine import UART
import bluetooth
import struct
import time
import network
import _thread
import math
import random

# --- Power calculation functions ---
def haversine_3d(p1, p2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, [p1["lat"], p1["lon"], p2["lat"], p2["lon"]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    d2d = 2*R*math.asin(math.sqrt(a))
    dz = (p2.get("elevation") or 0) - (p1.get("elevation") or 0)
    return (d2d**2 + dz**2) ** 0.5

def calculate_power(weight, p1, p2):
    g = 9.81
    Crr = 0.005
    rho = 1.225
    CdA = 0.3

    dt = p2.get("dt", 1)
    if dt <= 0: 
        return 0

    d = haversine_3d(p1, p2)
    v = d / dt
    elev_gain = (p2.get("elevation") or 0) - (p1.get("elevation") or 0)
    slope = elev_gain / d if d > 0 else 0

    P_gravity = weight * g * v * slope
    P_roll = weight * g * Crr * v
    P_aero = 0.5 * rho * CdA * v**3

    return max(0, P_gravity + P_roll + P_aero)

# --- Disable WiFi for BLE ---
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
ap = network.WLAN(network.AP_IF)
ap.active(False)
print("WiFi disabled to avoid BLE interference.")

# --- BLE Cycling Power Service ---
_CPS_UUID = bluetooth.UUID(0x1818)
_POWER_MEASUREMENT = (bluetooth.UUID(0x2A63), bluetooth.FLAG_NOTIFY,)
_CPS_FEATURE = (bluetooth.UUID(0x2A65), bluetooth.FLAG_READ,)
_SENSOR_LOCATION = (bluetooth.UUID(0x2A5D), bluetooth.FLAG_READ,)
_CPS_SERVICE = (_CPS_UUID, (_POWER_MEASUREMENT, _CPS_FEATURE, _SENSOR_LOCATION),)

class BLECyclingPower:
    def __init__(self, ble, name="PowerMeter"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        try:
            self._cps_handles = self._ble.gatts_register_services((_CPS_SERVICE,))[0]
            self._ble.gatts_write(self._cps_handles[1], struct.pack("<I", 0x20))
            self._ble.gatts_write(self._cps_handles[2], struct.pack("<B", 13))
            print("CPS service registered:", self._cps_handles)
        except Exception as e:
            print("Failed to register CPS service:", e)

        self._connections = set()
        self._sequence_number = 0
        self._crank_revolutions = 0
        self._last_crank_event_time = 0
        self._advertise(name)

    def _irq(self, event, data):
        if event == 1:  # Connected
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("Connected to:", conn_handle)
        elif event == 2:  # Disconnected
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self._advertise()
            print("Disconnected from:", conn_handle)
        elif event == 21:  # MTU exchanged
            conn_handle, mtu = data
            print(f"MTU exchanged for {conn_handle}: mtu={mtu}")

    def _advertise(self, name="PowerMeter"):
        adv = bytearray([0x02, 0x01, 0x06, 0x03, 0x03, 0x18, 0x18])
        adv += bytearray([len(name)+1, 0x09]) + name.encode()
        try:
            self._ble.gap_advertise(100_000, adv)
            print("BLE advertising as", name)
        except Exception as e:
            print("Advertising failed:", e)

    def send_power(self, power):
        self._sequence_number = (self._sequence_number + 1) % 256
        self._crank_revolutions = (self._crank_revolutions + 1) % 65536
        self._last_crank_event_time = (self._last_crank_event_time + 1024) % 65536

        payload = struct.pack("<HhHH", 0x0020, int(power), self._crank_revolutions, self._last_crank_event_time)

        if self._connections:
            for conn in self._connections:
                try:
                    self._ble.gatts_notify(conn, self._cps_handles[0], payload)
                    print(f"Sent {int(power)} W to {conn}")
                    time.sleep_ms(10)
                except OSError as e:
                    print("Notify failed:", e)
        else:
            print("No BLE connection, skipping notify")

# --- GPS Reading Thread ---
last_point = None
weight = 75  # kg, adjust as needed

def nmea_to_decimal(coord, direction):
    if not coord:
        return None
    deg = int(float(coord)/100)
    minutes = float(coord) - deg*100
    dec = deg + minutes/60
    if direction in ['S','W']:
        dec *= -1
    return round(dec, 6)

def gps_reader(cps):
    global last_point
    uart = UART(1, baudrate=9600, tx=4, rx=5, timeout=1000)
    print("GPS thread started...")
    while True:
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
                        if last_point:
                            power = calculate_power(weight, last_point, p)
                        else:
                            power = 0
                        last_point = p
                        cps.send_power(power)
                        print(f"Lat: {p['lat']}, Lon: {p['lon']}, Power: {int(power)} W")
            except Exception as e:
                print("GPS decode error:", e)
        time.sleep(0.1)

# --- Main --- 
def main():
    ble = bluetooth.BLE()
    cps = BLECyclingPower(ble)
    _thread.start_new_thread(gps_reader, (cps,))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        stop_threads = True
        time.sleep(1)
        cps.cleanup()
        print("Exited cleanly.")

if __name__ == "__main__":
    main()

