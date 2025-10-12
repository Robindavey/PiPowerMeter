import time
from wifi import connect_wifi
from SpoofListener import listen

def main():
    connect_wifi()
    while True:
        try:
            listen()
        except Exception as e:
            print("⚠️ Stream error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()

