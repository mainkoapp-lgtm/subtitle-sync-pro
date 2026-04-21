import tkinter as tk
from cefpython3 import cefpython as cef
import sys

def embed_cef():
    sys.excepthook = cef.ExceptHook
    cef.Initialize()
    window_info = cef.WindowInfo()
    window_info.SetAsChild(frame.winfo_id(), [0, 0, 900, 110])
    browser = cef.CreateBrowserSync(window_info, url="https://google.com")
    def message_loop():
        cef.MessageLoopWork()
        root.after(10, message_loop)
    root.after(10, message_loop)

root = tk.Tk()
root.geometry("900x200")
frame = tk.Frame(root, width=900, height=110)
frame.pack()
root.after(100, embed_cef)
root.mainloop()
cef.Shutdown()
