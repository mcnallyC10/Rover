import matplotlib.pyplot as plt
import time
from collections import deque
import serial
import pandas as pd
from matplotlib.widgets import Button


BAUD_RATE = 115200
SERIAL_PORT = "COM6"
WINDOW_SECONDS = 60
MAX_POINTS = 5000

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

xdata = deque(maxlen=MAX_POINTS)
ydata = [deque(maxlen=MAX_POINTS) for _ in range(3)]

names = ["sin", "cos", "tan"]
y_limits = [(-1.2, 1.2), (-1.2, 1.2), (-5.5, 5.5)]   # tan is clamped to +/-5 on the Arduino

fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 7))
lines = []

from datetime import datetime

def on_save(event):
    # Snapshot so the data can't change mid-save
    t = list(xdata)
    n = len(t)
    if n == 0:
        print("No data to save")
        return

    df = pd.DataFrame({
        "Time (s)": t,
        "sin": list(ydata[0])[:n],
        "cos": list(ydata[1])[:n],
        "tan": list(ydata[2])[:n],
    })

    filename = f"sensor_data_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    df.to_excel(filename, index=False)      # needs: pip install openpyxl
    print(f"Saved {n} rows to {filename}")

ax_save = fig.add_axes([0.71, 0.015, 0.15, 0.05])
btn_save = Button(ax_save, "Save", color="#1f2430", hovercolor="#2e3547")
btn_save.on_clicked(on_save)

for ax, name, (lo, hi) in zip(axes, names, y_limits):
    line, = ax.plot([], [], label=name)
    lines.append(line)
    ax.set_ylim(lo, hi)
    ax.set_ylabel(name)
    ax.legend(loc="upper right")
    ax.grid(True)

axes[-1].set_xlabel("Time (s)")
axes[0].set_xlim(0, WINDOW_SECONDS)

start_time = time.perf_counter()
plt.show(block=False)


try:
    while plt.fignum_exists(fig.number):
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        parts = raw.split(",")
        if len(parts) != 3:
            continue
        try:
            values = [float(p) for p in parts]    # float instead of int
        except ValueError:
            continue

        t = time.perf_counter() - start_time
        xdata.append(t)
        for i, v in enumerate(values):
            ydata[i].append(v)
            lines[i].set_data(xdata, ydata[i])

        if t > WINDOW_SECONDS:
            axes[0].set_xlim(t - WINDOW_SECONDS, t)

        plt.pause(0.01)
finally:
    ser.close()