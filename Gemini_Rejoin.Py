import os
import sys
import time
import json
import random
import threading
import subprocess
import datetime
import requests
import re

# ==========================================
# 🍊 CONFIGURATION & CONSTANTS
# ==========================================

CONFIG_FILE = "config.json"
VERSION = "GhostSpectre Root v2.5"
BANNER_NAME = "🍊 Doro1337"

# ANSI Colors
class Col:
    RESET = "\033[0m"
    RED = "\033[38;5;196m"
    GREEN = "\033[38;5;46m"
    YELLOW = "\033[38;5;226m"
    BLUE = "\033[38;5;39m"
    MAGENTA = "\033[38;5;201m"
    CYAN = "\033[38;5;51m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;240m"
    ORANGE = "\033[38;5;208m"
    BOLD = "\033[1m"

# Default Config
default_config = {
    "place_id": "2753915549", # Blox Fruits
    "prefix": "com.roblox.client",
    "webhook_url": "",
    "smart_hop": False,
    "interval": 15,
    "auto_restart": True,
    "random_interval": True
}

# Global State
running = False
packages = []
global_stats = {
    "start_time": time.time(),
    "total_rejoins": 0,
    "root_status": False
}

# ==========================================
# 🛠️ ROOT HELPER FUNCTIONS
# ==========================================

def check_root():
    """Checks for root access by attempting to run 'id' via su."""
    try:
        output = subprocess.check_output("su -c id", shell=True).decode()
        if "uid=0(root)" in output:
            return True
    except:
        pass
    return False

def su_exec(command):
    """Executes a command with Root privileges."""
    try:
        # Timeout added to prevent freezing if su hangs
        result = subprocess.run(f"su -c '{command}'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        return result.stdout.decode().strip()
    except Exception as e:
        return ""

def get_pid_root(package_name):
    """Gets PID of a package using Root."""
    try:
        # 'pidof' is reliable on Android
        pid = su_exec(f"pidof {package_name}")
        if pid:
            return int(pid.split()[0]) # Return first PID if multiple
    except:
        pass
    return 0

def kill_app_root(package_name):
    """Force stops an app using Root."""
    su_exec(f"am force-stop {package_name}")

def start_app_root(package_name, place_id=None):
    """Starts app using Root. Uses Deep Link if Place ID is provided."""
    if place_id:
        # Deep link direct join
        cmd = f"am start -a android.intent.action.VIEW -d \"roblox://experiences/start?placeId={place_id}\" -n {package_name}/com.roblox.client.Activity"
    else:
        # Standard launch
        cmd = f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
    
    su_exec(cmd)

# ==========================================
# 🔔 WEBHOOK SYSTEM
# ==========================================

class WebhookManager:
    @staticmethod
    def send(cfg, event_type, details, color_code=0x00FF00):
        url = cfg.get("webhook_url")
        if not url or "http" not in url:
            return

        embed = {
            "title": f"{BANNER_NAME} - Root Monitor",
            "description": f"**Event:** {event_type}",
            "color": color_code,
            "fields": [],
            "footer": {"text": f"GhostSpectre • {datetime.datetime.now().strftime('%H:%M:%S')}"}
        }

        for key, value in details.items():
            embed["fields"].append({"name": key, "value": str(value), "inline": True})

        try:
            threading.Thread(target=requests.post, args=(url,), kwargs={"json": {"embeds": [embed], "username": "Doro Root Bot"}}).start()
        except:
            pass

# ==========================================
# 📦 PACKAGE ENGINE
# ==========================================

class PackageInstance:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.status = "CHECK"
        self.restart_count = 0
        self.crash_count = 0
        self.uptime = time.time()
        self.pid = 0
        self.cpu = 0.0
        self.next_hop = 0
    
    def update_stats(self):
        # 1. Get PID
        self.pid = get_pid_root(self.name)
        
        if self.pid == 0:
            self.status = "DOWN"
            self.cpu = 0.0
        else:
            self.status = "RUN"
            # 2. Get CPU/RAM (Simplified for speed)
            # Parsing /proc/[pid]/stat is faster than running 'top'
            try:
                with open(f"/proc/{self.pid}/stat", 'r') as f:
                    stats = f.read().split()
                    # utime + stime (indices 13, 14) roughly correlates to load
                    # Calculating exact CPU % in Android without 'top' is complex math
                    # We will use a mock calculation based on state for speed, 
                    # or you can use `top -n 1 -p PID` if you don't mind lag.
                    self.cpu = 15.5 # Placeholder for smooth UI, real calculation is heavy
            except:
                self.cpu = 0.0

    def restart_app(self, reason="Auto Rejoin"):
        global global_stats
        self.status = "WAIT"
        
        # Kill
        kill_app_root(self.name)
        time.sleep(2)
        
        # Start (Auto Join)
        start_app_root(self.name, self.config["place_id"])
        
        self.restart_count += 1
        global_stats["total_rejoins"] += 1
        self.uptime = time.time()
        
        WebhookManager.send(self.config, "🔄 Rejoin Triggered", {
            "Package": self.name,
            "Reason": reason,
            "Place ID": self.config["place_id"]
        }, 0xFFFF00)

    def check_smarthop(self):
        if not self.config["smart_hop"] or self.status != "RUN":
            return
        
        if time.time() > self.next_hop:
            self.restart_app("🧠 SmartHop")
            # Calculate next hop
            interval_sec = self.config["interval"] * 60
            variance = random.randint(30, 180) if self.config["random_interval"] else 0
            self.next_hop = time.time() + interval_sec + variance

# ==========================================
# 🚨 LOGCAT MONITOR (REAL)
# ==========================================

def logcat_monitor(cfg):
    # Runs 'logcat' command and filters for keywords
    # Warning: This can be CPU intensive.
    process = subprocess.Popen(
        ["su", "-c", "logcat -v time *:E"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        universal_newlines=True # Text mode
    )
    
    while running:
        line = process.stdout.readline()
        if not line:
            continue
            
        # 277/279 Detection Logic
        # These are common partial strings in Roblox connection errors
        if "ConnectionLost" in line or "Error code: 277" in line or "Error code: 279" in line:
            # We need to attribute this error to a package.
            # Logcat is global, so we guess or restart all if critical.
            # A refined approach checks the PID in the log line.
            
            # Example Log: 10-12 15:00:00.000 1234 1234 E Roblox: ConnectionLost
            parts = line.split()
            if len(parts) > 4:
                try:
                    log_pid = int(parts[2]) # Usually PID is 3rd column
                    for pkg in packages:
                        if pkg.pid == log_pid:
                            pkg.crash_count += 1
                            pkg.restart_app("🚨 Detection 277/279")
                            break
                except:
                    pass

# ==========================================
# 📊 UI RENDERER
# ==========================================

def render_bar(percent, width=12):
    fill = int(width * percent // 100)
    bar = "█" * fill + "-" * (width - fill)
    col = Col.GREEN if percent < 50 else (Col.YELLOW if percent < 80 else Col.RED)
    return f"[{col}{bar}{Col.RESET}]"

def render_dashboard(cfg):
    os.system("clear")
    
    # Header
    print(f"{Col.ORANGE}{Col.BOLD}  🍊 Doro1337 ROOT{Col.RESET} | {VERSION}")
    print(f"{Col.GRAY}  Auth: {Col.GREEN}GRANTED (Root){Col.RESET}" if global_stats["root_status"] else f"{Col.GRAY}  Auth: {Col.RED}NO ROOT PERMISSION{Col.RESET}")
    
    # System Stats
    uptime = str(datetime.timedelta(seconds=int(time.time() - global_stats["start_time"])))
    print(f"\n{Col.GRAY}┌── {Col.BOLD}SYSTEM INFO{Col.RESET}")
    print(f"{Col.GRAY}│ {Col.RESET}Place: {Col.CYAN}{cfg['place_id']}{Col.RESET}")
    print(f"{Col.GRAY}│ {Col.RESET}Hop:   {Col.GREEN if cfg['smart_hop'] else Col.RED}{'Active' if cfg['smart_hop'] else 'Disabled'}{Col.RESET}")
    print(f"{Col.GRAY}│ {Col.RESET}Time:  {uptime} | Rejoins: {global_stats['total_rejoins']}")
    print(f"{Col.GRAY}└──────────────────────────────────────{Col.RESET}")

    # Package Table
    print(f"\n{Col.BOLD}{'PKG':<15} {'STATUS':<8} {'PROGRESS':<14} {'PID':<6} {'RST'}{Col.RESET}")
    
    for pkg in packages:
        # Status Color
        s_col = Col.GREEN if pkg.status == "RUN" else (Col.YELLOW if pkg.status == "WAIT" else Col.RED)
        
        # Fake progress based on uptime for visual aliveness
        p_val = min(100, int((time.time() - pkg.uptime) % 100))
        
        print(f"{pkg.name[-15:]:<15} {s_col}{pkg.status:<8}{Col.RESET} {render_bar(p_val)} {pkg.pid:<6} {pkg.restart_count}")

    print(f"\n{Col.GRAY}Logcat Monitor: {'Active' if global_stats['root_status'] else 'Inactive'}{Col.RESET}")
    print(f"{Col.GRAY}Press Ctrl+C to Stop{Col.RESET}")

# ==========================================
# 🚀 MAIN LOGIC
# ==========================================

def scan_packages_root(prefix):
    """Scans installed packages matching prefix using pm."""
    try:
        # returns "package:com.roblox.client"
        raw = su_exec(f"pm list packages | grep {prefix}")
        pkgs = []
        for line in raw.split("\n"):
            if line.strip():
                clean_name = line.replace("package:", "").strip()
                pkgs.append(clean_name)
        return pkgs
    except:
        return []

def main():
    cfg = default_config # Load your config load/save logic here
    
    # 1. Root Check
    print(f"{Col.YELLOW}Checking Root Access...{Col.RESET}")
    if check_root():
        global_stats["root_status"] = True
        print(f"{Col.GREEN}Root Access Granted!{Col.RESET}")
    else:
        print(f"{Col.RED}ERROR: Root access denied or 'su' not found.{Col.RESET}")
        print("Please grant Termux root access in Magisk/KernelSU.")
        return

    # 2. Scan Packages
    print(f"{Col.CYAN}Scanning packages ({cfg['prefix']})...{Col.RESET}")
    found_pkgs = scan_packages_root(cfg["prefix"])
    
    if not found_pkgs:
        # Fallback for standard Roblox if no clones found
        if cfg["prefix"] == "com.roblox.client":
            found_pkgs = ["com.roblox.client"]
        else:
            print(f"{Col.RED}No packages found with prefix!{Col.RESET}")
            return

    for p_name in found_pkgs:
        pk = PackageInstance(p_name, cfg)
        pk.next_hop = time.time() + (cfg["interval"] * 60)
        packages.append(pk)

    # 3. Start Threads
    global running
    running = True
    
    t_log = threading.Thread(target=logcat_monitor, args=(cfg,))
    t_log.daemon = True
    t_log.start()
    
    WebhookManager.send(cfg, "🚀 Root Tool Started", {"Mode": "ROOT", "Packages": len(packages)})

    # 4. Loop
    try:
        while running:
            for pkg in packages:
                pkg.update_stats()
                pkg.check_smarthop()
            
            render_dashboard(cfg)
            time.sleep(1)
            
    except KeyboardInterrupt:
        running = False
        print(f"\n{Col.RED}Exiting...{Col.RESET}")

if __name__ == "__main__":
    main()
    