import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog
import pygame
import time
import ctypes

# Windows-specific libraries for high-performance background polling
import XInput 

# Set high timer resolution for the OS to minimize input lag
ctypes.windll.winmm.timeBeginPeriod(1)

CONFIG_FILE = "overlay_config.json"

class OverlaySettings:
    """Manages the persistence of user configurations."""
    def __init__(self):
        self.load()

    def load(self):
        # Optimized default layout for Windows controllers
        default_config = {
            "lanes": [
                {"label": "Lane 1", "color": [0, 255, 120], "key": "d", "type": "pad_button", "id": "DPAD_LEFT"}, 
                {"label": "Lane 2", "color": [0, 255, 120], "key": "f", "type": "pad_button", "id": "DPAD_RIGHT"}, 
                {"label": "Lane 3", "color": [0, 255, 120], "key": "j", "type": "pad_button", "id": "X"},  
                {"label": "Lane 4", "color": [0, 255, 120], "key": "k", "type": "pad_button", "id": "Y"},  
                {"label": "Lane 5", "color": [0, 255, 120], "key": "l", "type": "pad_button", "id": "B"},  
                {"label": "OD",     "color": [255, 255, 0], "key": "space", "type": "pad_trigger", "id": 1} # 1 = RT
            ],
            "bg_color": [255, 0, 255], 
            "off_color": [20, 20, 20],
            "sound_path": "click.wav",
            "fps": 144,
            "trigger_threshold": 0.5
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.data = json.load(f)
                    for k, v in default_config.items():
                        if k not in self.data: self.data[k] = v
            except: self.data = default_config
        else: self.data = default_config

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

# --- Background Keyboard Polling ---
def is_key_pressed_win32(key_name):
    """Uses GetAsyncKeyState to check key states regardless of window focus."""
    VK_MAP = {
        "d": 0x44, "f": 0x46, "j": 0x4A, "k": 0x4B, "l": 0x4C,
        "space": 0x20, "escape": 0x1B
    }
    vk = VK_MAP.get(key_name.lower())
    if vk:
        return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0
    return False

# --- Config GUI ---
def open_settings(settings):
    root = tk.Tk()
    root.title("Festival Overlay Configuration")
    root.geometry("640x600")
    
    # UI Styling
    BG_DARK = "#121212"; FG_WHITE = "#ffffff"; ACCENT = "#00ff78"
    root.configure(bg=BG_DARK)

    # --- Global Config ---
    g_frame = tk.LabelFrame(root, text="Global Settings", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    g_frame.pack(fill="x", padx=20, pady=10)

    # Sound selection
    sound_var = tk.StringVar(value=os.path.basename(settings.data.get("sound_path", "click.wav")))
    def select_file():
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            sound_var.set(os.path.basename(path))
            settings.data["sound_path"] = path

    tk.Label(g_frame, text="Sound FX:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=0, sticky="w")
    tk.Entry(g_frame, textvariable=sound_var, width=20, state="readonly").grid(row=0, column=1, padx=5)
    tk.Button(g_frame, text="Browse", command=select_file).grid(row=0, column=2)

    # Performance
    tk.Label(g_frame, text="FPS Target:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=3, padx=(15, 0))
    fps_var = tk.StringVar(value=str(settings.data.get("fps", 144)))
    tk.Entry(g_frame, textvariable=fps_var, width=5).grid(row=0, column=4, padx=5)

    def pick_g_color(key):
        c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data[key]))
        if c[1]: settings.data[key] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

    tk.Button(g_frame, text="Chroma BG", command=lambda: pick_g_color("bg_color")).grid(row=1, column=0, pady=10)
    tk.Button(g_frame, text="Note Off", command=lambda: pick_g_color("off_color")).grid(row=1, column=1, pady=10)

    # --- Lane Config Area ---
    l_frame = tk.LabelFrame(root, text="Input Recording (Click to listen, ESC to cancel)", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    l_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Lane", "Keyboard", "Controller", "Color"]
    for i, txt in enumerate(headers):
        tk.Label(l_frame, text=txt, font=("Arial", 9, "bold"), bg=BG_DARK, fg="#666666").grid(row=0, column=i, sticky="ew")

    def record_input(target_var, lane_idx, is_pad=False):
        old_val = target_var.get()
        target_var.set("RECORDING...")
        root.update()
        time.sleep(0.3) # Prevent click bleed-through
        
        captured = False
        while not captured:
            if not is_pad:
                # Keyboard Recording
                def on_key(event):
                    nonlocal captured
                    kn = event.keysym.lower()
                    if kn == "escape": target_var.set(old_val)
                    else: target_var.set(kn)
                    captured = True
                root.bind("<Key>", on_key); root.wait_variable(target_var); root.unbind("<Key>")
            else:
                # Pad Recording (XInput Polling)
                state = XInput.get_state(0)
                btns = XInput.get_button_values(state)
                trigs = XInput.get_trigger_values(state)
                # Check buttons
                for b_name, pressed in btns.items():
                    if pressed:
                        settings.data["lanes"][lane_idx]["type"] = "pad_button"
                        settings.data["lanes"][lane_idx]["id"] = b_name
                        target_var.set(b_name); captured = True; break
                # Check triggers
                if not captured:
                    if trigs[0] > 0.7: # LT
                        settings.data["lanes"][lane_idx]["type"] = "pad_trigger"; settings.data["lanes"][lane_idx]["id"] = 0
                        target_var.set("LT"); captured = True
                    elif trigs[1] > 0.7: # RT
                        settings.data["lanes"][lane_idx]["type"] = "pad_trigger"; settings.data["lanes"][lane_idx]["id"] = 1
                        target_var.set("RT"); captured = True
            
            if is_key_pressed_win32("escape"): # Hardware ESC cancel
                target_var.set(old_val); captured = True
            root.update()
            if captured: break

    lane_vars = []
    for i, lane in enumerate(settings.data["lanes"]):
        row = i + 1
        tk.Label(l_frame, text=lane['label'], bg=BG_DARK, fg=ACCENT, width=10).grid(row=row, column=0, pady=5)
        
        # Keyboard setting
        kv = tk.StringVar(value=lane.get('key', ''))
        tk.Button(l_frame, textvariable=kv, width=8, command=lambda v=kv, idx=i: record_input(v, idx)).grid(row=row, column=1, padx=5)
        
        # Pad setting
        pv_label = str(lane.get('id', 'None'))
        if lane.get('type') == 'pad_trigger': pv_label = "LT" if lane.get('id') == 0 else "RT"
        pv = tk.StringVar(value=pv_label)
        tk.Button(l_frame, textvariable=pv, width=12, command=lambda v=pv, idx=i: record_input(v, idx, True)).grid(row=row, column=2, padx=5)
        
        # Color setting
        def pick_l_color(idx=i):
            c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data["lanes"][idx]["color"]))
            if c[1]: settings.data["lanes"][idx]["color"] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]
        tk.Button(l_frame, text="Color", command=pick_l_color, width=8).grid(row=row, column=3, padx=5)
        lane_vars.append(kv)

    def on_launch():
        try: settings.data["fps"] = int(fps_var.get())
        except: settings.data["fps"] = 144
        for i, k in enumerate(lane_vars): settings.data["lanes"][i]["key"] = k.get()
        settings.save(); root.destroy()

    tk.Button(root, text="SAVE & LAUNCH OVERLAY", command=on_launch, bg=ACCENT, fg="black", font=("Arial", 11, "bold")).pack(pady=20)
    root.mainloop()

# --- Main Runtime ---
def run_overlay(settings):
    pygame.init()
    data = settings.data
    
    # DirectX / DSOUND for low latency
    os.environ['SDL_AUDIODRIVER'] = 'dsound'
    pygame.mixer.init()
    
    sound = None
    if os.path.exists(data.get("sound_path", "click.wav")):
        sound = pygame.mixer.Sound(data["sound_path"])
        sound.set_volume(0.6)

    # Final Layout Params
    LW, OD_LW, GAP = 165, 90, 100
    screen = pygame.display.set_mode((1200, 100))
    pygame.display.set_caption("Festival Overlay")
    clock = pygame.time.Clock()
    prev_states = [False] * len(data["lanes"])

    while True:
        screen.fill(tuple(data["bg_color"]))
        if any(e.type == pygame.QUIT for e in pygame.event.get()): break

        # Native XInput Polling (Doesn't care about window focus)
        state = XInput.get_state(0)
        pad_buttons = XInput.get_button_values(state)
        pad_triggers = XInput.get_trigger_values(state)

        for i, lane in enumerate(data["lanes"]):
            pressed = False
            
            # 1. Background Keyboard (Win32 API)
            if is_key_pressed_win32(lane.get("key", "")):
                pressed = True
            
            # 2. Background PAD (XInput Polling)
            if not pressed:
                if lane.get("type") == "pad_button":
                    if pad_buttons.get(lane.get("id"), False): pressed = True
                elif lane.get("type") == "pad_trigger":
                    # Triggers in XInput are naturally 0.0 to 1.0
                    if pad_triggers[lane.get("id")] > 0.2: pressed = True

            # Play sound on edge detection
            if pressed and not prev_states[i] and sound:
                sound.play()
            prev_states[i] = pressed

            # Calculate screen positioning
            x = (50 + i * (LW + 15)) if i < 5 else (50 + 5 * (LW + 15) + GAP)
            rect = (x, 25, (LW if i < 5 else OD_LW), 50)
            c = tuple(lane["color"]) if pressed else tuple(data["off_color"])
            
            pygame.draw.rect(screen, c, rect, border_radius=6)
            if pressed:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=6)

        pygame.display.flip()
        clock.tick(data.get("fps", 144))
    
    pygame.quit()

if __name__ == "__main__":
    s = OverlaySettings(); open_settings(s); run_overlay(s)