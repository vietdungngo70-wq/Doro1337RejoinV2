# ================= DORO1337 REJOIN PRO =================
import os, time, subprocess, sys, threading, json, urllib.request
from datetime import datetime

GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
CYAN="\033[96m"
RESET="\033[0m"

place_id=None
place_name="Not Set"
packages=[]
webhook=None
running=False

CHECK_DELAY=5
FREEZE_CPU=2
FREEZE_TIME=20

freeze_tracker={}
cpu_history={}
is_rejoining={}
rejoin_counter={}

LOG_FILE="/sdcard/doro_rejoin_log.txt"

# ================= ROOT =================
def root_check():
    if os.geteuid()!=0:
        print(RED+"[!] Root required"+RESET)
        sys.exit()

# ================= LOG =================
def write_log(text):
    with open(LOG_FILE,"a") as f:
        f.write(f"[{datetime.now()}] {text}\n")

# ================= SYSTEM =================
def get_pid(pkg):
    try:
        return subprocess.check_output(f"pidof {pkg}",shell=True).decode().strip()
    except:
        return ""

def get_cpu(pid):
    try:
        out=subprocess.check_output(f"top -b -n 1 -p {pid} | tail -n 1",shell=True).decode()
        return int(float(out.split()[8]))
    except:
        return 0

def get_ram(pkg):
    try:
        out=subprocess.check_output(f"dumpsys meminfo {pkg} | grep TOTAL",shell=True).decode()
        kb=int(out.split()[1])
        return f"{kb//1024}MB"
    except:
        return "N/A"

def open_game(pkg):
    subprocess.call(
        f"am start -a android.intent.action.VIEW -d roblox://placeId={place_id} {pkg}",
        shell=True
    )

# ================= WEBHOOK =================
def send_webhook(msg):
    if not webhook: return
    try:
        data=json.dumps({"content":msg}).encode()
        urllib.request.urlopen(
            urllib.request.Request(webhook,data=data,
            headers={"Content-Type":"application/json"}),
            timeout=5
        )
    except:
        pass

# ================= REJOIN =================
def rejoin(pkg,reason):

    if is_rejoining.get(pkg):
        return

    is_rejoining[pkg]=True

    subprocess.call(f"am force-stop {pkg}",shell=True)
    time.sleep(2)
    open_game(pkg)

    rejoin_counter[pkg]=rejoin_counter.get(pkg,0)+1

    msg=f"Rejoin {pkg} | {reason}"
    send_webhook(msg)
    write_log(msg)

    is_rejoining[pkg]=False

# ================= MONITOR =================
def monitor_package(pkg):

    freeze_tracker[pkg]=0
    cpu_history[pkg]=[]
    rejoin_counter[pkg]=0

    while running:

        pid=get_pid(pkg)

        if pid:
            cpu=get_cpu(pid)

            cpu_history[pkg].append(cpu)
            if len(cpu_history[pkg])>5:
                cpu_history[pkg].pop(0)

            avg_cpu=sum(cpu_history[pkg])/len(cpu_history[pkg])

            if avg_cpu<FREEZE_CPU:
                freeze_tracker[pkg]+=CHECK_DELAY
            else:
                freeze_tracker[pkg]=0

            if freeze_tracker[pkg]>=FREEZE_TIME:
                rejoin(pkg,"freeze")
                freeze_tracker[pkg]=0

        else:
            rejoin(pkg,"disconnect")

        time.sleep(CHECK_DELAY)

# ================= STATUS =================
def status_loop():

    last_screen=""

    while running:

        lines=[]
        header="PKG                      | STATUS      | CPU | RAM  | RJ"
        separator="-------------------------------------------------------------"

        lines.append(header)
        lines.append(separator)

        for pkg in packages:

            pid=get_pid(pkg)

            if pid:
                cpu=get_cpu(pid)
                ram=get_ram(pkg)
                status=GREEN+"🟢 Run"+RESET
            else:
                cpu=0
                ram="N/A"
                status=RED+"🔴 Disc"+RESET

            rj=rejoin_counter.get(pkg,0)

            lines.append(
                f"{pkg:<24} | {status:<11} | {cpu:>3}% | {ram:<4} | {rj}"
            )

        screen="\n".join(lines)

        if screen!=last_screen:
            os.system("clear")
            print(CYAN+"DORO1337 REJOIN PRO"+RESET)
            print(YELLOW+f"Place: {place_name} ({place_id})"+RESET)
            print(screen)
            last_screen=screen

        time.sleep(2)

# ================= START =================
def start():
    global running

    if not place_id:
        print(RED+"Place ID not set"+RESET)
        return

    if not packages:
        print(RED+"No package added"+RESET)
        return

    running=True

    for pkg in packages:
        threading.Thread(target=monitor_package,args=(pkg,),daemon=True).start()

    threading.Thread(target=status_loop,daemon=True).start()

# ================= MENU =================
def menu():
    global place_id,place_name,webhook,running

    root_check()

    while True:
        print(CYAN+"\n=== DORO1337 PRO MENU ==="+RESET)
        print("1 ▶ Start")
        print("2 ▶ Set Place ID")
        print("3 ▶ Add Package")
        print("4 ▶ Set Webhook")
        print("5 ▶ Stop")
        print("0 ▶ Exit")

        c=input("> ").strip()

        if c=="1":
            start()

        elif c=="2":

            print(CYAN+"\n=== Set Place ID ==="+RESET)
            print("1 ▶ Blox Fruit (auto)")
            print("2 ▶ Set other place id")

            sub=input("> ").strip()

            if sub=="1":
                place_id="2753915549"
                place_name="Blox Fruit"
                print(GREEN+"✔ Blox Fruit Place ID set successfully"+RESET)

            elif sub=="2":
                new_id=input("Enter other place id: ").strip()
                if new_id.isdigit():
                    place_id=new_id
                    place_name="Custom"
                    print(GREEN+"✔ Custom Place ID set successfully"+RESET)
                else:
                    print(RED+"✖ Invalid Place ID"+RESET)

        elif c=="3":
            p=input("Package: ").strip()
            if p and p not in packages:
                packages.append(p)
                print(GREEN+"✔ Package added"+RESET)

        elif c=="4":
            webhook=input("Webhook: ").strip() or None
            print(GREEN+"✔ Webhook saved"+RESET)

        elif c=="5":
            running=False
            print(YELLOW+"Stopped"+RESET)

        elif c=="0":
            running=False
            break

menu()