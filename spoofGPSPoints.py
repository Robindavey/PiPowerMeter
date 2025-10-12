import socket
import time
import json
import gpxpy

# -------------------------
# Load GPX file
# -------------------------
def parse_gpx(file_path):
    import math
    import gpxpy.gpx
    points = []
    with open(file_path, "r") as f:
        gpx = gpxpy.parse(f)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time:
                        points.append({
                            "time": point.time.isoformat(),
                            "lat": point.latitude,
                            "lon": point.longitude,
                            "elevation": point.elevation
                        })
    return points

# Add speed
def add_speed(points):
    import math
    enriched = []
    for i in range(1, len(points)):
        p1, p2 = points[i-1], points[i]
        dt = (time.strptime(p2["time"][:19], "%Y-%m-%dT%H:%M:%S").tm_sec -
              time.strptime(p1["time"][:19], "%Y-%m-%dT%H:%M:%S").tm_sec)
        if dt <= 0:
            dt = 1
        # rough haversine in meters
        R = 6371000
        from math import radians, sin, cos, sqrt, asin
        lat1, lon1, lat2, lon2 = map(radians, [p1["lat"], p1["lon"], p2["lat"], p2["lon"]])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        d = 2*R*asin(sqrt(a))
        speed = d/dt
        enriched.append({
            **p2,
            "speed_mps": round(speed, 2),
            "dt": dt
        })
    return enriched

# -------------------------
# TCP Streaming
# -------------------------
HOST = "0.0.0.0"
PORT = 9000

points = add_speed(parse_gpx("Cycling_Out1.gpx"))
print(f"Loaded {len(points)} points")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
print(f"TCP Server listening on {HOST}:{PORT}")
SpeedUp = 4
while True:
    conn, addr = s.accept()
    print("Client connected:", addr)
    try:
        for point in points:
            line = json.dumps(point, separators=(",", ":")) + "\n"
            conn.sendall(line.encode("utf-8"))
            time.sleep(point["dt"])  # use real-time delay from GPX
    except Exception as e:
        print("Client disconnected or error:", e)
    finally:
        conn.close()
