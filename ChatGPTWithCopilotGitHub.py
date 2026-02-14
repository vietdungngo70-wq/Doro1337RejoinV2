
import threading
import time
import json
import os
import random
import psutil
import requests
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# ================= CONFIG =================
CONFIG_FILE = "config.json"
LOG_FILE = "ghostspectre.log"

DEFAULT_CONFIG = {
    "place_id": 1234567,
    "prefix": "pkg",
    "webhook": "",
    "smart_hop": True,
    "interval": 10,
    "auto_restart": True,
    "random_mode": True,
    "package_count": 3
}

COOLDOWN_SECONDS = 10
WEBHOOK_COOLDOWN = 20
CPU_LIMIT = 95
RAM_LIMIT = 90

APP_BANNER = f"{Fore.YELLOW}👻 GhostSpectre Unified{Style.RESET_ALL}"
VERSION = "2.0"

# ================= CONFIG SYSTEM =================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

config = load_config()

# ================= STATE =================
pkg_stats = {}
pkg_threads = []
global_rejoin_counter = 0
last_webhook_time = 0
lock = threading.Lock()

def generate_packages():
    global pkg_stats
    pkg_stats = {}
    for i in range(1, config["package_count"] + 1):
        name = f"{config['prefix']}{i}"
        pkg_stats[name] = {
            "status": "RUN",
            "restart": 0,
            "crash": 0,
            "uptime": time.time(),
            "cpu": random.randint(1, 60),
            "ram": random.randint(1, 60),
            "last_rejoin": 0
        }

generate_packages()

# ================= WEBHOOK =================
def send_webhook(event_type, pkg, color="green"):
    global last_webhook_time
    if not config["webhook"]:
        return

    now = time.time()
    if now - last_webhook_time < WEBHOOK_COOLDOWN:
        return

    payload = {
        "event": event_type,
        "package": pkg,
        "restart": pkg_stats[pkg]["restart"],
        "crash": pkg_stats[pkg]["crash"],
        "global_rejoin": global_rejoin_counter,
        "time": datetime.now().strftime("%H:%M:%S")
    }

    try:
        requests.post(config["webhook"], json=payload, timeout=5)
        last_webhook_time = now
    except:
        pass

# ================= ENGINE =================
class PackageThread(threading.Thread):
    def __init__(self, pkg):
        super().__init__()
        self.pkg = pkg
        self.running = True
        self.smart_timer = random.randint(8, 16)

    def run(self):
        global global_rejoin_counter

        while self.running:
            stat = pkg_stats[self.pkg]

            # Simulate crash
            if random.random() < 0.02:
                stat["status"] = "CRASH"
                stat["crash"] += 1
                send_webhook("CRASH", self.pkg, "red")
                time.sleep(2)

                if config["auto_restart"]:
                    now = time.time()
                    if now - stat["last_rejoin"] > COOLDOWN_SECONDS:
                        with lock:
                            stat["restart"] += 1
                            global_rejoin_counter += 1
                        stat["status"] = "RUN"
                        stat["uptime"] = time.time()
                        stat["last_rejoin"] = now
                        send_webhook("RESTART", self.pkg, "green")

            # SmartHop
            self.smart_timer -= 1
            if self.smart_timer <= 0 and config["smart_hop"]:
                send_webhook("SMARTHOP", self.pkg, "yellow")
                self.smart_timer = random.randint(8, 16)

            interval = random.randint(8, 16) if config["random_mode"] else config["interval"]
            time.sleep(interval)

# ================= DASHBOARD =================
def system_block():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    alerts = ""
    if cpu > CPU_LIMIT:
        alerts += Fore.RED + "CPU ALERT! "
    if ram > RAM_LIMIT:
        alerts += Fore.RED + "RAM ALERT! "
    return f"""
{APP_BANNER}  v{VERSION}
🎮 Place ID: {config['place_id']}
📦 Prefix: {config['prefix']}
📊 Packages: {config['package_count']}
🧠 SmartHop: {config['smart_hop']}
🔗 Webhook: {'OK' if config['webhook'] else 'Not Set'}
🔁 Global Rejoin: {global_rejoin_counter}
🖥 CPU: {cpu}%
💾 RAM: {ram}%
{alerts}
"""

def package_block():
    out = "\n[ PACKAGE STATUS ]\n"
    for name, stat in pkg_stats.items():
        color = Fore.GREEN if stat["status"] == "RUN" else Fore.RED
        uptime = int(time.time() - stat["uptime"])
        out += f"{color}● {name} {Style.RESET_ALL}"
        out += f"Restart:{stat['restart']} Crash:{stat['crash']} "
        out += f"Uptime:{uptime}s\n"
    return out

def draw_dashboard():
    os.system("cls" if os.name == "nt" else "clear")
    print(system_block())
    print(package_block())

# ================= MENU =================
def start_threads():
    global pkg_threads
    if pkg_threads:
        return
    for name in pkg_stats.keys():
        t = PackageThread(name)
        t.daemon = True
        t.start()
        pkg_threads.append(t)

def menu():
    while True:
        draw_dashboard()
        print("""
1️⃣ Start Tool
2️⃣ Set Place ID
3️⃣ Set Prefix
4️⃣ Set Package Count
5️⃣ Toggle SmartHop
6️⃣ Set Webhook
7️⃣ Toggle Auto Restart
8️⃣ Reset Stats
0️⃣ Exit
""")
        sel = input("Select: ")

        if sel == "1":
            start_threads()
            print(Fore.GREEN + "✅ Tool started successfully")
            input()

        elif sel == "2":
            config["place_id"] = int(input("Enter place id: "))
            save_config(config)
            print(Fore.GREEN + "✅ Place ID set successfully")
            input()

        elif sel == "3":
            config["prefix"] = input("Prefix: ")
            generate_packages()
            save_config(config)
            print(Fore.GREEN + "✅ Prefix set successfully")
            input()

        elif sel == "4":
            config["package_count"] = int(input("Package count: "))
            generate_packages()
            save_config(config)
            print(Fore.GREEN + "✅ Package count updated successfully")
            input()

        elif sel == "5":
            config["smart_hop"] = not config["smart_hop"]
            save_config(config)
            print(Fore.GREEN + "✅ SmartHop toggled successfully")
            input()

        elif sel == "6":
            config["webhook"] = input("Webhook URL: ")
            save_config(config)
            print(Fore.GREEN + "✅ Webhook set successfully")
            input()

        elif sel == "7":
            config["auto_restart"] = not config["auto_restart"]
            save_config(config)
            print(Fore.GREEN + "✅ Auto Restart toggled successfully")
            input()

        elif sel == "8":
            for stat in pkg_stats.values():
                stat["restart"] = 0
                stat["crash"] = 0
                stat["uptime"] = time.time()
            print(Fore.GREEN + "✅ Stats reset successfully")
            input()

        elif sel == "0":
            os._exit(0)

menu()
