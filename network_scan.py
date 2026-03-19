import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


def _check_port(ip, port=9100, timeout=0.3):
    """Check if a printer port is open at the given IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                hostname = ""
            return ip, hostname
    except Exception:
        pass
    return None


def scan_network(subnet="192.168.1", port=9100, progress_callback=None):
    """
    Scan a /24 subnet for printers on the given port.
    Returns list of dicts: [{"ip": ..., "hostname": ...}]
    """
    found = []
    ips = [f"{subnet}.{i}" for i in range(1, 255)]

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(_check_port, ip, port): ip for ip in ips}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback(completed, 254)
            result = future.result()
            if result:
                ip, hostname = result
                found.append({"ip": ip, "hostname": hostname})

    found.sort(key=lambda x: list(map(int, x["ip"].split("."))))
    return found


def get_all_local_ips():
    """
    Get ALL local network interfaces (not just the default route).
    Returns list of (ip, subnet_prefix) tuples.
    Filters out loopback and known VPN/virtual ranges.
    """
    import socket
    candidates = []
    hostname = socket.gethostname()
    try:
        # Get all IPs for this host
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            if ":" in ip:  # skip IPv6
                continue
            if ip.startswith("127."):
                continue
            parts = ip.split(".")
            subnet = ".".join(parts[:3])
            candidates.append((ip, subnet))
    except Exception:
        pass

    # Also try the default-route method as a fallback
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        default_ip = s.getsockname()[0]
        s.close()
        parts = default_ip.split(".")
        entry = (default_ip, ".".join(parts[:3]))
        if entry not in candidates:
            candidates.append(entry)
    except Exception:
        pass

    # Deduplicate by subnet
    seen = set()
    result = []
    for ip, subnet in candidates:
        if subnet not in seen:
            seen.add(subnet)
            result.append((ip, subnet))

    return result if result else [("192.168.1.1", "192.168.1")]


def get_local_subnet():
    """Return the best-guess local subnet (prefers 192.168.x / 10.x / 172.16-31.x)."""
    candidates = get_all_local_ips()

    # Prefer common LAN ranges over VPN/virtual (172.17-31 is often Docker/VPN)
    def priority(entry):
        ip, subnet = entry
        if ip.startswith("192.168."):
            return 0
        if ip.startswith("10."):
            return 1
        # 172.16.x - 172.31.x: lower priority (often VPN/Docker)
        parts = ip.split(".")
        if parts[0] == "172" and 16 <= int(parts[1]) <= 31:
            return 3
        return 2

    candidates.sort(key=priority)
    return candidates[0][1] if candidates else "192.168.1"
