import matplotlib.pyplot as plt
import json


def read_gnss(name: str):
    with open(name, "r") as f:
        data = f.readlines()
        data = [json.loads(d) for d in data]

        return data


def equilibrate(data1, data2):
    # Find the first timestamp
    t1 = data1[0]["timestamp"]
    t2 = data2[0]["timestamp"]

    if t1 < t2:
        # data1 is first
        data1 = data1[1:]
    elif t1 > t2:
        # data2 is first
        data2 = data2[1:]
    else:
        # They are equal
        pass

    # Find the last timestamp
    t1 = data1[-1]["time"]
    t2 = data2[-1]["time"]

    if t1 < t2:
        # data2 is last
        data2 = data2[:-1]
    elif t1 > t2:
        # data1 is last
        data1 = data1[:-1]
    else:
        # They are equal
        pass

    return data1, data2

data2 = read_gnss("../gnss2.txt")

plt.plot([data2[i]["lat"][1] for i in range(len(data2))])
plt.savefig("lat.png")