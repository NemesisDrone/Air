import matplotlib.pyplot as plt
import json
import numpy as np

import gnss_utils as gu


def read_gnss(name: str):
    with open(name, "r") as f:
        data = f.readlines()
        data = [json.loads(d) for d in data]
        return data


def equilibrate(d1, d2):
    idx1 = 0
    idx2 = 0


data1 = read_gnss("./gnss1.txt")
data2 = read_gnss("./gnss2.txt")

lat1 = np.array([gu.DMm_to_DD(*d["lat"]) for d in data1], dtype=np.float64)
lat2 = np.array([gu.DMm_to_DD(*d["lat"]) for d in data2], dtype=np.float64)
lon1 = np.array([gu.DMm_to_DD(*d["lon"]) for d in data1], dtype=np.float64)
lon2 = np.array([gu.DMm_to_DD(*d["lon"]) for d in data2], dtype=np.float64)
print(len(lat1), len(lat2), len(lon1), len(lon2))
exit(0)

lat_delta = np.array([gu.DD_delta(lat1[i], lon1[i], lat2[i], lon2[i]) for i in range(len(lat1))])
lon_delta = np.array([gu.DD_delta(lat1[i], lon1[i], lat2[i], lon2[i]) for i in range(len(lon1))])

# 2 row 2 col
fig, (ax1, ax2) = plt.subplots(2, 1)
ax1.plot(lat_delta)
ax2.plot(lon_delta)
plt.show()
