import network
import time

SSID = "MGH2 Wifi"
PASS = "MarlayGrange2"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi…")
        wlan.connect(SSID, PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("✅ Wi-Fi connected", wlan.ifconfig())
    return wlan

