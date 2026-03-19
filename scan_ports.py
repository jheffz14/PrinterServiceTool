
import socket

def scan_printer_ports(ip):
    common_ports = [9100, 515, 631, 8080, 8443, 80, 443, 54921, 9101, 9102, 8611]
    print(f"\nScanning ports on {ip}...")
    print("-" * 40)
    found = []
    for port in common_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        result = sock.connect_ex((ip, port))
        sock.close()
        status = "✅ OPEN" if result == 0 else "❌ closed"
        print(f"  Port {port:6d}  {status}")
        if result == 0:
            found.append(port)
    print("-" * 40)
    if found:
        print(f"\n  Use port: {found[0]}  in the Printer Service Tool")
    else:
        print("\n  No open ports found.")
        print("  - Check printer is powered on")
        print("  - Check you are on the same network")
        print("  - Try pinging:", ip)
    return found

if __name__ == "__main__":
    ip = input("Enter printer IP address: ").strip()
    scan_printer_ports(ip)
    input("\nPress Enter to close...")
