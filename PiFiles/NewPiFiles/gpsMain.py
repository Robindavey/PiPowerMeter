import _thread
import time
import network
import bluetooth
from ble_service import BLECyclingPower
from gps_reader import GPSReader
from config import BLE_NAME
from machine import Pin
def disable_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    print("WiFi disabled to avoid BLE interference.")
def hover(led, wait):
    for i in range(wait*2):
        led.toggle() # Toggles the LED between on (1) and off (0)
        time.sleep(0.5)

def main():
    led = Pin("LED", Pin.OUT)

    hover(led, 3)
    led.toggle()
    disable_wifi()

    ble = bluetooth.BLE()
    cps = BLECyclingPower(ble)

    gps_reader = GPSReader(cps)
    _thread.start_new_thread(gps_reader.run, ())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        gps_reader.stop()
        time.sleep(1)
        if hasattr(cps, 'cleanup'):
            cps.cleanup()
        print("Exited cleanly.")
        led.toggle()

if __name__ == "__main__":
    main()
