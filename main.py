"""
Printer Service Tool — Dynamic, Multi-Brand Printer Utility
Supports: Epson, Brother (extensible to any brand)
Features:
  - Dynamic brand/model/action management (add from GUI)
  - Network auto-scan with progress
  - USB printer detection
  - Printer action dispatcher
  - Error code lookup (Epson & Brother)
  - Save/load printer database
  - Connection tester
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json
import os
import sys

# ── Paths ────────────────────────────────────────────────────────────────────
# Works both as a normal .py and as a PyInstaller frozen .exe
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_DIR = os.path.dirname(sys.executable)
    # Also add the _MEIPASS temp dir so bundled .py modules are importable
    sys.path.insert(0, sys._MEIPASS)
else:
    # Running as normal .py script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "configs", "printer_database.json")

# Auto-create configs folder and default DB if missing (first run on new PC)
if not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

if not os.path.exists(DB_PATH):
    _default_db = {
        "Epson": {
            "models": {
                "L3110": ["Clear Waste Ink Counter", "Printer Status", "Head Cleaning", "Nozzle Check"],
                "L120":  ["Clear Waste Ink Counter", "Printer Status"],
                "L5190": ["Clear Waste Ink Counter", "Printer Status", "Head Cleaning"],
                "ET-2720":["Clear Waste Ink Counter", "Printer Status", "Head Cleaning"]
            },
            "error_codes": {
                "E-01": {"meaning": "General printer error", "solution": "Turn off and on again. Check for paper or protective material inside."},
                "E-10": {"meaning": "Waste ink pad at end of service life", "solution": "Ink pad needs replacement by an authorized Epson service provider."},
                "E-11": {"meaning": "Ink pad needs replacement", "solution": "Contact Epson or an authorized service provider."},
                "0x97": {"meaning": "Internal hardware error", "solution": "Power cycle. If persists, professional servicing required."},
                "W-01": {"meaning": "Paper jam occurred", "solution": "Remove jammed paper and press button on LCD to clear the error."}
            }
        },
        "Brother": {
            "models": {
                "HL-L2320D":   ["Reset Toner", "Printer Status", "Drum Reset"],
                "DCP-L2540DW": ["Reset Toner", "Drum Reset", "Printer Status"]
            },
            "error_codes": {
                "46":  {"meaning": "Ink absorber pad full", "solution": "Contact Brother customer service for replacement."},
                "7D":  {"meaning": "Printer drum is dirty", "solution": "Clean the printer drum per your manual."},
                "CF":  {"meaning": "Toner cartridge container is full", "solution": "Empty waste toner container carefully."}
            }
        }
    }
    import json as _json
    with open(DB_PATH, 'w') as _f:
        _json.dump(_default_db, _f, indent=2)

sys.path.insert(0, BASE_DIR)

from network_scan   import scan_network, get_local_subnet
from printer_actions import run_action

# ── Colors / Theme ────────────────────────────────────────────────────────────
BG        = "#0f1117"
BG2       = "#1a1d27"
BG3       = "#22263a"
ACCENT    = "#00d4ff"
ACCENT2   = "#ff6b35"
SUCCESS   = "#00e676"
WARNING   = "#ffab40"
DANGER    = "#ff5252"
FG        = "#e8eaf6"
FG2       = "#8892b0"
BORDER    = "#2d3561"
FONT      = ("Consolas", 10)
FONT_BOLD = ("Consolas", 10, "bold")
FONT_LG   = ("Consolas", 13, "bold")
FONT_SM   = ("Consolas", 9)


# ═════════════════════════════════════════════════════════════════════════════
#  Database helper
# ═════════════════════════════════════════════════════════════════════════════
def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


# ═════════════════════════════════════════════════════════════════════════════
#  Styled widget helpers
# ═════════════════════════════════════════════════════════════════════════════
def styled_frame(parent, **kw):
    kw.setdefault("bg", BG2)
    kw.setdefault("relief", "flat")
    return tk.Frame(parent, **kw)

def styled_label(parent, text, color=FG, font=FONT, **kw):
    bg = kw.pop("bg", BG2)
    fg = kw.pop("fg", color)
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kw)

def styled_btn(parent, text, cmd, color=ACCENT, **kw):
    btn = tk.Button(
        parent, text=text, command=cmd,
        bg=BG3, fg=color, font=FONT_BOLD,
        relief="flat", bd=0, cursor="hand2",
        activebackground=BORDER, activeforeground=color,
        padx=10, pady=5, **kw
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=BORDER))
    btn.bind("<Leave>", lambda e: btn.config(bg=BG3))
    return btn

def styled_combo(parent, values=None, width=30, **kw):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
        fieldbackground=BG3, background=BG3,
        foreground=FG, selectbackground=BORDER,
        selectforeground=ACCENT, arrowcolor=ACCENT,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    cb = ttk.Combobox(parent, values=values or [], width=width,
                      style="Dark.TCombobox", font=FONT, **kw)
    return cb

def styled_entry(parent, width=30, **kw):
    return tk.Entry(parent, width=width, bg=BG3, fg=FG,
                    font=FONT, insertbackground=ACCENT,
                    relief="flat", bd=4, **kw)

def section_header(parent, title, bg=BG2):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=(10, 4))
    tk.Label(row, text="▸ " + title, bg=bg, fg=ACCENT,
             font=FONT_BOLD).pack(side="left", padx=8)
    tk.Frame(row, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=8)
    return row


# ═════════════════════════════════════════════════════════════════════════════
#  Main Application
# ═════════════════════════════════════════════════════════════════════════════
class PrinterTool:

    def __init__(self, root):
        self.root = root
        self.root.title("Printer Service Tool v2.0")
        self.root.geometry("980x720")
        self.root.configure(bg=BG)
        self.root.minsize(860, 600)

        self.db = load_db()
        self._scan_thread = None

        self._build_ui()

    # ─── UI Layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top bar
        self._build_topbar()

        # Notebook tabs
        nb_style = ttk.Style()
        nb_style.theme_use("clam")
        nb_style.configure("Dark.TNotebook",
            background=BG, borderwidth=0, tabmargins=[0,0,0,0])
        nb_style.configure("Dark.TNotebook.Tab",
            background=BG2, foreground=FG2, font=FONT_BOLD,
            padding=[14, 6])
        nb_style.map("Dark.TNotebook.Tab",
            background=[("selected", BG3)],
            foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0,8))

        self._build_tab_action()
        self._build_tab_scanner()
        self._build_tab_errors()
        self._build_tab_manage()

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = tk.Label(self.root, textvariable=self.status_var,
                          bg=BG3, fg=FG2, font=FONT_SM, anchor="w", padx=10)
        status.pack(fill="x", side="bottom")

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=BG3, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="🖨  PRINTER SERVICE TOOL",
                 bg=BG3, fg=ACCENT, font=("Consolas", 14, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(bar, text="v2.0 | Multi-Brand | Network & USB",
                 bg=BG3, fg=FG2, font=FONT_SM).pack(side="left", padx=4)

        # Quick IP entry in topbar
        tk.Label(bar, text="Printer IP:", bg=BG3, fg=FG2, font=FONT).pack(side="right", padx=(0,4))
        self.ip_var = tk.StringVar(value="192.168.1.")
        self.ip_entry = styled_entry(bar, width=18, textvariable=self.ip_var)
        self.ip_entry.pack(side="right", padx=(0,10), pady=10)
        tk.Label(bar, text="Port:", bg=BG3, fg=FG2, font=FONT).pack(side="right", padx=(0,2))
        self.port_var = tk.StringVar(value="9100")
        styled_entry(bar, width=6, textvariable=self.port_var).pack(side="right", padx=(0,6))

    # ─── Tab 1: Run Actions ───────────────────────────────────────────────────
    def _build_tab_action(self):
        tab = styled_frame(self.root, bg=BG)
        self.nb.add(tab, text="  ⚡ Run Action  ")

        left = styled_frame(tab, bg=BG2)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        left.pack_propagate(False)
        left.config(width=300)

        section_header(left, "Printer Selection", BG2)

        # Brand
        styled_label(left, "Brand:", bg=BG2, fg=FG2).pack(anchor="w", padx=10, pady=(4,0))
        self.brand_var = tk.StringVar()
        self.brand_cb  = styled_combo(left, list(self.db.keys()), width=28,
                                      textvariable=self.brand_var)
        self.brand_cb.pack(padx=10, pady=3)
        self.brand_cb.bind("<<ComboboxSelected>>", self._on_brand)

        # Model
        styled_label(left, "Model:", bg=BG2, fg=FG2).pack(anchor="w", padx=10, pady=(4,0))
        self.model_var = tk.StringVar()
        self.model_cb  = styled_combo(left, width=28, textvariable=self.model_var)
        self.model_cb.pack(padx=10, pady=3)
        self.model_cb.bind("<<ComboboxSelected>>", self._on_model)

        # Action
        styled_label(left, "Action:", bg=BG2, fg=FG2).pack(anchor="w", padx=10, pady=(4,0))
        self.action_var = tk.StringVar()
        self.action_cb  = styled_combo(left, width=28, textvariable=self.action_var)
        self.action_cb.pack(padx=10, pady=3)

        section_header(left, "Connection", BG2)

        # IP from scanner
        styled_label(left, "Use detected IP:", bg=BG2, fg=FG2).pack(anchor="w", padx=10)
        self.detected_var = tk.StringVar()
        self.detected_cb  = styled_combo(left, width=28, textvariable=self.detected_var)
        self.detected_cb.pack(padx=10, pady=3)
        self.detected_cb.bind("<<ComboboxSelected>>",
                              lambda e: self.ip_var.set(self.detected_var.get()))

        tk.Frame(left, bg=BG2).pack(expand=True, fill="y")

        # Test connection
        styled_btn(left, "🔌  Test Connection", self._test_connection,
                   color=WARNING).pack(fill="x", padx=10, pady=4)
        # Run
        run_btn = styled_btn(left, "▶  RUN ACTION", self._run_action, color=SUCCESS)
        run_btn.config(font=("Consolas", 11, "bold"), pady=10)
        run_btn.pack(fill="x", padx=10, pady=(4,10))

        # Right: Output log
        right = styled_frame(tab, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)

        section_header(right, "Output Log", BG)
        self.log = tk.Text(right, bg=BG2, fg=FG, font=FONT, relief="flat",
                           bd=0, wrap="word", state="disabled",
                           insertbackground=ACCENT)
        scroll = ttk.Scrollbar(right, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True, padx=(8,0))

        # Tag colors
        self.log.tag_config("info",    foreground=FG)
        self.log.tag_config("success", foreground=SUCCESS)
        self.log.tag_config("warning", foreground=WARNING)
        self.log.tag_config("error",   foreground=DANGER)
        self.log.tag_config("accent",  foreground=ACCENT)
        self.log.tag_config("dim",     foreground=FG2)

        btn_row = tk.Frame(right, bg=BG)
        btn_row.pack(fill="x", padx=8, pady=4)
        styled_btn(btn_row, "Clear Log", self._clear_log, color=FG2).pack(side="right")

        self._log("Printer Service Tool started.\n", "accent")
        self._log("Select a brand, model, and action, enter the printer IP, then click RUN ACTION.\n", "dim")

    # ─── Tab 2: Network Scanner ───────────────────────────────────────────────
    def _build_tab_scanner(self):
        tab = styled_frame(self.root, bg=BG)
        self.nb.add(tab, text="  🔍 Network Scan  ")

        ctrl = styled_frame(tab, bg=BG2)
        ctrl.pack(fill="x", padx=8, pady=8)

        section_header(ctrl, "Network Scanner", BG2)

        row = tk.Frame(ctrl, bg=BG2)
        row.pack(fill="x", padx=10, pady=6)

        styled_label(row, "Subnet (e.g. 192.168.1):", bg=BG2).pack(side="left")
        self.subnet_var = tk.StringVar(value=get_local_subnet())
        styled_entry(row, width=18, textvariable=self.subnet_var).pack(side="left", padx=8)

        styled_label(row, "Port:", bg=BG2).pack(side="left")
        self.scan_port_var = tk.StringVar(value="9100")
        styled_entry(row, width=6, textvariable=self.scan_port_var).pack(side="left", padx=4)

        self.scan_btn = styled_btn(row, "🔍  Scan Network", self._start_scan, color=ACCENT)
        self.scan_btn.pack(side="left", padx=12)

        styled_btn(row, "USB Detect", self._usb_detect, color=WARNING).pack(side="left")

        # Progress
        prog_row = tk.Frame(ctrl, bg=BG2)
        prog_row.pack(fill="x", padx=10, pady=(0,6))
        self.scan_progress = ttk.Progressbar(prog_row, mode="determinate", length=400)
        self.scan_progress.pack(side="left")
        self.scan_status = styled_label(prog_row, "  Idle", bg=BG2, fg=FG2)
        self.scan_status.pack(side="left", padx=8)

        # Results table
        cols = ("IP Address", "Hostname", "Status")
        frame = styled_frame(tab, bg=BG)
        frame.pack(fill="both", expand=True, padx=8, pady=(0,8))

        style = ttk.Style()
        style.configure("Dark.Treeview",
            background=BG2, fieldbackground=BG2,
            foreground=FG, rowheight=24, font=FONT,
            bordercolor=BORDER)
        style.configure("Dark.Treeview.Heading",
            background=BG3, foreground=ACCENT, font=FONT_BOLD)
        style.map("Dark.Treeview", background=[("selected", BORDER)])

        self.scan_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                       style="Dark.Treeview")
        for c in cols:
            self.scan_tree.heading(c, text=c)
        self.scan_tree.column("IP Address", width=160)
        self.scan_tree.column("Hostname",   width=220)
        self.scan_tree.column("Status",     width=120)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.scan_tree.pack(fill="both", expand=True)
        self.scan_tree.bind("<Double-1>", self._use_scanned_ip)

        hint = styled_label(tab, "Double-click a result to use that IP in Run Action tab.",
                            bg=BG, fg=FG2, font=FONT_SM)
        hint.pack(pady=2)

    # ─── Tab 3: Error Code Lookup ─────────────────────────────────────────────
    def _build_tab_errors(self):
        tab = styled_frame(self.root, bg=BG)
        self.nb.add(tab, text="  ❗ Error Codes  ")

        ctrl = styled_frame(tab, bg=BG2)
        ctrl.pack(fill="x", padx=8, pady=8)
        section_header(ctrl, "Error Code Lookup", BG2)

        row = tk.Frame(ctrl, bg=BG2)
        row.pack(fill="x", padx=10, pady=6)

        styled_label(row, "Brand:", bg=BG2).pack(side="left")
        self.err_brand_var = tk.StringVar()
        brands_with_errors = [b for b in self.db if "error_codes" in self.db[b]]
        err_brand_cb = styled_combo(row, brands_with_errors, width=14,
                                    textvariable=self.err_brand_var)
        err_brand_cb.pack(side="left", padx=8)

        styled_label(row, "Code:", bg=BG2).pack(side="left")
        self.err_code_var = tk.StringVar()
        styled_entry(row, width=12, textvariable=self.err_code_var).pack(side="left", padx=4)

        styled_btn(row, "Look Up", self._lookup_error, color=ACCENT).pack(side="left", padx=8)
        styled_btn(row, "Show All", self._show_all_errors, color=FG2).pack(side="left")

        # Error result area
        self.err_result = tk.Text(tab, bg=BG2, fg=FG, font=FONT,
                                  relief="flat", bd=0, state="disabled", wrap="word")
        self.err_result.tag_config("code",     foreground=ACCENT,   font=FONT_BOLD)
        self.err_result.tag_config("meaning",  foreground=WARNING,  font=FONT)
        self.err_result.tag_config("solution", foreground=SUCCESS,   font=FONT)
        self.err_result.tag_config("header",   foreground=ACCENT2,  font=FONT_BOLD)
        self.err_result.tag_config("dim",      foreground=FG2,      font=FONT_SM)

        esb = ttk.Scrollbar(tab, command=self.err_result.yview)
        self.err_result.configure(yscrollcommand=esb.set)
        esb.pack(side="right", fill="y", padx=(0,8), pady=(0,8))
        self.err_result.pack(fill="both", expand=True, padx=(8,0), pady=(0,8))

        self._err_write("Select a brand and enter an error code, or click 'Show All'.\n\n", "dim")

    # ─── Tab 4: Manage Database ───────────────────────────────────────────────
    def _build_tab_manage(self):
        tab = styled_frame(self.root, bg=BG)
        self.nb.add(tab, text="  ⚙ Manage  ")

        left = styled_frame(tab, bg=BG2)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        left.pack_propagate(False)
        left.config(width=300)

        section_header(left, "Add Brand / Model / Action", BG2)

        styled_label(left, "Brand Name:", bg=BG2, fg=FG2).pack(anchor="w", padx=10, pady=(6,0))
        self.mgmt_brand_var = tk.StringVar()
        styled_entry(left, width=28, textvariable=self.mgmt_brand_var).pack(padx=10, pady=3)
        styled_btn(left, "+ Add Brand", self._add_brand, color=SUCCESS).pack(fill="x", padx=10, pady=3)

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=10, pady=8)

        styled_label(left, "Model Name:", bg=BG2, fg=FG2).pack(anchor="w", padx=10, pady=(0,0))
        self.mgmt_model_var = tk.StringVar()
        styled_entry(left, width=28, textvariable=self.mgmt_model_var).pack(padx=10, pady=3)
        styled_btn(left, "+ Add Model to Selected Brand",
                   self._add_model, color=WARNING).pack(fill="x", padx=10, pady=3)

        tk.Frame(left, bg=BORDER, height=1).pack(fill="x", padx=10, pady=8)

        styled_label(left, "Action Name:", bg=BG2, fg=FG2).pack(anchor="w", padx=10)
        self.mgmt_action_var = tk.StringVar()
        styled_entry(left, width=28, textvariable=self.mgmt_action_var).pack(padx=10, pady=3)
        styled_btn(left, "+ Add Action to Selected Model",
                   self._add_action, color=ACCENT).pack(fill="x", padx=10, pady=3)

        tk.Frame(left, bg=BG2).pack(expand=True, fill="y")

        styled_btn(left, "💾  Save Database", self._save_db, color=SUCCESS).pack(
            fill="x", padx=10, pady=(0,6))
        styled_btn(left, "🔄  Reload Database", self._reload_db, color=FG2).pack(
            fill="x", padx=10, pady=(0,10))

        # Right: tree view of DB
        right = styled_frame(tab, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0,8), pady=8)
        section_header(right, "Current Database", BG)

        style = ttk.Style()
        style.configure("Mgmt.Treeview",
            background=BG2, fieldbackground=BG2,
            foreground=FG, rowheight=22, font=FONT,
            bordercolor=BORDER)
        style.configure("Mgmt.Treeview.Heading",
            background=BG3, foreground=ACCENT, font=FONT_BOLD)
        style.map("Mgmt.Treeview", background=[("selected", BORDER)])

        self.db_tree = ttk.Treeview(right, style="Mgmt.Treeview")
        self.db_tree.heading("#0", text="Printer Database")
        vsb2 = ttk.Scrollbar(right, command=self.db_tree.yview)
        self.db_tree.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y")
        self.db_tree.pack(fill="both", expand=True, padx=(8,0))

        btn_row = tk.Frame(right, bg=BG)
        btn_row.pack(fill="x", padx=8, pady=4)
        styled_btn(btn_row, "🗑 Delete Selected", self._delete_selected,
                   color=DANGER).pack(side="left")

        self._refresh_db_tree()

    # ─── Callbacks ────────────────────────────────────────────────────────────
    def _on_brand(self, event=None):
        brand = self.brand_var.get()
        if brand in self.db:
            models = list(self.db[brand].get("models", {}).keys())
            self.model_cb["values"] = models
            self.model_var.set("")
            self.action_cb["values"] = []
            self.action_var.set("")

    def _on_model(self, event=None):
        brand = self.brand_var.get()
        model = self.model_var.get()
        if brand in self.db and model in self.db[brand].get("models", {}):
            actions = self.db[brand]["models"][model]
            self.action_cb["values"] = actions
            self.action_var.set("")

    def _run_action(self):
        brand  = self.brand_var.get().strip()
        model  = self.model_var.get().strip()
        action = self.action_var.get().strip()
        ip     = self.ip_var.get().strip()
        port   = self._get_port()

        if not all([brand, model, action, ip]):
            messagebox.showwarning("Missing Fields",
                "Please select brand, model, action, and enter a printer IP.")
            return

        self._log(f"\n{'─'*50}\n", "dim")
        self._log(f"  Brand:  {brand}\n", "accent")
        self._log(f"  Model:  {model}\n", "accent")
        self._log(f"  Action: {action}\n", "accent")
        self._log(f"  IP:     {ip}:{port}\n", "accent")
        self._log(f"{'─'*50}\n", "dim")
        self.status_var.set(f"Running: {action} on {brand} {model} ({ip})…")

        def worker():
            result = run_action(brand, action, ip, port)
            tag = "success" if result.startswith("✅") else "error"
            self.root.after(0, lambda: self._log(f"  {result}\n", tag))
            self.root.after(0, lambda: self.status_var.set(f"Done: {action}"))

        threading.Thread(target=worker, daemon=True).start()

    def _test_connection(self):
        import socket
        ip   = self.ip_var.get().strip()
        port = self._get_port()
        self._log(f"\n🔌 Testing connection to {ip}:{port}…\n", "accent")

        def worker():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                r = s.connect_ex((ip, port))
                s.close()
                if r == 0:
                    self.root.after(0, lambda: self._log(
                        f"✅ Connection OK — {ip}:{port} is reachable.\n", "success"))
                else:
                    self.root.after(0, lambda: self._log(
                        f"❌ Cannot reach {ip}:{port}. Check IP and that printer is on.\n", "error"))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self._log(f"❌ Error: {m}\n", "error"))

        threading.Thread(target=worker, daemon=True).start()

    # ─── Network scan ─────────────────────────────────────────────────────────
    def _start_scan(self):
        if self._scan_thread and self._scan_thread.is_alive():
            return
        subnet = self.subnet_var.get().strip()
        try:
            port = int(self.scan_port_var.get())
        except ValueError:
            port = 9100

        for row in self.scan_tree.get_children():
            self.scan_tree.delete(row)

        self.scan_btn.config(state="disabled")
        self.scan_status.config(text="  Scanning…", fg=WARNING)
        self.scan_progress["value"] = 0

        def worker():
            def progress(done, total):
                pct = int(done / total * 100)
                self.root.after(0, lambda: self.scan_progress.configure(value=pct))
                self.root.after(0, lambda: self.scan_status.config(
                    text=f"  {done}/{total}"))

            results = scan_network(subnet, port, progress)

            def finish():
                self.scan_btn.config(state="normal")
                self.scan_progress["value"] = 100
                if results:
                    detected_ips = []
                    for r in results:
                        self.scan_tree.insert("", "end",
                            values=(r["ip"], r["hostname"] or "—", "✅ Online"))
                        detected_ips.append(r["ip"])
                    self.detected_cb["values"] = detected_ips
                    self.scan_status.config(
                        text=f"  Found {len(results)} printer(s)", fg=SUCCESS)
                    self._log(f"\n🔍 Scan complete. Found {len(results)} printer(s):\n", "accent")
                    for r in results:
                        self._log(f"   {r['ip']}  {r['hostname']}\n", "success")
                else:
                    self.scan_status.config(text="  No printers found", fg=DANGER)
                    self._log("\n🔍 Scan complete. No printers found on port 9100.\n", "warning")

            self.root.after(0, finish)

        self._scan_thread = threading.Thread(target=worker, daemon=True)
        self._scan_thread.start()

    def _use_scanned_ip(self, event):
        sel = self.scan_tree.selection()
        if sel:
            ip = self.scan_tree.item(sel[0])["values"][0]
            self.ip_var.set(ip)
            self.status_var.set(f"IP set to {ip}")
            self.nb.select(0)

    def _usb_detect(self):
        try:
            import usb.core
            devices = usb.core.find(find_all=True)
            for row in self.scan_tree.get_children():
                self.scan_tree.delete(row)
            count = 0
            for dev in devices:
                vid = hex(dev.idVendor)
                pid = hex(dev.idProduct)
                self.scan_tree.insert("", "end",
                    values=(f"USB {vid}:{pid}", "USB Device", "🔌 USB"))
                count += 1
            self.scan_status.config(text=f"  {count} USB device(s)", fg=SUCCESS)
        except ImportError:
            messagebox.showinfo("USB Detect",
                "pyusb not installed.\nRun: pip install pyusb\n\n"
                "On Windows, also install Zadig driver.")
        except Exception as e:
            messagebox.showerror("USB Error", str(e))

    # ─── Error code lookup ────────────────────────────────────────────────────
    def _lookup_error(self):
        brand = self.err_brand_var.get().strip()
        code  = self.err_code_var.get().strip().upper()

        if not brand or not code:
            messagebox.showwarning("Input", "Please select a brand and enter an error code.")
            return

        err_db = self.db.get(brand, {}).get("error_codes", {})
        # Flexible match: exact or starts-with
        match = err_db.get(code) or next(
            (v for k, v in err_db.items() if code in k.upper() or k.upper() in code), None)

        self.err_result.config(state="normal")
        self.err_result.delete("1.0", "end")
        if match:
            self._err_write(f"  [{brand}] Error Code: {code}\n\n", "header")
            self._err_write(f"  Meaning:\n    {match['meaning']}\n\n", "meaning")
            self._err_write(f"  Solution:\n    {match['solution']}\n", "solution")
        else:
            self._err_write(f"  No entry found for code '{code}' in {brand}.\n", "dim")
            self._err_write("  Try 'Show All' to browse all codes.\n", "dim")
        self.err_result.config(state="disabled")

    def _show_all_errors(self):
        brand = self.err_brand_var.get().strip()
        if not brand:
            messagebox.showwarning("Input", "Please select a brand.")
            return
        err_db = self.db.get(brand, {}).get("error_codes", {})

        self.err_result.config(state="normal")
        self.err_result.delete("1.0", "end")
        self._err_write(f"  All Error Codes — {brand}\n", "header")
        self._err_write(f"  {'─'*60}\n", "dim")
        for code, info in err_db.items():
            self._err_write(f"\n  [{code}]\n", "code")
            self._err_write(f"    {info['meaning']}\n", "meaning")
            self._err_write(f"    → {info['solution']}\n", "solution")
        self.err_result.config(state="disabled")

    # ─── Manage DB ────────────────────────────────────────────────────────────
    def _add_brand(self):
        name = self.mgmt_brand_var.get().strip()
        if not name:
            return
        if name not in self.db:
            self.db[name] = {"models": {}, "error_codes": {}}
            self._refresh_all()
            self.status_var.set(f"Brand '{name}' added.")
        else:
            messagebox.showinfo("Exists", f"Brand '{name}' already exists.")

    def _add_model(self):
        brand = self._selected_branch_brand()
        name  = self.mgmt_model_var.get().strip()
        if not brand or not name:
            messagebox.showwarning("Select", "Select a brand node in the tree and enter a model name.")
            return
        self.db[brand].setdefault("models", {})[name] = []
        self._refresh_all()
        self.status_var.set(f"Model '{name}' added to {brand}.")

    def _add_action(self):
        brand, model = self._selected_branch_brand_model()
        name = self.mgmt_action_var.get().strip()
        if not brand or not model or not name:
            messagebox.showwarning("Select",
                "Select a model node in the tree and enter an action name.")
            return
        actions = self.db[brand]["models"].get(model, [])
        if name not in actions:
            actions.append(name)
            self.db[brand]["models"][model] = actions
            self._refresh_all()
            self.status_var.set(f"Action '{name}' added to {brand}/{model}.")

    def _delete_selected(self):
        sel = self.db_tree.selection()
        if not sel:
            return
        item = self.db_tree.item(sel[0])
        text = item["text"]
        parent = self.db_tree.parent(sel[0])
        grandparent = self.db_tree.parent(parent) if parent else None

        if not messagebox.askyesno("Delete", f"Delete '{text}'?"):
            return

        if not parent:  # brand node
            self.db.pop(text, None)
        elif not grandparent:  # model node
            brand = self.db_tree.item(parent)["text"]
            self.db[brand]["models"].pop(text, None)
        else:  # action node
            model = self.db_tree.item(parent)["text"]
            brand = self.db_tree.item(grandparent)["text"]
            acts  = self.db[brand]["models"].get(model, [])
            if text in acts:
                acts.remove(text)

        self._refresh_all()
        self.status_var.set(f"Deleted '{text}'.")

    def _save_db(self):
        save_db(self.db)
        self.status_var.set("Database saved.")
        messagebox.showinfo("Saved", "Printer database saved successfully.")

    def _reload_db(self):
        self.db = load_db()
        self._refresh_all()
        self.status_var.set("Database reloaded.")

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _refresh_all(self):
        self._refresh_db_tree()
        brands = list(self.db.keys())
        self.brand_cb["values"] = brands
        self.brand_var.set("")
        self.model_cb["values"] = []
        self.action_cb["values"] = []
        err_brands = [b for b in self.db if "error_codes" in self.db[b]]
        # update error brand combo if possible
        try:
            self.err_result.master.nametowidget(
                self.err_result.master.children)
        except Exception:
            pass

    def _refresh_db_tree(self):
        for item in self.db_tree.get_children():
            self.db_tree.delete(item)
        for brand, bdata in self.db.items():
            b_node = self.db_tree.insert("", "end", text=brand, open=True)
            for model, actions in bdata.get("models", {}).items():
                m_node = self.db_tree.insert(b_node, "end", text=model, open=False)
                for act in actions:
                    self.db_tree.insert(m_node, "end", text=act)

    def _selected_branch_brand(self):
        sel = self.db_tree.selection()
        if not sel:
            return None
        item = sel[0]
        # Walk up to top-level (brand)
        while self.db_tree.parent(item):
            item = self.db_tree.parent(item)
        brand = self.db_tree.item(item)["text"]
        return brand if brand in self.db else None

    def _selected_branch_brand_model(self):
        sel = self.db_tree.selection()
        if not sel:
            return None, None
        item = sel[0]
        parent = self.db_tree.parent(item)
        if not parent:
            return None, None
        grandparent = self.db_tree.parent(parent)
        if grandparent:
            # selected an action node — go up to model
            model_item = parent
            brand_item = grandparent
        else:
            model_item = item
            brand_item = parent
        brand = self.db_tree.item(brand_item)["text"]
        model = self.db_tree.item(model_item)["text"]
        return brand, model

    def _get_port(self):
        try:
            return int(self.port_var.get())
        except ValueError:
            return 9100

    def _log(self, msg, tag="info"):
        self.log.config(state="normal")
        self.log.insert("end", msg, tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _err_write(self, msg, tag="info"):
        self.err_result.config(state="normal")
        self.err_result.insert("end", msg, tag)
        self.err_result.config(state="disabled")


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app  = PrinterTool(root)
    root.mainloop()
