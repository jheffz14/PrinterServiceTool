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


def reset_toner(ip, port=9100):
    """Send Brother toner reset command."""
    ok, resp = _send_command(ip, port, b'\x1b\x45')
    if ok:
        return "✅ Toner reset command sent successfully."
    return f"❌ Failed: {resp}"


def drum_reset(ip, port=9100):
    """Send Brother drum reset command."""
    ok, resp = _send_command(ip, port, b'\x1b\x4c')
    if ok:
        return "✅ Drum reset command sent successfully."
    return f"❌ Failed: {resp}"


def printer_status(ip, port=9100):
    """Request Brother printer status."""
    ok, resp = _send_command(ip, port, b'\x1b\x40\x04\x00\x00\x00\x00')
    if ok:
        return f"✅ Status request sent. Response: {resp.hex() if resp else 'No response (normal)'}."
    return f"❌ Failed: {resp}"
