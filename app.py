import customtkinter as ctk
import threading
import os
import sys
from datetime import datetime
from PIL import Image, ImageGrab
import pystray
from pystray import MenuItem as item
from monitor import ClipboardMonitor

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class UltimateClipboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Ctrl+V Ultimate Suite")
        self.geometry("900x600")
        
        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Main content row

        self.monitor = ClipboardMonitor()
        self.monitor_thread = None
        self.history = []
        
        self.setup_ui()
        self.setup_tray()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def setup_ui(self):
        # --- Hero Header ---
        self.hero_frame = ctk.CTkFrame(self, height=100, corner_radius=0, fg_color="#1a1a1a")
        self.hero_frame.grid(row=0, column=0, sticky="ew")
        self.hero_frame.grid_columnconfigure(2, weight=1) # Push button to right

        # Logo/Title
        self.logo_label = ctk.CTkLabel(self.hero_frame, text="CTRL+V", font=ctk.CTkFont(family="Inter", size=32, weight="bold"), text_color="#3B8ED0")
        self.logo_label.grid(row=0, column=0, padx=30, pady=(20, 5), sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(self.hero_frame, text="Ultimate Productivity Suite", font=ctk.CTkFont(family="Inter", size=14), text_color="#aaaaaa")
        self.subtitle_label.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="w")

        # Action Button (Start/Stop)
        self.action_btn = ctk.CTkButton(self.hero_frame, text="START MONITORING", 
                                       command=self.toggle_monitoring, 
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       height=40, width=180,
                                       fg_color="#2CC985", hover_color="#229964")
        self.action_btn.grid(row=0, column=2, rowspan=2, padx=30, sticky="e")

        # --- Main Content ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(2, weight=1)

        # 1. Stat Cards
        self.create_stat_cards()

        # 2. Controls & Filter
        self.controls_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(20, 10))
        self.controls_frame.grid_columnconfigure(1, weight=1) # Search filler

        # Mode Segmented Button
        self.mode_label = ctk.CTkLabel(self.controls_frame, text="Active Mode:", font=ctk.CTkFont(size=12, weight="bold"))
        self.mode_label.pack(side="left", padx=(0, 10))
        
        self.mode_segment = ctk.CTkSegmentedButton(self.controls_frame, values=["General", "Links Only", "Smart Sorting"], 
                                                  command=self.change_mode)
        self.mode_segment.set("General")
        self.mode_segment.pack(side="left")

        # Search
        self.search_entry = ctk.CTkEntry(self.controls_frame, placeholder_text="🔍 Search history...", width=250)
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", self.filter_history)

        # 3. History List
        self.history_frame = ctk.CTkScrollableFrame(self.content_frame, label_text="Clipboard History", label_font=ctk.CTkFont(size=14, weight="bold"))
        self.history_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        
        # Initial Empty State
        self.empty_state_label = ctk.CTkLabel(self.history_frame, text="Waiting for captures...\nCopy something to see it here.", 
                                             font=ctk.CTkFont(size=16), text_color="#666666")
        self.empty_state_label.pack(pady=50)

        # Footer
        self.footer_frame = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a", corner_radius=0)
        self.footer_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_pill = ctk.CTkLabel(self.footer_frame, text="● STOPPED", text_color="#FF5555", font=ctk.CTkFont(size=11, weight="bold"))
        self.status_pill.pack(side="left", padx=20, pady=5)
        
        self.open_folder_btn = ctk.CTkButton(self.footer_frame, text="Open Captures Folder 📂", 
                                            command=self.open_folder, 
                                            fg_color="transparent", border_width=1, border_color="#555555",
                                            height=25, font=ctk.CTkFont(size=11))
        self.open_folder_btn.pack(side="right", padx=20, pady=5)

    def create_stat_cards(self):
        self.stats_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_container.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.stats_container.grid_columnconfigure((0,1,2), weight=1)

        # Helper to make cards
        def make_card(parent, title, icon, col):
            card = ctk.CTkFrame(parent, corner_radius=10)
            card.grid(row=0, column=col, padx=5, sticky="ew")
            
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=24)).pack(side="left", padx=20, pady=20)
            
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", pady=15)
            ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa").pack(anchor="w")
            lbl = ctk.CTkLabel(info, text="0", font=ctk.CTkFont(size=20, weight="bold"))
            lbl.pack(anchor="w")
            return lbl

        self.text_count_lbl = make_card(self.stats_container, "TEXT CLIPS", "📝", 0)
        self.link_count_lbl = make_card(self.stats_container, "LINKS SAVED", "🔗", 1)
        self.img_count_lbl  = make_card(self.stats_container, "IMAGES GRABBED", "🖼️", 2)

    def toggle_monitoring(self):
        if not self.monitor.is_running:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        self.monitor.is_running = True
        self.monitor_thread = threading.Thread(target=self.monitor.start, args=(self.on_capture,), daemon=True)
        self.monitor_thread.start()
        
        self.action_btn.configure(text="STOP MONITORING", fg_color="#FF5555", hover_color="#993333")
        self.status_pill.configure(text="● RUNNING", text_color="#55FF55")
        self.mode_segment.configure(state="disabled")

    def stop_monitoring(self):
        self.monitor.stop()
        self.action_btn.configure(text="START MONITORING", fg_color="#2CC985", hover_color="#229964")
        self.status_pill.configure(text="● STOPPED", text_color="#FF5555")
        self.mode_segment.configure(state="normal")

    def change_mode(self, mode):
        self.monitor.set_mode(mode)
        # Optional: Flash a toast or update description

    def on_capture(self, type, content):
        # Update Stats on Main Thread
        self.text_count_lbl.configure(text=str(self.monitor.stats['text']))
        self.link_count_lbl.configure(text=str(self.monitor.stats['links']))
        self.img_count_lbl.configure(text=str(self.monitor.stats['images']))

        # Update History
        timestamp = datetime.now().strftime("%H:%M:%S")
        if type == "image":
            display = f"🖼️ Image saved to {os.path.basename(str(content))}"
        else:
            clean_content = str(content).replace("\n", " ")
            display = f"{'🔗' if type=='text' and 'http' in str(content) else '📝'} {clean_content[:60]}..."
        
        self.history.insert(0, f"[{timestamp}] {display}")
        self.refresh_history_list()

    def refresh_history_list(self, query=""):
        # Clear current list
        for widget in self.history_frame.winfo_children():
            if widget != self.empty_state_label: # Keep the empty label reference if needed
                widget.destroy()

        filtered = [h for h in self.history if query.lower() in h.lower()]

        if not filtered:
            self.empty_state_label.pack(pady=50)
        else:
            self.empty_state_label.pack_forget()
            for item in filtered:
                # Create a sleek row for each item
                row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=item, anchor="w", font=ctk.CTkFont(family="Consolas", size=12)).pack(fill="x", padx=10)

    def filter_history(self, event):
        self.refresh_history_list(self.search_entry.get())

    def open_folder(self):
        os.startfile(".")

    # --- Tray Logic ---
    def setup_tray(self):
        try:
            image = Image.new('RGB', (64, 64), color=(44, 201, 133)) # Green icon
            menu = (item('Show', self.show_window), item('Exit', self.exit_app))
            self.icon = pystray.Icon("CtrlV", image, "Ctrl+V Ultimate", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()
        except:
            pass

    def show_window(self):
        self.deiconify()
        self.state('normal')

    def minimize_to_tray(self):
        self.withdraw()

    def exit_app(self):
        self.monitor.stop()
        if hasattr(self, 'icon'):
            self.icon.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = UltimateClipboardApp()
    app.mainloop()
