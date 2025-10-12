import math

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

