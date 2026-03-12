# MicroPython BLE Cycling Power Service (CPS)
# Compatible with Zwift, Wahoo Fitness, and ELEMNT/BOLT V2
# Author: GPT-5 (2025-10)

import bluetooth
import struct
import time
import random
import network


# ---------------------------------------------------------------------------
#  Disable Wi-Fi (prevents BLE interference on ESP32 and similar)
# ---------------------------------------------------------------------------
def disable_wifi():
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(False)
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        print("Wi-Fi disabled to avoid BLE interference.")
    except Exception as e:
        print("Wi-Fi disable failed:", e)


# ---------------------------------------------------------------------------
#  BLE Cycling Power Service implementation
# ---------------------------------------------------------------------------
class BLECyclingPower:
    def __init__(self, ble, name="PowerMeter"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._connections = set()
        self._crank_revs = 0
        self._event_time = 0
        self._name = name  # Store the name so we can re-advertise with it

        # --- CPS Service (simple, like working version) ---
        _CPS_UUID = bluetooth.UUID(0x1818)
        _POWER_MEASUREMENT = (bluetooth.UUID(0x2A63), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
        _CPS_FEATURE = (bluetooth.UUID(0x2A65), bluetooth.FLAG_READ,)
        _SENSOR_LOCATION = (bluetooth.UUID(0x2A5D), bluetooth.FLAG_READ,)
        _CPS_SERVICE = (_CPS_UUID, (_POWER_MEASUREMENT, _CPS_FEATURE, _SENSOR_LOCATION),)

        # --- Device Information Service ---
        _DIS_UUID = bluetooth.UUID(0x180A)
        _MFR_NAME = (bluetooth.UUID(0x2A29), bluetooth.FLAG_READ,)
        _MODEL_NUMBER = (bluetooth.UUID(0x2A24), bluetooth.FLAG_READ,)
        _SERIAL_NUMBER = (bluetooth.UUID(0x2A25), bluetooth.FLAG_READ,)
        _FW_REVISION = (bluetooth.UUID(0x2A26), bluetooth.FLAG_READ,)
        _HW_REVISION = (bluetooth.UUID(0x2A27), bluetooth.FLAG_READ,)
        _DIS_SERVICE = (_DIS_UUID, (_MFR_NAME, _MODEL_NUMBER, _SERIAL_NUMBER, _FW_REVISION, _HW_REVISION),)

        # --- Battery Service (required by many cycling computers) ---
        _BATTERY_UUID = bluetooth.UUID(0x180F)
        _BATTERY_LEVEL = (bluetooth.UUID(0x2A19), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
        _BATTERY_SERVICE = (_BATTERY_UUID, (_BATTERY_LEVEL,),)

        # Register all services
        try:
            services = self._ble.gatts_register_services((_CPS_SERVICE, _DIS_SERVICE, _BATTERY_SERVICE))
            self._cps_handles = services[0]  # (Measurement, Feature, Location)
            self._dis_handles = services[1]  # (Mfr, Model, Serial, FW, HW)
            self._bat_handle = services[2][0]  # Battery Level
            print("✅ CPS service registered, handles:", self._cps_handles)
            print("✅ DIS service registered, handles:", self._dis_handles)
            print("✅ Battery service registered, handle:", self._bat_handle)
        except Exception as e:
            print("❌ Service registration failed:", e)
            raise

        # Write CPS Feature: realistic Stages-like feature mask (bit5 + bit17)
        self._ble.gatts_write(self._cps_handles[1], struct.pack("<I", 0x00020020))

        # Write Sensor Location: 13 = Left Crank
        self._ble.gatts_write(self._cps_handles[2], struct.pack("<B", 13))


        # Write Device Information - match real Stages exactly
        self._ble.gatts_write(self._dis_handles[0], b"Stages Cycling")
        self._ble.gatts_write(self._dis_handles[1], b"Stages Power L")
        self._ble.gatts_write(self._dis_handles[2], b"AG12345678")  # Stages serial format
        self._ble.gatts_write(self._dis_handles[3], b"3.1.25")
        self._ble.gatts_write(self._dis_handles[4], b"3.0")
        print("✅ Device Information set (spoofed as Stages)")
        
        # Write Battery Level: 85%
        self._ble.gatts_write(self._bat_handle, struct.pack("<B", 85))
        print("✅ Battery level set to 85%")

        # Start advertising
        self._advertise(name)

    # -----------------------------------------------------------------------
    #  BLE event handler
    # -----------------------------------------------------------------------
    def _irq(self, event, data):
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            conn, _, _ = data
            self._connections.add(conn)
            print("Connected:", conn)

        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            conn, _, _ = data
            self._connections.discard(conn)
            print("Disconnected:", conn)
            self._advertise(self._name)  # Re-advertise with the same name

        elif event == 3:  # _IRQ_GATTS_WRITE
            conn, value_handle = data
            print(f"GATTS WRITE on handle {value_handle} from {conn}")

        elif event == 4:  # _IRQ_GATTS_READ_REQUEST
            conn, value_handle = data
            print(f"READ request on handle {value_handle} from {conn}")

        elif event == 20:  # _IRQ_GATTS_INDICATE_DONE
            conn, value_handle, status = data
            print(f"Indicate done: {conn} status: {status}")

        elif event == 21:  # _IRQ_MTU_EXCHANGED
            conn, mtu = data
            print(f"MTU exchanged: {mtu}")

        else:
            print(f"Unhandled IRQ: {event}, data: {data}")

    # -----------------------------------------------------------------------
    #  Advertising
    # -----------------------------------------------------------------------
    def _advertise(self, name=None):
        if name is None:
            name = self._name

        # Short, valid 31-byte advertisement
        adv = bytearray([
            0x02, 0x01, 0x06,                           # Flags
            0x05, 0x03, 0x18, 0x18, 0x0F, 0x18,         # UUIDs: CPS + Battery
            0x06, 0x16, 0x18, 0x18, 0x96, 0x00, 0x00,   # Service Data (CPS, 150 W)
            0x03, 0x19, 0x84, 0x04,                     # Appearance = P