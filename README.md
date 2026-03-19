# 🖨 Printer Service Tool v2.0

A dynamic, multi-brand printer service utility for technicians.

## Features
- ⚡ **Run Actions** — brand/model/action selection with IP entry
- 🔍 **Network Scan** — auto-detect printers on your subnet (multi-threaded, fast)
- 🔌 **USB Detection** — list connected USB printers (requires pyusb)
- ❗ **Error Code Lookup** — full Epson & Brother error code database
- ⚙ **Manage Database** — add/remove brands, models, and actions from the GUI
- 💾 **Persistent Database** — all changes saved to `configs/printer_database.json`

## Folder Structure
```
printer_tool/
├── main.py                  ← Run this
├── network_scan.py
├── printer_actions.py
├── configs/
│   └── printer_database.json
└── printers/
    ├── __init__.py
    ├── epson.py
    └── brother.py
```

## Requirements
```
pip install pyusb        # For USB detection (optional)
```
Python 3.8+ and tkinter (included with Python on Windows/macOS).

## Usage
```bash
python main.py
```

## Adding a New Brand
1. Go to the **⚙ Manage** tab
2. Type the brand name → click **+ Add Brand**
3. Add models and actions the same way
4. Click **💾 Save Database**

To add actual printer commands:
- Create `printers/yourbrand.py` with functions matching your action names
- Register them in `printer_actions.py` → `ACTION_MAP`

## Supported Actions (Built-in)
### Epson
- Clear Waste Ink Counter
- Printer Status
- Head Cleaning
- Nozzle Check

### Brother
- Reset Toner
- Drum Reset
- Printer Status

## Error Codes Included
- All major Epson codes: E-01 through I-41, 0x97, 0xF1, W-xx series
- All major Brother codes: text errors + numeric codes 26–E57
