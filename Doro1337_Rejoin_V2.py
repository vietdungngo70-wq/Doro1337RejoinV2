

# ======================================================
#   Doro1337's Rejoin - ROOT Multi Package Edition
#   Designed for Termux (Root Required)
# ======================================================

import os
import time
import subprocess

# ================== CONFIG ==================

place_id = "2753915549"   # CHANGE YOUR PLACE ID HERE

packages = [
    "com.roblox.client",
    "zam.cryptic"
]

check_delay = 5  # seconds

# ============================================

start_time = time.time()


def clear():
    print("\033[H\033[J", end="")


def banner():
    print("""
██████╗  ██████╗ ██████╗  ██████╗
██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗
██║  ██║██║   ██║██████╔╝██║   ██║
██║  ██║██║   ██║██╔══██╗██║   ██║
██████╔╝╚██████╔╝██║  ██║╚██████╔╝
╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝
        Doro1337
""")


def get_pid(pkg):
    try:
        pid = subprocess.check_output(f"pidof {pkg}", shell=True).decode().strip()
        return pid
    except:
        return None


def get_cpu_pid(pid):
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            data = f.read().split()

        utime = int(data[13])
        stime = int(data[14])
        return (utime + stime) % 100
    except:
        return 0


def get_ram_pkg(pkg):
    try:
        output = subprocess.check_output(
            f"dumpsys meminfo {pkg} | grep TOTAL",
            shell=True
        ).decode()

        ram_kb = int(output.split()[1])
        return f"{ram_kb//1024}MB"
    except:
        return "N/A"


def cpu_bar(percent):
    bars = int(percent / 5)
    return "█" * bars + "-" * (20 - bars)


def show_status():
    clear()
    banner()

    uptime = int(time.time() - start_time)

    print("════════════════════════════════════════════════════")
    print(f"🛡 ROOT MODE ENABLED | ⏱ Uptime: {uptime}s")
    print("════════════════════════════════════════════════════")
    print("PKG                     | STATUS        | CPU               | RAM")
    print("--------------------------------------------------------------------")

    for pkg in packages:
        pid = get_pid(pkg)

        if pid:
            cpu_percent = get_cpu_pid(pid)
            ram = get_ram_pkg(pkg)
            status = "🟢 Running"
            bar = cpu_bar(cpu_percent)
            print(f"{pkg:<22} | {status:<13} | {bar} {cpu_percent:>3}% | {ram}")
        else:
            status = "🔴 Disconnect"
            print(f"{pkg:<22} | {status:<13} | {'-'*20}   0% | N/A")


def rejoin(pkg):
    print(f"\n🪙 Rejoining {pkg} ...")
    os.system(f'am start -a android.intent.action.VIEW -d "roblox://placeId={place_id}"')


# ================= MAIN LOOP =================

while True:
    show_status()

    for pkg in packages:
        if not get_pid(pkg):
            rejoin(pkg)

    time.sleep(check_delay)

