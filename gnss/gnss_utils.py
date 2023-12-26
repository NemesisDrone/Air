from math import radians, sin, cos, sqrt, atan2


def DMm_to_DD(degrees: int, minutes: float):
    """
    Convert (DD, MM.mmmmm) to DD.dddddd
    """
    return degrees + minutes / 60.0


def DD_delta(lat1: float, lon1: float, lat2: float, lon2: float):
    """
    Calculate the difference between two (DD.dddddd, DD.dddddd) coordinates using the Haversine formula.
    :return: (lat_delta, lon_delta)
    """
    # Radius of the Earth in meters
    R = 6371000.0

    # Convert decimal degrees to radians
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])

    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Distance in meters
    lat_delta = R * c

    # Distance in meters
    lon_delta = R * c

    return lat_delta, lon_delta
