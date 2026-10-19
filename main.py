import time
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from shell_gui import shell_setup
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import serial

from serial.tools import list_ports


BAUD_RATE = 115200
SERIAL_PORT = "COM6"
WINDOW_SECONDS = 60
MAX_POINTS = 5000
UPDATE_MS = 30
SSH_ADDRESS = ""

root = tk.Tk()


def open_port(port):
    global ser
    if ser is not None and ser.is_open:
        ser.close()
    ser = None

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout = 1)
        status_var.set(f"Connected: {port}")
    except serial.SerialException as e:
        status_ver.set("Cannot open {port}")
        print("Cannot open port: ", port, e)


def apply_string():
    global SSH_ADDRESS
    SSH_ADDRESS = entry_var.get().strip()


def list_port_names():
    return [p.device for p in list_ports.comports()]

def on_port_selected(event=None):
    open_port(port_var.get())

def refresh_ports():
    port_box["values"] = list_port_names()

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

def update_averages():
    for name, data, var in zip(names, ydata, avg_vars):
        if len(data) >= UPDATE_MS:
            recent = list(data)[-UPDATE_MS:]
            var.set(f"{name} avg: {sum(recent) / len(recent):.3f}")


def on_close():
    global running
    running = False
    ssh_close()
    if ser is not None and ser.is_open:
        ser.close()
    root.destroy()

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

            update_averages()
            if xs[-1] > WINDOW_SECONDS:
                axes[0].set_xlim(xs[-1] - WINDOW_SECONDS, xs[-1])
            canvas.draw_idle()

    root.after(UPDATE_MS, update_plot)




ser = None

style = ttk.Style(root)
style.theme_use("clam")
style.configure("Save.TButton", background="green", foreground="black")
style.map("Save.TButton",
          background=[("active", "blue")],
          foreground=[("active", "black")])


style1 = ttk.Style(root)
style1.theme_use("clam")
style1.configure("Dark.TFrame", background="black")

style.configure("Status.TLabel", background = "black", foreground = "white")
style.map("TCombobox", fieldbackground = [("readonly","#111111")],
          foreground=[("readonly", "white")],
          selectbackground=[("readonly", "#111111")],
          selectforeground=[("readonly", "white")])


style.configure("Readout.TLabel", background="black", foreground="lime",
                font=("Consolas", 16, "bold"))

style.configure("artStyle.TLabel", background = "black", foreground = "white",
                font = ("Consolas", 4, "bold"))

running = True
xdata = deque(maxlen=MAX_POINTS)
ydata = [deque(maxlen=MAX_POINTS) for _ in range(3)]
start_time = time.perf_counter()
names = ["sin", "cos", "tan"]
y_limits = [(-1.2, 1.2), (-1.2, 1.2), (-5.5, 5.5)]

root.title("Power Systems Analysis")
root.geometry("1000x800")
root.minsize(200, 100)
root.config(bg="black")

root.columnconfigure(0,weight = 1, uniform = "cols")
root.columnconfigure(1,weight = 1, uniform = "cols")
root.rowconfigure(0,weight = 0)
root.rowconfigure(1,weight = 1, uniform = "rows")
root.rowconfigure(2,weight = 1, uniform = "rows")

top_frame = ttk.Frame(root, padding=10,style = "Dark.TFrame")
top_frame.grid(row=0, column=0, columnspan=2, sticky="e")
plot_frame = ttk.Frame(root, padding=10, style="Dark.TFrame")
plot_frame.grid(row=1, column=1, sticky="nsew") 
readout_frame = ttk.Frame(root, padding = 10, style = "Dark.TFrame")
readout_frame.grid(row=2,column = 1, sticky = "nsew")

video_frame = ttk.Frame(root, padding = 5, style = "Dark.TFrame")
video_frame.grid(row = 0, column = 0, sticky = "w")

art_frame = ttk.Frame(root, padding = 2, style = "Dark.TFrame")
art_frame.grid(row = 2, column = 1, sticky = "se")

ttk.Button(top_frame, text = "SSH connect", 
           command = lambda: ssh_connect(SSH_ADDRESS, "pi")).pack(side = "right", padx = 10)
ttk.Button(top_frame, text = "Set SSH Address", command = apply_string).pack(side = "left", padx=2)

entry_var = tk.StringVar()
entry = ttk.Entry(top_frame, textvariable=entry_var,width = 25)
entry.pack(side = "left", padx = 5)

status_var = tk.StringVar(value = "Not Connected")

port_var = tk.StringVar()
port_box = ttk.Combobox(top_frame, textvariable=port_var, state="readonly",
                        width=10, values=list_port_names())
port_box.pack(side="left", padx=5)



port_box.bind("<<ComboboxSelected>>", on_port_selected)

ttk.Button(top_frame, text="Refresh", command=refresh_ports).pack(side="left", padx=5)
ttk.Label(top_frame, textvariable=status_var, style="Status.TLabel").pack(side="left", padx=10)


save_button = ttk.Button(top_frame, text="Save to Excel",
                         style="Save.TButton", command=on_save)
save_button.pack(side="right", padx=10)

# --- frame ---
     # don't forget this

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
canvas_widget = canvas.get_tk_widget()
canvas_widget.config(width = 100, height = 100)
canvas_widget.pack(fill = "both", expand = True)



ttk.Label(video_frame, text = "Video Footage: ", style = "Readout.TLabel").pack(anchor = "w", pady = 2)

address_string = "Currently connected to: "+SSH_ADDRESS



avg_vars = [tk.StringVar(value=f"{n} avg: --") for n in names]


for var in avg_vars:
    ttk.Label(readout_frame, textvariable=var,
              style="Readout.TLabel").pack(anchor="w", pady=2)

ssh_connect, ssh_close = shell_setup(root, row = 2, column = 0)

entry.bind("<Return>",apply_string)





art = """
                                                                                                                            
                                                                                                                            
                                                                                                                            
                                                                                                                            
                                                                                                                            
                                                          ........                                                          
                                                .:==*#######%#####%####*+=::                                                
                                           :=####%#####%#%###%#%#%#%#%###%#####=:                                           
                                       :=#########%#%*=--::###%##:::-=#%###%#######=:                                       
                                    :*##%#%#%##%#%####-.#*.-%##%+ -##+###%###%*###%###+:                                    
                                 :*#%#####%##= -##%#%#= +::##%##*#= :*%#######= =-=######+.                                 
                               +######-#%###%-*: -####= *#= :*%# =#=.*##%##%#= =%= =%#%#####:                               
                            :###%#%#*  =####%:+## :=#####%#%###%######%###%#+.=+ :+#####*#####-                             
                          :#####*:-##:+::##%*:=##%#%#%#%%#%#%%#%#%##%##%#%##+=## +#%#= :+*==#%##-                           
                        .*###%###:-. =:#: =#%#%#%#%###+-..        .:=##%##%#%##%*-##= #####:*##%##:                         
                       =#%#%####%#+=#=:##%%##%##+:.::=*###%##%#%#%###+-:.:=##%#%###%+-#%#* :#####%#+.                       
                     :########%####=-*##%###=:.=+##%%#%#%#%#%##%#%%%#%#%##*=::=##%#%#*=:.:=####.-##%#:                      
                    -##%####%###%####%#%#*::+##%##%##%#%#%#%#%#%###%#%#%#%#%##*.:*#%#%%%#%##%+ =##*#%#=                     
                   =%###+=***=###%#####=.-#%%#%#%#%%#%###%#:##%#%#%#%#%#%#%#%%#%#- =###%#%%#= =#*=:=#%#+                    
                  +#%#%+=###=: *##%##=.=#%#%#%#%#%#%%#%%#%%#%####*++*####%#:#%#%%%#=.=#%##%*:=+##%%#%#%#+                   
                 +#####+ =###*=#%##=.=#%#%#%##=#%#%#%%#%##=:-+####%#%#%#%#= ##%##%#%#-.*%#%#%#%#%#%#%:#%%*                  
                =%#%%%###:..:*#%##::#%#%%#%%#%#%#%###=::*#%#%%#%%#%#%##=:.   .:*#%#%#%#.-#%%#%####+: .:#%#+                 
               -#%##=*#%#%#%#%##+.=#%#%*+%#%#%##+=:=*%##%#%#%#%#%#%#%#%%%#+ #%%#%#%#%#%#-:#%%##= :=-=#+=#%#=                
              :#%#%##*+-=#%###%+.*%#%#%#%#%##=:=*#%#%#%#%#%%%%#%#%#%#%##%#%-%#%%#%%%#%#%#-.#%%%#=##*##*#%#%#:               
             .##%%=*#%###=#%%#*.*%#%#%%#%#=.-#%#%%####=::.    =#%#%#%#%#%#%#%%#%%##:#%%#%%=:##%%#..+%%#%#%#%*               
             =#%#*-:..-=:+%#%* +%#%#%##+:-*%#%#%#%+.   :%#=   =#%%#%%#%#%%#%#%#%#%%%%#%%#%#-:#%#%%#%#%##*:#%#-              
            .*%#%#%###++###%#.=%%%#%#-.=##%#%#%#%#+     --. *+#%#%%#%##%#%#%#%#%%#%#%%###%%#:=%%#%*--:..--*%##              
            -##%#%#%%#%#%#%#-:%#%##:.#%#%%#%%%%#%%####=:. ..%#%#%#%%#%#%#%#%%#%#%#%#%#%#+#%%+ #%%##=##:-*:-#%#:             
            +%#%#%##%#%#%#%+.##%#:.*%%#%#%#+*#%%#%%#%%## :#%%%%%#%#%%#%#%%%#%%##%%%#%%#%%%#%%::#%#%#= =+:=#%#%+             
            ##%#%#%#%#%#%#%=-##:.+%#%#%#%%%##%#%%#%%#%%* :#%#%#%%%%#%%#%#%#%#%#%#%#%#%%#%#%#%*.*%#%#-#%%%#%#%#*.            
           :%#%####%#%#%#%#.=+ -#%#%%%%%#%#%%%%#%#%%%#%# :#%%%%#==:=##%#%#%%%%#%%#%#%#%#%%%%#%.=#%#%#%#%#%%#%%#:            
           -%%#%%%#%#%#%#%# . *%%%#%#+#%%%#%#%#%%%#%%#*==+##**++.=. .*%%%%#%####%%%%%#%%#%#%%#::#%#%#%#%#%#%#%#:            
           =#%%##%#%#%%%%#+ :##%#%%#%#%#%#%%%%%#%%%%##=--:==-==: :===+###%%##-=:#%#%###%%%%#%%=:#%#%#%%#%#%#%##-            
           +%#%%#%#%%#%#%%=.+%%#%#%#%%%%%%#%#%#-==+*##. +***#*#####***+=:...:  =%%%#%%%#%#%%#%=:#%%#%#%%%#%%#%#-            
           +%##%#+.:#%#%#%=:##%%%%%%#%#%#%#= ...    ##. #+       -*        :#*##%#%%#%#%%%%%%#=:##%#%##.:#%#%%#-            
           =%%%#%#%%%#%%#%+:#%#%#%#%%%%#%%#- ..    .##: #*       :#        #-  :#%#%%%%#%#%#%%-:#%#%#%%%#%#%#%#:            
           -##%#%%#%#%#%%##.*%%%%#%#%#%%#*::::#=  -=#*. =-  *##+  ::::-==+*#*+==%%%#%#%%%%#%#%:-#%#%#%#%#%%%#%#:            
           .%#%#%#%#%%#%#%#:=%#%%%%%####=...-#%#:::   .  :#%%%#######=     :##:   *%%%#%#%%%%#.*#%%#%#%#%#%#%#*.            
            ##%#%%#%#%#%#%#=:#%%%##=---::*#*##%%%%%%%#****###=::::=##+#%###%%%%#*+==++#%%#%#%::#%#%%#%%%#%%%#%=             
            =%%#%#%%%%%#%#%#:+%#%%+::::.*%#-*%%%%#%#::::.+#%::::::#%#:*%%%%%%%%-::.:+#.#%%%%* *%#%#%%#%#%#%#%#:             
            :##%#%#%#%#%#%#%=.#%#%#+==-:#%#-=%%#%%%-    .%%#:....-#%#-*%#%#%#%#    .#%:=%%##:=%#%#%#%#%#%#%#%*              
             =#%#%#%#%#%%#%#%=.#%%*:::::*%#-+%%%%%%=:::..%#%=====:#%#:*%%%%%%##::.::#%:+%%#-:#%#%%#%#%#%%#%##.              
             .#%%#%#%#%#%#%#%#=:*%#===-::+-.::::-==#===-:+#%*====:+%-:-::::-==*===--++:#%%-:#%#%#%#%#%%#%%#%=               
              :#%#%#%#%#%%#%#%#=.=-:  :=*####%%##+-:::.......        :::=*####*+-.    .:=::#%#%#%#%#%#%#%#%+.               
               :#%#%#%#%#%#%%#%#*.-#%#%##*::.            +###*=:.          .::::-+####*: =%#%#%%#%%#%%#%#%#:                
                =#%%%#%#%#%#%#%%##-:-::-. =:.:==*#######=                   .:====   .-.*#%#%%#%%#%%#%#%%#:                 
                 =#%#%#%#%#%%#%#%%#*: .  :*##%#%#%#%#%##-         :=+******+=::.      +#%#%#%#%#%##%#%###:                  
                  =%#%#%#%#%#%#%#%%#%*. +%#%%%%#%###*:    ..    #%%#%#%%#%#%#%#%#:  =#%#%%#%#%#%#%#%#%%#:                   
                   :#%#%%#%#%%%%#%#%%%#*:.====-:.     .+#%#+.   =##%%%#%#%%%%#%*-:=#%#%#%#%#%#%%#%%#%##:                    
                    :##%#%#%###%#%#%#%%#%#=.                    :==-:::-----:: =##%%#%#%%%#%%%#%%#%#%+                      
                      +%%%%#%%#%#%%#%#%#%#%##*:  -#####%#.     .:--:.       =#%%%%#%%#%##%%#%#%#%#%#-                       
                       :##%%#%#%%#%#%#%##+#%%%%%#*=::.:.             .:-+#%%%#%#*#%#%#%%#%#%%%#%%%*:                        
                         =#%%%#%#%#%%%%%*#*::=#%%#%#%####*++++++*####%%#%%%%%%%: =#%%%#%#%%##%%##:                          
                           =#%%#%#%#%#%#%#::##:#%#%%%%%%%%%%#%#%#%%%%#%#%+. :#%=- =%#%%%%#%%#%#=                            
                            .+#%%%#%#%#%#.:#%%%#%%%#..=-.#%#%%%%#:=#%%%%%#%:-.:==+ -##%#%%#%#=                              
                               =#%#%%#%#=.=%#%#%#%## :+**%%%#%#%*:.=#%%#%%%#-*+.=#+##%%%%%#-                                
                                 :##%#%%%%#%#%%%%%%= ==*%%%%%%%%.:. :#%%#%#%+:*%#%%%%#%#+.                                  
                                    -##%#%%#%#%#%#*:.=*+ #%#%##=-#%+.:#%%%%%%%#%%#%##*:                                     
                                       :+#%#%%%%#%#%%#%##%%#%%####%%%%#%%#%#%%%%%#=:                                        
                                           :=##%%#%#%%%%%#%#%#%%%%#%#%%#%%%%##=:                                            
                                                :=*#####%%%%%%#%#%%#####*-.                                                 
                                                        ..:::::::..                                                         
                                                                                                                            
"""
art_label = ttk.Label(art_frame, text = art,
          style = "artStyle.TLabel", justify = "right")
art_label.pack(anchor = "e")

root.protocol("WM_DELETE_WINDOW", on_close)
root.after(UPDATE_MS, update_plot)
root.mainloop()