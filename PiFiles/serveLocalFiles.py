import network
import socket
import os

# 🔧 Wi-Fi credentials
SSID = "MGH2 Wifi"
PASSWORD = "MarlayGrange2"

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
print("Connecting to WiFi...", end="")
while not wlan.isconnected():
    pass
print(" connected!")
print("IP:", wlan.ifconfig()[0])

# --- Server setup ---
PORT = 8080  # safer than 80 on Pico
addr = socket.getaddrinfo('0.0.0.0', PORT)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
print("Listening on http://%s:%s" % (wlan.ifconfig()[0], PORT))

def is_file(name):
    try:
        mode = os.stat(name)[0]
        return not (mode & 0x4000)  # directory flag
    except:
        return False

def serve_file(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        headers = (
            "HTTP/1.0 200 OK\r\n"
            "Content-Type: application/octet-stream\r\n"
            f"Content-Disposition: attachment; filename=\"{path}\"\r\n"
            "\r\n"
        )
        return headers.encode() + data
    except:
        return b"HTTP/1.0 404 NOT FOUND\r\n\r\nFile not found."

def list_files():
    html = """
    <html>
    <head><title>Pico File Server</title></head>
    <body style="font-family:sans-serif;">
    <h2>Pico File Server</h2>
    <p>Click a file to download:</p>
    <ul>
    """
    for fname in os.listdir():
        if is_file(fname):
            html += f'<li><a href="/{fname}">{fname}</a></li>'
    html += "</ul></body></html>"
    return b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + html.encode()

while True:
    cl, addr = s.accept()
    request = cl.recv(1024).decode()
    if not request:
        cl.close()
        continue

    path = request.split(' ')[1]
    if path == "/" or path == "":
        response = list_files()
    else:
        response = serve_file(path[1:])  # strip leading '/'

    cl.send(response)
    cl.close()