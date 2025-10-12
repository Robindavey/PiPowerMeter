# 📝 Pi Pico W Cycling Power Broadcaster - TODOs

## Setup & Hardware
- [ ] Flash **MicroPython** or **CircuitPython** onto the Pi Pico W
- [ ] Connect **GPS module** to Pico W (UART/I2C/SPI)
- [ ] Optional: Connect **OLED/TFT display** for live stats
- [ ] Verify GPS module is **receiving NMEA data** and position fixes

## Software: Core Functionality
- [ ] Create `gps_reader.py` to:
  - [ ] Read GPS coordinates (latitude, longitude, altitude)
  - [ ] Compute **speed** from successive positions
  - [ ] Compute **slope** from elevation changes
- [ ] Create `power_calculator.py` to:
  - [ ] Implement physics-based power calculation:
    - `P_gravity = weight * g * v * slope`
    - `P_roll = weight * g * Crr * v`
    - `P_aero = 0.5 * rho * CdA * v³`
    - `P_total = P_gravity + P_roll + P_aero`
  - [ ] Smooth power values using a **rolling average**

## BLE / Wireless Broadcast
- [ ] Implement BLE peripheral in `ble_broadcaster.py`
- [ ] Advertise **Cycling Power Service** (UUID: 0x1818)
- [ ] Update **Power Measurement Characteristic** (UUID: 0x2A63) every second
- [ ] Test BLE broadcast appears as a virtual power meter (name: `PiPower`)

## User Interface (Optional)
- [ ] Implement display driver in `display.py`
- [ ] Show:
  - [ ] Current power (W)
  - [ ] Speed (km/h or mph)
  - [ ] Slope (%)
  - [ ] GPS fix quality

## Integration & Testing
- [ ] Create `main.py` loop to:
  - [ ] Read GPS data
  - [ ] Calculate power
  - [ ] Broadcast via BLE
  - [ ] Update display (if attached)
- [ ] Test **stationary** to verify GPS and power calculation
- [ ] Test **moving ride** to verify live power output
- [ ] Validate **BLE pairing** with Wahoo or other cycling computers

## Optional Improvements
- [ ] Log ride data to **CSV/JSON** file
- [ ] Add **heart rate / cadence input** (via ANT+ or BLE)
- [ ] Implement **configurable rider parameters** (weight, CdA, Crr)
- [ ] Implement **Wi-Fi dashboard** for real-time monitoring
