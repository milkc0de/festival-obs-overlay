import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog
import pygame
import time

# --- Platform Specific Setup ---
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import ctypes

# --- Configuration ---
CONFIG_FILE = "overlay_config.json"

class OverlaySettings:
    """Handles persistent user configuration."""
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

# --- Background Input Helper (Windows) ---
def is_key_pressed_win32(key_name):
    if not IS_WINDOWS: return False
    VK_MAP = {"d": 0x44, "f": 0x46, "j": 0x4A, "k": 0x4B, "l": 0x4C, "space": 0x20, "escape": 0x1B}
    vk = VK_MAP.get(key_name.lower())
    if vk:
        return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0
    return False

# --- GUI Configurator ---
def open_settings(settings):
    root = tk.Tk()
    root.title("Festival Overlay Config")
    root.geometry("640x600")
    
    BG_DARK = "#121212"; FG_WHITE = "#ffffff"; ACCENT = "#00ff78"
    root.configure(bg=BG_DARK)

    # --- Global Config Area ---
    g_frame = tk.LabelFrame(root, text="Global Settings", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    g_frame.pack(fill="x", padx=20, pady=10)

    # Sound Setup
    sound_var = tk.StringVar(value=os.path.basename(settings.data.get("sound_path", "click.wav")))
    def select_file():
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            sound_var.set(os.path.basename(path)); settings.data["sound_path"] = path

    tk.Label(g_frame, text="SFX:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=0, sticky="w")
    tk.Entry(g_frame, textvariable=sound_var, width=15, state="readonly").grid(row=0, column=1, padx=5)
    tk.Button(g_frame, text="Browse", command=select_file).grid(row=0, column=2)

    # Performance
    tk.Label(g_frame, text="FPS:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=3, padx=(15, 0))
    fps_var = tk.StringVar(value=str(settings.data.get("fps", 144)))
    tk.Entry(g_frame, textvariable=fps_var, width=5).grid(row=0, column=4, padx=5)

    def pick_color(key):
        c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data[key]))
        if c[1]: settings.data[key] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

    tk.Button(g_frame, text="Background Color", command=lambda: pick_color("bg_color")).grid(row=1, column=0, pady=10)
    tk.Button(g_frame, text="Note Off Color", command=lambda: pick_color("off_color")).grid(row=1, column=1, pady=10)

    # --- Lane Bindings Area ---
    l_frame = tk.LabelFrame(root, text="Lane Bindings (ESC to cancel)", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    l_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Lane", "Keyboard", "Controller", "Color"]
    for i, txt in enumerate(headers):
        tk.Label(l_frame, text=txt, font=("Arial", 9, "bold"), bg=BG_DARK, fg="#666666").grid(row=0, column=i, sticky="ew")

    # Joystick Init for Config
    pygame.init()
    if hasattr(pygame, 'joystick'):
        pygame.joystick.init()
        joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if joy: joy.init()

    lane_vars = []

    def record_input(target_var, lane_idx, is_pad=False):
        old_val = target_var.get()
        target_var.set("WAITING...")
        root.update()
        
        pygame.event.pump()
        # Take snapshot of current axis state to handle drift/triggers
        ref_axes = [joy.get_axis(i) for i in range(joy.get_numaxes())] if (is_pad and joy) else []
        
        time.sleep(0.3)
        target_var.set("REC...")
        root.update()

        captured = False
        while not captured:
            pygame.event.pump()
            if not is_pad:
                def on_key(event):
                    nonlocal captured
                    kn = event.keysym.lower()
                    if kn == "escape": target_var.set(old_val)
                    else: target_var.set(kn)
                    captured = True
                root.bind("<Key>", on_key); root.wait_variable(target_var); root.unbind("<Key>")
            else:
                if joy:
                    # Check Buttons
                    for b in range(joy.get_numbuttons()):
                        if joy.get_button(b):
                            settings.data["lanes"][lane_idx]["input_type"] = "button"
                            settings.data["lanes"][lane_idx]["input_id"] = b
                            target_var.set(f"Btn {b}"); captured = True; break
                    # Check Hats (D-pad)
                    if not captured:
                        for h in range(joy.get_numhats()):
                            if joy.get_hat(h) != (0, 0):
                                settings.data["lanes"][lane_idx]["input_type"] = "hat"
                                settings.data["lanes"][lane_idx]["input_id"] = h
                                settings.data["lanes"][lane_idx]["hat_val"] = joy.get_hat(h)
                                target_var.set(f"Hat {joy.get_hat(h)}"); captured = True; break
                    # Check Axes (Sticks/Triggers)
                    if not captured:
                        for a in range(joy.get_numaxes()):
                            if abs(joy.get_axis(a) - ref_axes[a]) > 0.6:
                                settings.data["lanes"][lane_idx]["input_type"] = "axis"
                                settings.data["lanes"][lane_idx]["input_id"] = a
                                target_var.set(f"Axis {a}"); captured = True; break
                
                def on_esc(event):
                    nonlocal captured
                    if event.keysym.lower() == "escape": target_var.set(old_val); captured = True
                root.bind("<Key>", on_esc); root.update()
                if captured: root.unbind("<Key>")
            if captured: break

    for i, lane in enumerate(settings.data["lanes"]):
        row = i + 1
        tk.Label(l_frame, text=lane['label'], bg=BG_DARK, fg=ACCENT, width=10).grid(row=row, column=0, pady=5)
        
        kv = tk.StringVar(value=lane.get('key', ''))
        tk.Button(l_frame, textvariable=kv, width=10, command=lambda v=kv, idx=i: record_input(v, idx)).grid(row=row, column=1, padx=5)
        
        initial_pad = f"{lane.get('input_type', 'button')} {lane.get('input_id', 0)}"
        if lane.get('input_type') == 'hat': initial_pad = f"Hat {lane.get('hat_val')}"
        bv = tk.StringVar(value=initial_pad)
        tk.Button(l_frame, textvariable=bv, width=12, command=lambda v=bv, idx=i: record_input(v, idx, True)).grid(row=row, column=2, padx=5)
        
        def pick_l_color(idx=i):
            c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data["lanes"][idx]["color"]))
            if c[1]: settings.data["lanes"][idx]["color"] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]
        tk.Button(l_frame, text="Pick Color", command=pick_l_color, width=8).grid(row=row, column=3, padx=5)
        lane_vars.append((kv, bv))

    def on_launch():
        try: settings.data["fps"] = int(fps_var.get())
        except: settings.data["fps"] = 144
        for i, (k, b) in enumerate(lane_vars): settings.data["lanes"][i]["key"] = k.get()
        settings.save(); root.destroy()

    tk.Button(root, text="SAVE & LAUNCH OVERLAY", command=on_launch, bg=ACCENT, fg="black", font=("Arial", 11, "bold")).pack(pady=20)
    root.mainloop()

# --- Main Application Loop ---
def run_overlay(settings):
    # CRITICAL: Allow background inputs for joysticks
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    pygame.init()
    data = settings.data
    
    # Audio setup
    has_audio = False
    if hasattr(pygame, 'mixer'):
        try:
            pygame.mixer.init()
            if os.path.exists(data.get("sound_path", "click.wav")):
                sound = pygame.mixer.Sound(data["sound_path"]); has_audio = True
        except: pass

    # Joystick setup
    joystick = None
    neutral_axes = []
    if hasattr(pygame, 'joystick'):
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            pygame.event.pump()
            # Capture startup axis states to prevent stick/trigger drift "stuck" state
            neutral_axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]

    screen = pygame.display.set_mode((1200, 100))
    pygame.display.set_caption("Overlay")
    clock = pygame.time.Clock()
    prev_states = [False] * len(data["lanes"])

    LW, OD_LW, GAP = 160, 95, 110

    while True:
        # Essential for Pygame to refresh event queue (even for joysticks)
        pygame.event.pump()
        
        screen.fill(tuple(data["bg_color"]))
        if any(e.type == pygame.QUIT for e in pygame.event.get()): break

        keys = pygame.key.get_pressed() if not IS_WINDOWS else None
        
        for i, lane in enumerate(data["lanes"]):
            pressed = False
            
            # 1. Keyboard Detection
            kn = lane.get("key", "")
            if IS_WINDOWS:
                if is_key_pressed_win32(kn): pressed = True
            else:
                try:
                    tk_key = pygame.K_SPACE if kn == "space" else pygame.key.key_code(kn)
                    if keys[tk_key]: pressed = True
                except: pass
            
            # 2. Joystick Detection
            if joystick:
                i_type = lane.get("input_type", "button")
                i_id = lane.get("input_id", 0)
                try:
                    if i_type == "button":
                        if joystick.get_button(i_id): pressed = True
                    elif i_type == "axis":
                        # Check relative to neutral startup position
                        if abs(joystick.get_axis(i_id) - neutral_axes[i_id]) > 0.5: pressed = True
                    elif i_type == "hat":
                        if joystick.get_hat(i_id) == tuple(lane.get("hat_val", (0, 0))): pressed = True
                except: pass

            if pressed and not prev_states[i] and has_audio: sound.play()
            prev_states[i] = pressed

            # Rendering Layout
            x = (50 + i * (LW + 15)) if i < 5 else (50 + 5 * (LW + 15) + GAP)
            rect = (x, 25, (LW if i < 5 else OD_LW), 50)
            c = tuple(lane["color"]) if pressed else tuple(data["off_color"])
            pygame.draw.rect(screen, c, rect, border_radius=6)
            if pressed: pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=6)

        pygame.display.flip()
        clock.tick(data.get("fps", 144))
    pygame.quit()

if __name__ == "__main__":
    s = OverlaySettings(); open_settings(s); run_overlay(s)