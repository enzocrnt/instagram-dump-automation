import tkinter as tk
from tkinter import ttk, messagebox
import random

class InstagramAutomationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Photo Dump Pipeline")
        self.root.geometry("1100x650")
        self.root.configure(bg="#121212")
        
        # Style Configuration for Dark Mode
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#121212", foreground="#E0E0E0")
        self.style.configure("TLabel", background="#121212", foreground="#E0E0E0", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#FFFFFF")
        self.style.configure("Sub.TLabel", font=("Segoe UI", 11, "bold"), foreground="#A0A0A0")
        
        # Chronological State Tracking
        self.months = [
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ]
        self.current_month_idx = 0
        self.current_day = 1
        
        # Mock State for Photos and Standby Queue
        self.current_pool = []
        self.standby_batches = [] # Stores dicts: {"id": X, "date": Y, "photos": [...], "caption": ""}
        self.batch_counter = 1

        self.setup_layout()
        self.reroll_photos() # Initial load

    def setup_layout(self):
        # -----------------------------------------------------------------
        # LEFT COLUMN: PHASE 1 - THE CURATION DECK
        # -----------------------------------------------------------------
        left_frame = tk.Frame(self.root, bg="#1E1E1E", width=450, padx=15, pady=15)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
        
        ttk.Label(left_frame, text="Phase 1: Curation Deck", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        # Date Selectors Row
        date_frame = tk.Frame(left_frame, bg="#1E1E1E")
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="Month:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.month_var = tk.StringVar(value=self.months[self.current_month_idx])
        self.month_dropdown = ttk.Combobox(date_frame, textvariable=self.month_var, values=self.months, width=12, state="readonly")
        self.month_dropdown.grid(row=0, column=1, padx=5)
        self.month_dropdown.bind("<<ComboboxSelected>>", self.on_date_changed_manually)
        
        ttk.Label(date_frame, text="Day:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.day_var = tk.StringVar(value=str(self.current_day))
        self.day_dropdown = ttk.Combobox(date_frame, textvariable=self.day_var, values=[str(i) for i in range(1, 32)], width=5, state="readonly")
        self.day_dropdown.grid(row=0, column=3, padx=5)
        self.day_dropdown.bind("<<ComboboxSelected>>", self.on_date_changed_manually)

        # Gallery Thumbnail Grid Area (Placeholder Blocks)
        ttk.Label(left_frame, text="Staging Gallery Preview (Max 10 Items Logged)", style="Sub.TLabel").pack(anchor=tk.W, pady=(15, 5))
        
        self.gallery_frame = tk.Frame(left_frame, bg="#2D2D2D", bd=1, relief=tk.SOLID)
        self.gallery_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Action Buttons for Phase 1
        btn_frame = tk.Frame(left_frame, bg="#1E1E1E")
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="🔄 Reroll Day Pool", bg="#3A3A3A", fg="white", bd=0, padx=10, pady=8, command=self.reroll_photos).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame, text="📥 Save to Standby", bg="#007ACC", fg="white", bd=0, padx=10, pady=8, command=self.save_to_standby).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame, text="➡️ Next Day", bg="#3A3A3A", fg="white", bd=0, padx=10, pady=8, command=self.increment_day).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # -----------------------------------------------------------------
        # RIGHT COLUMN: PHASE 2 & 3 - STANDBY QUEUE & DEPLOYMENT
        # -----------------------------------------------------------------
        right_frame = tk.Frame(self.root, bg="#1E1E1E", width=600, padx=15, pady=15)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)
        
        ttk.Label(right_frame, text="Phase 2 & 3: Standby Queue & Deployment", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        # Container for vertical scrolling list of Standby Batches
        self.queue_canvas = tk.Canvas(right_frame, bg="#1E1E1E", highlightthickness=0)
        self.queue_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.queue_canvas.yview)
        self.scrollable_queue_frame = tk.Frame(self.queue_canvas, bg="#1E1E1E")
        
        self.scrollable_queue_frame.bind(
            "<Configure>",
            lambda e: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        )
        self.queue_canvas.create_window((0, 0), window=self.scrollable_queue_frame, anchor="nw", width=530)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)
        
        self.queue_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # -----------------------------------------------------------------
    # BACKEND CORE LOGIC PLACEHOLDERS
    # -----------------------------------------------------------------
    def render_gallery(self):
        """Clears and re-renders the thumbnail mockup items in the curation view."""
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
            
        # Displaying simulated grid blocks representing standard image arrays
        for idx, img_name in enumerate(self.current_pool):
            r = idx // 5
            c = idx % 5
            box = tk.Label(self.gallery_frame, text=img_name, bg="#4A4A4A", fg="#FFFFFF", width=9, height=4, bd=1, relief=tk.RAISED, font=("Segoe UI", 8))
            box.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

    def reroll_photos(self):
        """Simulates querying the target directory for files matching the date parameters."""
        m = self.month_var.get()
        d = self.day_var.get()
        
        # Mock random pool slice capped cleanly at the 10 item desktop carousel limit
        qty = random.randint(3, 10)
        self.current_pool = [f"IMG_{m[:3].upper()}{d}_{i+1:02d}.jpg" for i in range(qty)]
        self.render_gallery()

    def on_date_changed_manually(self, event):
        """Syncs the internal program state variables if user shifts dropdown selections directly."""
        self.current_month_idx = self.months.index(self.month_var.get())
        self.current_day = int(self.day_var.get())
        self.reroll_photos()

    def increment_day(self):
        """Advances the state tracking variables chronologically to the next calendar unit."""
        if self.current_day < 31:
            self.current_day += 1
        else:
            self.current_day = 1
            self.current_month_idx = (self.current_month_idx + 1) % 12
            
        self.month_var.set(self.months[self.current_month_idx])
        self.day_var.set(str(self.current_day))
        self.reroll_photos()

    def save_to_standby(self):
        """Locks current baseline file selection into a discrete standby deployment track."""
        if not self.current_pool:
            messagebox.showwarning("Empty Pool", "There are no images selected on this date to stage.")
            return
            
        new_batch = {
            "id": self.batch_counter,
            "date": f"{self.month_var.get()} {self.day_var.get()}",
            "photos": list(self.current_pool),
            "caption": ""
        }
        self.standby_batches.append(new_batch)
        self.batch_counter += 1
        
        # Trigger screen updates and auto-advance workflow focus block to the next day
        self.update_standby_ui()
        self.increment_day()

    def update_standby_ui(self):
        """Completely rebuilds the standalone queue blocks to match the active standby array."""
        for widget in self.scrollable_queue_frame.winfo_children():
            widget.destroy()
            
        if not self.standby_batches:
            lbl = ttk.Label(self.scrollable_queue_frame, text="No batches staged in standby. Curation Deck is ready.", font=("Segoe UI", 10, "italic"))
            lbl.pack(pady=20, anchor=tk.W)
            return

        for batch in self.standby_batches:
            card = tk.Frame(self.scrollable_queue_frame, bg="#252526", bd=1, relief=tk.SOLID, padx=10, pady=10)
            card.pack(fill=tk.X, pady=5, anchor=tk.W)
            
            # Left Sub-Info Panel (Meta Details)
            info_frame = tk.Frame(card, bg="#252526")
            info_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
            
            ttk.Label(info_frame, text=f"Batch #{batch['id']:03d}", font=("Segoe UI", 11, "bold"), background="#252526", foreground="#38E54D").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Source: {batch['date']}", font=("Segoe UI", 9), background="#252526", foreground="#A0A0A0").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Files: {len(batch['photos'])} items", font=("Segoe UI", 9), background="#252526").pack(anchor=tk.W)
            
            # Action controls within individual cards
            btn_deploy = tk.Button(info_frame, text="🚀 Upload Batch", bg="#28A745", fg="white", bd=0, font=("Segoe UI", 9, "bold"), pady=4, command=lambda b=batch: self.upload_batch_pipeline(b))
            btn_deploy.pack(anchor=tk.W, pady=(8, 0))
            
            # Right Sub-Panel (Manual Text Area Input)
            text_frame = tk.Frame(card, bg="#252526")
            text_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))
            
            ttk.Label(text_frame, text="Manual Caption Composition Context:", font=("Segoe UI", 8, "italic"), background="#252526", foreground="#888888").pack(anchor=tk.W)
            
            txt_box = tk.Text(text_frame, bg="#121212", fg="#FFFFFF", insertbackground="white", bd=0, height=4, width=40, font=("Segoe UI", 9))
            txt_box.pack(fill=tk.X, pady=2)
            txt_box.insert(tk.END, batch["caption"])
            
            # Sync text changes continuously back to state dictionary representation
            txt_box.bind("<KeyRelease>", lambda e, b=batch, t=txt_box: self.sync_caption(b, t))

    def sync_caption(self, batch, text_widget):
        """Captures localized manual string buffers inside the corresponding storage state."""
        batch["caption"] = text_widget.get("1.0", tk.END).strip()

    def upload_batch_pipeline(self, batch):
        """Fires the sequential system execution logic for the specific targeted folder."""
        # Verification layer confirmation prompt
        confirm = messagebox.askyesno(
            "Confirm Pipeline Push", 
            f"Launch Selenium Engine sequence for Batch #{batch['id']:03d}?\n\n"
            f"Staged Items: {len(batch['photos'])}\n"
            f"Caption Length: {len(batch['caption'])} characters"
        )
        if confirm:
            print(f"\n--- RUNNING UPLOADER PIPELINE FOR BATCH {batch['id']} ---")
            print(f"Targeting active Chrome profile session via Selenium...")
            print(f"Injecting files array sequentially: {batch['photos']}")
            print(f"Writing parsed rich-text element container: '{batch['caption']}'")
            print("Status code verified. Post successfully pushed.")
            
            # Complete execution lifetime closure: Update tracker DB array state, drop from queue
            self.standby_batches.remove(batch)
            self.update_standby_ui()
            messagebox.showinfo("Success", f"Batch #{batch['id']:03d} successfully deployed live. Staging files flushed.")

if __name__ == "__main__":
    app_root = tk.Tk()
    ui_instance = InstagramAutomationUI(app_root)
    app_root.mainloop()