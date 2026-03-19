from printers import epson, brother

ACTION_MAP = {
    "Epson": {
        "Clear Waste Ink Counter": epson.clear_waste_counter,
        "Printer Status":          epson.printer_status,
        "Head Cleaning":           epson.head_cleaning,
        "Nozzle Check":            epson.nozzle_check,
    },
    "Brother": {
        "Reset Toner":    brother.reset_toner,
        "Drum Reset":     brother.drum_reset,
        "Printer Status": brother.printer_status,
    }
}


def run_action(brand, action, ip, port=9100):
    """Dispatch a printer action. Returns a result string."""
    brand_actions = ACTION_MAP.get(brand)
    if brand_actions is None:
        return f"❌ Unknown brand: {brand}"
    func = brand_actions.get(action)
    if func is None:
        return f"❌ Action '{action}' not supported for {brand}"
    try:
        return func(ip, port)
    except Exception as e:
        return f"❌ Error running action: {e}"
