import bluetooth
import struct
import random
import time
import network

# Disable WiFi to prevent BLE interference
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
ap = network.WLAN(network.AP_IF)
ap.active(False)
print("WiFi disabled to avoid BLE interference.")

# --- BLE UUIDs ---
_CPS_UUID = bluetooth.UUID(0x1818)  # Cycling Power Service
_POWER_MEASUREMENT = (bluetooth.UUID(0x2A63), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
_CPS_FEATURE = (bluetooth.UUID(0x2A65), bluetooth.FLAG_READ,)
_SENSOR_LOCATION = (bluetooth.UUID(0x2A5D), bluetooth.FLAG_READ,)
_CPS_SERVICE = (_CPS_UUID, (_POWER_MEASUREMENT, _CPS_FEATURE, _SENSOR_LOCATION),)


class BLECyclingPower:
    def __init__(self, ble, name="PowerMeter"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        # Register CPS Service
        try:
            cps_services = self._ble.gatts_register_services((_CPS_SERVICE,))
            self._cps_handles = cps_services[0]  # (Measurement, Feature, Location)
            print("CPS service registered:", self._cps_handles)
        except Exception as e:
            print("Failed to register CPS service:", e)

        # CPS Feature: Crank Rev (bit 5)
        features = 0x00000020
        self._ble.gatts_write(self._cps_handles[1], struct.pack("<I", features))

        # Sensor Location: 13 = Left Crank
        self._ble.gatts_write(self._cps_handles[2], struct.pack("<B", 13))

        self._connections = set()
        self._sequence_number = 0
        self._crank_revolutions = 0
        self._last_crank_event_time = 0  # 1/1024 s
        self._advertise(name)

    # --- BLE IRQ handler ---
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
        elif event == 3:  # GATT write
            conn_handle, value_handle, data = data
            print(f"Write to {value_handle} from {conn_handle}: {data}")
        elif event == 4:  # GATT read request
            conn_handle, value_handle = data
            print(f"Read request for {value_handle} from {conn_handle}")
        elif event == 20:  # GATTS indicate done
            conn_handle, value_handle, status = data
            char = "Unknown"
            if value_handle == self._cps_handles[0]:
                char = "Power Measurement (0x2A63)"
            print(f"Indicate done for {conn_handle}: {char}, status={status}")
        elif event == 21:  # MTU exchanged
            conn_handle, mtu = data
            print(f"MTU exchanged for {conn_handle}: mtu={mtu}")
        else:
            print(f"Unhandled IRQ event: {event}, data: {data}")

    # --- Advertising ---
    def _advertise(self, name="PowerMeter"):
        adv = bytearray([0x02, 0x01, 0x06])           # Flags: LE General Discoverable
        adv += bytearray([0x03, 0x03, 0x18, 0x18])    # CPS UUID
        adv += bytearray([0x07, 0x16, 0x18, 0x18, 0x00, 0x00, 0x64, 0x00])  # CPS Service Data
        adv += bytearray([0x03, 0x19, 0x84, 0x04])    # Appearance: Cycling Power Sensor
        adv += bytearray([len(name)+1, 0x09]) + name.encode()  # Name
        scan_resp = bytearray([len(name)+1, 0x08]) + name.encode()
        try:
            self._ble.gap_advertise(100_000, adv, resp_data=scan_resp)
            print("🔵 BLE advertising as", name)
        except Exception as e:
            print("Advertising failed:", e)

    # --- Send spoofed power ---
    def send_power(self, instantaneous_power):
        self._sequence_number = (self._sequence_number + 1) % 256
        self._crank_revolutions = (self._crank_revolutions + 1) % 65536
        delta_time = int(1.0 * 1024)  # 1s in 1/1024 s
        self._last_crank_event_time = (self._last_crank_event_time + delta_time) % 65536

        flags = 0x0020
        cps_payload = struct.pack(
            "<HhHH",
            flags,
            instantaneous_power,
            self._crank_revolutions,
            self._last_crank_event_time
        )

        if self._connections:
            for conn_handle in self._connections:
                try:
                    self._ble.gatts_notify(conn_handle, self._cps_handles[0], cps_payload)
                    print(
                        f"Sent to {conn_handle}: Seq: {self._sequence_number} | "
                        f"Power: {instantaneous_power} W | Cadence: ~80 rpm"
                    )
                    time.sleep_ms(10)
                except OSError as e:
                    print(f"Failed to notify {conn_handle}: {e}")
        else:
            print("No connections, skipping notify")

    # --- Cleanup BLE ---
    def cleanup(self):
        print("Cleaning up Bluetooth...")
        self._ble.active(False)
        print("Bluetooth turned off.")
