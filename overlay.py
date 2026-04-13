import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog
import pygame
import time

# --- Configuration File Path ---
CONFIG_FILE = "overlay_config.json"

class OverlaySettings:
    def __init__(self):
        self.load()

    def load(self):
        default_config = {
            "lanes": [
                {"label": "Lane 1", "color": [0, 255, 120], "key": "d", "input_type": "button", "input_id": 13}, 
                {"label": "Lane 2", "color": [0, 255, 120], "key": "f", "input_type": "button", "input_id": 14}, 
                {"label": "Lane 3", "color": [0, 255, 120], "key": "j", "input_type": "button", "input_id": 2},  
                {"label": "Lane 4", "color": [0, 255, 120], "key": "k", "input_type": "button", "input_id": 3},  
                {"label": "Lane 5", "color": [0, 255, 120], "key": "l", "input_type": "button", "input_id": 1},  
                {"label": "OD",     "color": [255, 255, 0], "key": "space", "input_type": "axis", "input_id": 5} 
            ],
            "bg_color": [255, 0, 255],
            "off_color": [20, 20, 20],
            "sound_path": "click.wav",
            "fps": 144
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

# --- GUI Configurator ---
def open_settings(settings):
    root = tk.Tk()
    root.title("Festival Overlay Configuration")
    root.geometry("650x600")
    
    BG_COLOR = "#1a1a1a"
    FG_COLOR = "#ffffff"
    ACCENT_COLOR = "#00ff78"
    root.configure(bg=BG_COLOR)

    # --- Global Settings ---
    g_frame = tk.LabelFrame(root, text="Global Settings", bg=BG_COLOR, fg=FG_COLOR, padx=15, pady=10)
    g_frame.pack(fill="x", padx=20, pady=10)

    sound_name = os.path.basename(settings.data.get("sound_path", "click.wav"))
    sound_var = tk.StringVar(value=sound_name)
    def browse_sound():
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            sound_var.set(os.path.basename(path))
            settings.data["sound_path"] = path

    tk.Label(g_frame, text="SFX:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, sticky="w")
    tk.Entry(g_frame, textvariable=sound_var, width=15, state="readonly").grid(row=0, column=1, padx=5)
    tk.Button(g_frame, text="Browse", command=browse_sound).grid(row=0, column=2, padx=5)

    tk.Label(g_frame, text="FPS:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=3, padx=(15, 0))
    fps_var = tk.StringVar(value=str(settings.data.get("fps", 144)))
    tk.Entry(g_frame, textvariable=fps_var, width=5).grid(row=0, column=4, padx=5)

    def pick_color(key):
        c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data[key]))
        if c[1]: settings.data[key] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

    tk.Button(g_frame, text="Screen BG", command=lambda: pick_color("bg_color")).grid(row=1, column=0, pady=10)
    tk.Button(g_frame, text="Notes Off", command=lambda: pick_color("off_color")).grid(row=1, column=1, pady=10)

    # --- Lane Binding ---
    l_frame = tk.LabelFrame(root, text="Input Bindings (ESC to cancel)", bg=BG_COLOR, fg=FG_COLOR, padx=15, pady=10)
    l_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Lane", "Keyboard", "Controller", "Color"]
    for i, txt in enumerate(headers):
        tk.Label(l_frame, text=txt, font=("Arial", 9, "bold"), bg=BG_COLOR, fg="#777777").grid(row=0, column=i, sticky="ew")

    pygame.init()
    if hasattr(pygame, 'joystick'):
        pygame.joystick.init()
        joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if joy: joy.init()

    lane_vars = []

    def record_input(target_var, lane_idx, is_pad=False):
        """Fixed recorder that prevents accidental triggers (ghost axes)."""
        old_val = target_var.get()
        target_var.set("REC...")
        root.update()
        
        # Give user a moment to release buttons
        time.sleep(0.2)
        pygame.event.pump()
        
        captured = False
        while not captured:
            pygame.event.pump()
            
            # 1. Keyboard Recording
            if not is_pad:
                def on_key(event):
                    nonlocal captured
                    key_name = event.keysym.lower()
                    if key_name == "escape":
                        target_var.set(old_val)
                    else:
                        target_var.set(key_name)
                    captured = True
                root.bind("<Key>", on_key)
                root.wait_variable(target_var)
                root.unbind("<Key>")
            else:
                # 2. Controller Recording
                if joy:
                    # Check Buttons
                    for b in range(joy.get_numbuttons()):
                        if joy.get_button(b):
                            settings.data["lanes"][lane_idx]["input_type"] = "button"
                            settings.data["lanes"][lane_idx]["input_id"] = b
                            target_var.set(f"Btn {b}"); captured = True; break
                    
                    # Check D-pad (Hats)
                    if not captured:
                        for h in range(joy.get_numhats()):
                            h_val = joy.get_hat(h)
                            if h_val != (0, 0):
                                settings.data["lanes"][lane_idx]["input_type"] = "hat"
                                settings.data["lanes"][lane_idx]["input_id"] = h
                                settings.data["lanes"][lane_idx]["hat_val"] = h_val
                                target_var.set(f"Hat {h_val}"); captured = True; break
                    
                    # Check Triggers/Axes (Increased threshold to 0.8 to ignore drift)
                    if not captured:
                        for a in range(joy.get_numaxes()):
                            if abs(joy.get_axis(a)) > 0.8:
                                settings.data["lanes"][lane_idx]["input_type"] = "axis"
                                settings.data["lanes"][lane_idx]["input_id"] = a
                                target_var.set(f"Axis {a}"); captured = True; break
                
                # ESC to cancel
                def on_esc(event):
                    nonlocal captured
                    if event.keysym.lower() == "escape":
                        target_var.set(old_val); captured = True
                root.bind("<Key>", on_esc)
                root.update()
                if captured: root.unbind("<Key>")
            if captured: break

    for i, lane in enumerate(settings.data["lanes"]):
        row = i + 1
        tk.Label(l_frame, text=lane['label'], bg=BG_COLOR, fg=ACCENT_COLOR, width=10).grid(row=row, column=0, pady=5)
        
        # Keyboard Column
        kv = tk.StringVar(value=lane.get('key', ''))
        tk.Button(l_frame, textvariable=kv, width=10, command=lambda v=kv, idx=i: record_input(v, idx)).grid(row=row, column=1, padx=5)

        # Controller Column
        initial_pad = f"{lane.get('input_type', 'button')} {lane.get('input_id', 0)}"
        if lane.get('input_type') == 'hat': initial_pad = f"Hat {lane.get('hat_val')}"
        
        bv = tk.StringVar(value=initial_pad)
        tk.Button(l_frame, textvariable=bv, width=12, command=lambda v=bv, idx=i: record_input(v, idx, True)).grid(row=row, column=2, padx=5)

        def pick_lane_color(idx=i):
            c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data["lanes"][idx]["color"]))
            if c[1]: settings.data["lanes"][idx]["color"] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

        tk.Button(l_frame, text="Color", command=pick_lane_color, width=8).grid(row=row, column=3, padx=5)
        lane_vars.append((kv, bv))

    def start_app():
        try: settings.data["fps"] = int(fps_var.get())
        except: settings.data["fps"] = 144
        for i, (k, b) in enumerate(lane_vars):
            settings.data["lanes"][i]["key"] = k.get()
        settings.save(); root.destroy()

    tk.Button(root, text="SAVE & LAUNCH OVERLAY", command=start_app, bg=ACCENT_COLOR, fg="black", font=("Arial", 11, "bold")).pack(pady=20)
    root.mainloop()

# --- Overlay Logic ---
def run_overlay(settings):
    pygame.init()
    data = settings.data
    
    has_audio = False
    if hasattr(pygame, 'mixer'):
        try:
            pygame.mixer.init()
            s_path = data.get("sound_path", "click.wav")
            if os.path.exists(s_path):
                sound = pygame.mixer.Sound(s_path)
                has_audio = True
        except: pass

    joystick = None
    if hasattr(pygame, 'joystick'):
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0); joystick.init()

    SCR_W, SCR_H = 1200, 100
    screen = pygame.display.set_mode((SCR_W, SCR_H))
    pygame.display.set_caption("Festival Overlay")
    clock = pygame.time.Clock()
    prev_states = [False] * len(data["lanes"])

    NORMAL_LW = 160
    OD_LW = 95
    GAP = 110

    while True:
        screen.fill(tuple(data["bg_color"]))
        if any(e.type == pygame.QUIT for e in pygame.event.get()): break

        keys = pygame.key.get_pressed()
        for i, lane in enumerate(data["lanes"]):
            pressed = False
            
            # Keyboard Check
            kn = lane.get("key", "")
            try:
                target_k = pygame.K_SPACE if kn == "space" else pygame.key.key_code(kn)
                if keys[target_k]: pressed = True
            except: pass
            
            # Controller Check
            if joystick:
                i_type = lane.get("input_type", "button")
                i_id = lane.get("input_id", 0)
                try:
                    if i_type == "button":
                        if joystick.get_button(i_id): pressed = True
                    elif i_type == "axis":
                        if abs(joystick.get_axis(i_id)) > 0.5: pressed = True
                    elif i_type == "hat":
                        if joystick.get_hat(i_id) == tuple(lane.get("hat_val", (0, 0))): pressed = True
                except: pass

            if pressed and not prev_states[i] and has_audio: sound.play()
            prev_states[i] = pressed

            # Drawing
            if i < 5:
                x = 40 + i * (NORMAL_LW + 15)
                rect = (x, 25, NORMAL_LW, SCR_H - 50)
            else:
                x = 40 + 5 * (NORMAL_LW + 15) + GAP
                rect = (x, 25, OD_LW, SCR_H - 50)

            color = tuple(lane["color"]) if pressed else tuple(data["off_color"])
            pygame.draw.rect(screen, color, rect, border_radius=6)
            if pressed:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=6)

        pygame.display.flip()
        clock.tick(data.get("fps", 144))
    pygame.quit()

if __name__ == "__main__":
    overlay_settings = OverlaySettings()
    open_settings(overlay_settings)
    run_overlay(overlay_settings)