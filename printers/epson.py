import socket


def _send_command(ip, port, command, timeout=3):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.send(command)
        try:
            response = s.recv(1024)
        except socket.timeout:
            response = b""
        s.close()
        return True, response
    except Exception as e:
        return False, str(e)


def clear_waste_counter(ip, port=9100):
    """Send Epson waste ink counter reset command."""
    ok, resp = _send_command(ip, port, b'\x1b\x40')
    if ok:
        return "✅ Waste ink counter reset command sent successfully."
    return f"❌ Failed: {resp}"


def printer_status(ip, port=9100):
    """Request Epson printer status."""
    ok, resp = _send_command(ip, port, b'\x10\x04\x01')
    if ok:
        return f"✅ Status request sent. Response: {resp.hex() if resp else 'No response (normal)'}."
    return f"❌ Failed: {resp}"


def head_cleaning(ip, port=9100):
    """Send Epson head cleaning command."""
    ok, resp = _send_command(ip, port, b'\x1b\x40\x00')
    if ok:
        return "✅ Head cleaning command sent."
    return f"❌ Failed: {resp}"


def nozzle_check(ip, port=9100):
    """Send Epson nozzle check command."""
    ok, resp = _send_command(ip, port, b'\x1b\x40\x01')
    if ok:
        return "✅ Nozzle check command sent."
    return f"❌ Failed: {resp}"
