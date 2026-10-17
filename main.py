import time
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import serial

BAUD_RATE = 115200
SERIAL_PORT = "COM6"
WINDOW_SECONDS = 60
MAX_POINTS = 5000
UPDATE_MS = 30

ser = None
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except serial.SerialException as e:
    print("Cannot open port:", SERIAL_PORT, e)

running = True
xdata = deque(maxlen=MAX_POINTS)
ydata = [deque(maxlen=MAX_POINTS) for _ in range(3)]
start_time = time.perf_counter()
names = ["sin", "cos", "tan"]
y_limits = [(-1.2, 1.2), (-1.2, 1.2), (-5.5, 5.5)]

# ---- Root first, before anything matplotlib creates a window ----
root = tk.Tk()
root.title("Power Systems Analysis")
root.geometry("1000x800")
root.minsize(200, 100)
root.config(bg="black")

root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)
root.columnconfigure(1, weight = 1)
root.rowconfigure(2, weight = 1)


style = ttk.Style(root)
style.theme_use("clam")
style.configure("Save.TButton", background="green", foreground="black")
style.map("Save.TButton",
          background=[("active", "blue")],
          foreground=[("active", "black")])


style1 = ttk.Style(root)
style1.theme_use("clam")
style1.configure("Dark.TFrame", background="black")

top_frame = ttk.Frame(root, padding=10,style = "Dark.TFrame")
top_frame.grid(row=0, column=0, sticky="ne")

def on_save(event=None):
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
    df.to_excel(filename, index=False)
    print(f"Saved {n} rows to {filename}")


save_button = ttk.Button(top_frame, text="Save to Excel",
                         style="Save.TButton", command=on_save)
save_button.pack(side="right", padx=10)


# ... Save.TButton config etc.

# --- frame ---
plot_frame = ttk.Frame(root, padding=10, style="Dark.TFrame")
plot_frame.grid(row=1, column=0, sticky="nsew")      # don't forget this

# --- figure ---
fig = Figure(figsize=(10, 7), facecolor="black")
axes = fig.subplots(3, 1, sharex=True)

line_colours = ["cyan", "red", "orange"]
lines = []
for ax, name, (lo, hi), colour in zip(axes, names, y_limits, line_colours):
    line, = ax.plot([], [], label=name, color=colour, linewidth=1.5)
    lines.append(line)
    ax.set_ylim(lo, hi)
    ax.set_ylabel(name, color="white")
    ax.set_facecolor("#111111")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")
    ax.grid(True, color="gray", alpha=0.4)
    ax.legend(loc="upper right", facecolor="#222222",
              edgecolor="white", labelcolor="white")

axes[-1].set_xlabel("Time (s)", color="white")
axes[0].set_xlim(0, WINDOW_SECONDS)
fig.tight_layout()

# --- canvas ---
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)
def on_close():
    global running
    running = False
    if ser is not None and ser.is_open:
        ser.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)   # now actually registered

def update_plot():
    if not running:
        return

    if ser is not None and ser.is_open:
        try:
            for _ in range(200):
                if ser.in_waiting == 0:
                    break
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
                try:
                    values = [float(p) for p in raw.split(",")]
                except ValueError:
                    continue
                if len(values) < 3:
                    continue
                xdata.append(time.perf_counter() - start_time)
                for j in range(3):
                    ydata[j].append(values[j])
        except serial.SerialException as e:
            print("Lost connection:", e)

        if xdata:
            xs = list(xdata)
            for i, line in enumerate(lines):
                line.set_data(xs, list(ydata[i]))
            if xs[-1] > WINDOW_SECONDS:
                axes[0].set_xlim(xs[-1] - WINDOW_SECONDS, xs[-1])
            canvas.draw_idle()

    root.after(UPDATE_MS, update_plot)

root.after(UPDATE_MS, update_plot)
root.mainloop()