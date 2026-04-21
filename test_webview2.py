import sys
sys.coinit_flags = 2  # COINIT_APARTMENTTHREADED
import tkinter as tk
from tkwebview2.tkwebview2 import WebView2, have_runtime, install_runtime

def test():
    root = tk.Tk()
    root.geometry("900x200")
    
    if not have_runtime():
        install_runtime()
        
    frame = WebView2(root, 900, 110)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.load_url("https://www.google.com")
    
    root.mainloop()

test()
