import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog
import pygame

# --- Config File Path ---
CONFIG_FILE = "overlay_config.json"

class OverlaySettings:
    """Handles loading and saving of the user configuration."""
    def __init__(self):
        self.load()

    def load(self):
        # Default layout configuration
        default_config = {
            "lanes": [
                {"label": "Lane 1", "color": [0, 255, 120], "key": "d", "btn_id": 13}, 
                {"label": "Lane 2", "color": [0, 255, 120], "key": "f", "btn_id": 14}, 
                {"label": "Lane 3", "color": [0, 255, 120], "key": "j", "btn_id": 2},  
                {"label": "Lane 4", "color": [0, 255, 120], "key": "k", "btn_id": 3},  
                {"label": "Lane 5", "color": [0, 255, 120], "key": "l", "btn_id": 1},  
                {"label": "OD",     "color": [255, 255, 0], "key": "space", "btn_id": 5} 
            ],
            "bg_color": [255, 0, 255], # Magenta for OBS Chroma Key
            "off_color": [20, 20, 20], # Neutral dark for inactive notes
            "sound_path": "click.wav", # Default sound file
            "fps": 144
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.data = json.load(f)
                    # Merge missing default keys into existing config
                    for k, v in default_config.items():
                        if k not in self.data: self.data[k] = v
            except: self.data = default_config
        else: self.data = default_config

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

# --- GUI Settings with Input Recording & ESC Support ---
def open_settings(settings):
    root = tk.Tk()
    root.title("Festival Overlay Config")
    root.geometry("600x580")
    
    # Dark Theme Colors
    BG_DARK = "#1a1a1a" 
    FG_WHITE = "#ffffff"
    ACCENT = "#00ff78"
    root.configure(bg=BG_DARK)

    # --- Global Settings ---
    g_frame = tk.LabelFrame(root, text="Global Settings", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    g_frame.pack(fill="x", padx=20, pady=10)

    # Sound Selection
    sound_var = tk.StringVar(value=os.path.basename(settings.data.get("sound_path", "click.wav")))
    def select_sound():
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            sound_var.set(os.path.basename(path))
            settings.data["sound_path"] = path

    tk.Label(g_frame, text="Sound:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=0, sticky="w")
    tk.Entry(g_frame, textvariable=sound_var, width=15, state="readonly").grid(row=0, column=1, padx=5)
    tk.Button(g_frame, text="Browse", command=select_sound).grid(row=0, column=2, padx=5)

    # FPS Control
    tk.Label(g_frame, text="FPS:", bg=BG_DARK, fg=FG_WHITE).grid(row=0, column=3, padx=(10, 0))
    fps_var = tk.StringVar(value=str(settings.data.get("fps", 144)))
    tk.Entry(g_frame, textvariable=fps_var, width=5).grid(row=0, column=4, padx=5)

    def pick_g_color(key):
        c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data[key]))
        if c[1]: settings.data[key] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

    tk.Button(g_frame, text="Chroma BG", command=lambda: pick_g_color("bg_color")).grid(row=1, column=0, pady=10)
    tk.Button(g_frame, text="Off Color", command=lambda: pick_g_color("off_color")).grid(row=1, column=1, pady=10)

    # --- Lane Bindings ---
    l_frame = tk.LabelFrame(root, text="Lane Bindings (Press ESC to cancel)", bg=BG_DARK, fg=FG_WHITE, padx=15, pady=10)
    l_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Lane", "Keyboard", "Controller", "Color"]
    for i, txt in enumerate(headers):
        tk.Label(l_frame, text=txt, font=("Arial", 9, "bold"), bg=BG_DARK, fg="#888888").grid(row=0, column=i, sticky="ew")

    # Initialize Controller support for recording
    pygame.init()
    if hasattr(pygame, 'joystick'):
        pygame.joystick.init()
        joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if joy: joy.init()

    lane_vars = []

    def record_input(target_var, is_pad=False):
        """Captures hardware input and updates the configuration variable."""
        old_val = target_var.get()
        target_var.set("REC...")
        root.update()
        captured = False
        
        while not captured:
            if not is_pad:
                def on_key(event):
                    nonlocal captured
                    key = event.keysym.lower()
                    if key == "escape": # Restore original on ESC
                        target_var.set(old_val)
                    else:
                        target_var.set(key)
                    captured = True
                root.bind("<Key>", on_key)
                root.wait_variable(target_var)
                root.unbind("<Key>")
            else:
                pygame.event.pump()
                if joy:
                    for b_id in range(joy.get_numbuttons()):
                        if joy.get_button(b_id):
                            target_var.set(str(b_id)); captured = True; break
                # Allow ESC to cancel controller recording too
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
        tk.Label(l_frame, text=lane['label'], bg=BG_DARK, fg=ACCENT, width=12).grid(row=row, column=0, pady=5)
        
        kv = tk.StringVar(value=lane.get('key', ''))
        tk.Button(l_frame, textvariable=kv, width=8, command=lambda v=kv: record_input(v)).grid(row=row, column=1, padx=5)

        bv = tk.StringVar(value=str(lane.get('btn_id', '0')))
        tk.Button(l_frame, textvariable=bv, width=8, command=lambda v=bv: record_input(v, True)).grid(row=row, column=2, padx=5)

        def pick_l_color(idx=i):
            c = colorchooser.askcolor(initialcolor='#%02x%02x%02x' % tuple(settings.data["lanes"][idx]["color"]))
            if c[1]: settings.data["lanes"][idx]["color"] = [int(c[1][j:j+2], 16) for j in (1, 3, 5)]

        tk.Button(l_frame, text="Pick Color", command=pick_l_color, width=10).grid(row=row, column=3, padx=5)
        lane_vars.append((kv, bv))

    def on_launch():
        """Saves values and closes GUI to start the overlay."""
        try: settings.data["fps"] = int(fps_var.get())
        except: settings.data["fps"] = 144
        for i, (k, b) in enumerate(lane_vars):
            settings.data["lanes"][i]["key"] = k.get()
            try: settings.data["lanes"][i]["btn_id"] = int(b.get())
            except: pass
        settings.save(); root.destroy()

    tk.Button(root, text="SAVE & LAUNCH OVERLAY", command=on_launch, bg=ACCENT, fg="black", font=("Arial", 11, "bold")).pack(pady=20)
    root.mainloop()

# --- Main Overlay Logic ---
def run_overlay(settings):
    pygame.init()
    data = settings.data
    
    # Audio setup (Safe initialization for Mac/Python 3.14 environments)
    has_audio = False
    if hasattr(pygame, 'mixer'):
        try:
            pygame.mixer.init()
            s_path = data.get("sound_path", "click.wav")
            if os.path.exists(s_path):
                sound = pygame.mixer.Sound(s_path)
                has_audio = True
        except: pass

    # Controller initialization
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

    # Layout constants
    LANE_WIDTH = 165
    OD_LANE_WIDTH = 90
    OD_GAP = 100

    while True:
        screen.fill(tuple(data["bg_color"]))
        if any(e.type == pygame.QUIT for e in pygame.event.get()): break

        keys = pygame.key.get_pressed()
        for i, lane in enumerate(data["lanes"]):
            pressed = False
            kn = lane.get("key", "")
            
            # Key check
            try:
                target_key = pygame.K_SPACE if kn == "space" else pygame.key.key_code(kn)
                if keys[target_key]: pressed = True
            except: pass
            
            # Controller button check
            if joystick:
                try:
                    if joystick.get_button(lane.get("btn_id", 0)): pressed = True
                except: pass

            # SFX Trigger
            if pressed and not prev_states[i] and has_audio: sound.play()
            prev_states[i] = pressed

            # Calculate screen position
            if i < 5:
                # Normal Lanes
                x = 50 + i * (LANE_WIDTH + 15)
                rect = (x, 20, LANE_WIDTH, SCR_H - 40)
            else:
                # Overdrive Lane (6th lane with a visual gap)
                x = 50 + 5 * (LANE_WIDTH + 15) + OD_GAP
                rect = (x, 20, OD_LANE_WIDTH, SCR_H - 40)

            # Draw note
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