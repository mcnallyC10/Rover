import os
import re
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, simpledialog

import paramiko

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def shell_setup(root, row=2, column=0):
    """Panel that is a local shell until you connect over SSH.
    Returns (connect, close)."""
    chan = None
    client = None
    out_queue = queue.Queue()

    # --- widgets ---
    frame = ttk.Frame(root, padding=10, style="Dark.TFrame")
    frame.grid(row=row, column=column, sticky="nsew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    shell_out = tk.Text(frame, bg="black", fg="white", insertbackground="white",
                        font=("Consolas", 10), width=1, height=1,
                        wrap="word", state="disabled")
    shell_out.grid(row=0, column=0, sticky="nsew")

    scroll = ttk.Scrollbar(frame, command=shell_out.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    shell_out.config(yscrollcommand=scroll.set)

    shell_in = tk.Entry(frame, bg="#111111", fg="white",
                        insertbackground="white", font=("Consolas", 10))
    shell_in.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    # --- local shell ---
    if os.name == "nt":
        cmd, flags = ["cmd.exe"], subprocess.CREATE_NO_WINDOW
    else:
        cmd, flags = ["/bin/bash"], 0

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=0,
                            errors="replace", creationflags=flags)

    def local_reader():
        while True:
            ch = proc.stdout.read(1)
            if not ch:
                break
            out_queue.put(ch)

    threading.Thread(target=local_reader, daemon=True).start()   # must be started

    # --- output handling ---
    def append_output(text):
        shell_out.config(state="normal")
        shell_out.insert("end", text)
        shell_out.see("end")
        shell_out.config(state="disabled")

    def pump_output():
        chunk = ""
        while not out_queue.empty():
            chunk += out_queue.get_nowait()
        if chunk:
            append_output(chunk)
        root.after(50, pump_output)

    # --- SSH ---
    def connect(host, user):
        nonlocal chan, client
        pw = simpledialog.askstring("SSH", f"Password for {user}@{host}:", show="*")
        if pw is None:
            return

        def worker():
            nonlocal chan, client
            try:
                c = paramiko.SSHClient()
                c.load_system_host_keys()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(host, username=user, password=pw, timeout=10)
                client = c
                chan = c.invoke_shell(term="dumb")
                out_queue.put(f"\n[connected to {host}]\n")
                while True:
                    data = chan.recv(1024)
                    if not data:
                        break
                    out_queue.put(ANSI.sub("", data.decode(errors="replace")))
            except Exception as e:
                out_queue.put(f"\n[SSH error: {e}]\n")
            finally:
                chan = None            # fall back to the local shell
                out_queue.put("\n[SSH closed, back to local shell]\n")

        threading.Thread(target=worker, daemon=True).start()

    def send_command(event=None):
        line = shell_in.get()
        shell_in.delete(0, "end")

        
        append_output(line + "\n")      
        try:
            proc.stdin.write(line + "\n")
            proc.stdin.flush()
        except OSError:
            append_output("[local shell closed]\n")

    def close():
        if chan:
            chan.close()
        if client:
            client.close()
        proc.terminate()

    shell_in.bind("<Return>", send_command)
    pump_output()

    return connect, close