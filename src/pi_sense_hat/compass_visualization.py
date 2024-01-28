import json
import matplotlib.pyplot as plt

with open("compass_calibrated_2_data_30.json", "r") as file:
    data = json.load(file)

transposed_data = list(map(list, zip(*data)))

plt.figure(figsize=(8, 6))

plt.scatter(transposed_data[1], transposed_data[0], label="compassX / Y")

plt.scatter(transposed_data[0], transposed_data[1], label="compassY / X")

plt.scatter(transposed_data[0], transposed_data[2], label="compassZ / X")

plt.title("Magnetometer data from SenseHat")
plt.xlabel("X")
plt.ylabel("Y/Z")
plt.legend()

plt.show()