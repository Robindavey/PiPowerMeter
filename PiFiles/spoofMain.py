import time
from wifi import connect_wifi
from SpoofListener import listen, cleanup
def main():
    
    connect_wifi()
    while True:
        try:
            print("Running Bluetooth program. Press Ctrl+C to stop.")
            listen()

            # Your Bluetooth work here (advertising, connecting, etc.)
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt received.")
            cleanup()

        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(5)
            cleanup()

        finally:
            # Optional: ensure cleanup always runs, even on exceptions
            if ble.active():
                cleanup()
            print("Program exited cleanly.")
        

if __name__ == "__main__":
    main()
