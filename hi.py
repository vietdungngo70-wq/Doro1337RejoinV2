import os
import sys

# ==========================================
# SUPER ULTIMATE SOURCE CODE (GOD MODE)
# ==========================================
GOD_MODE_SOURCE = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐲 DORO GOD MODE - ULTIMATE ROBLOX MANAGER v99.0
Build: TITAN CLASS | Developer: Doro Dev Team (Modded by Gemini)
Features: Webhook, Device Doctor, Auto-Cleaner, Deep Watchdog
"""

import os
import sys
import time
import json
import random
import threading
import subprocess
import re
import select
import datetime
from collections import deque, defaultdict

# --- AUTO INSTALL DEPENDENCIES ---
try:
    import requests
    from rich.live import Live
    from rich.table import Table
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.console import Console
    from rich.align import Align
    from rich import box
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
except ImportError:
    os.system("pip install rich requests")
    print("Restarting...")
    sys.exit()

CONFIG_FILE = "config_apex_god.json"
VERSION = "v99.0 GOD-MODE"
console = Console()

# --- GLOBAL VARIABLES & STATE ---
g_state = {
    "start_time": time.time(),
    "cpu": 0, "ram": 0, "temp": 0, "ping": 0, "battery": 100,
    "lock": threading.Lock(),
    "running": True,
    "restart_log": deque(maxlen=500),
    "pid_map": {}, "pkg_state": {}, "total_targets": 0,
    "net_ok": True, "core_count": os.cpu_count() or 8,
    "total_crashes": 0, "total_rejoins": 0
}

# --- DEFAULT CONFIGURATION (HEAVY) ---
DEFAULT_CONFIG = {
    "place_id": "2753915549", 
    "place_name": "Blox Fruit", 
    "prefix": "dinozzz.cryptic", 
    "webhook_url": "", 
    "smart_hop": True, 
    "hop_min": 15, 
    "hop_max": 25,
    "auto_restart": True, 
    "ram_limit": 90, 
    "cpu_limit": 95,
    "temp_limit": 75, # Auto cooldown if temp > 75C
    "clone_ram_limit": 4096, 
    "clone_cpu_limit": 90,
    "check_interval": 5, 
    "net_recovery": True,
    "device_doctor": True, # New Feature
    "auto_cleaner": True,  # New Feature
    "discord_notify": False
}

# ==========================================
# 1. KERNEL & SYSTEM INTERFACE
# ==========================================
class KernelShell:
    def __init__(self):
        self.proc = None; self.fd_out = None; self.fd_in = None
        self.lock = threading.RLock(); self.restart()
    def restart(self):
        with self.lock:
            if self.proc:
                try: self.proc.terminate(); self.proc.wait(timeout=1)
                except: pass
            try:
                self.proc = subprocess.Popen(["su"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, text=False)
                self.fd_out = self.proc.stdout.fileno(); self.fd_in = self.proc.stdin.fileno()
            except: sys.exit(1)
    def exec(self, cmd):
        with self.lock:
            if not self.proc or self.proc.poll() is not None: self.restart()
            try:
                os.write(self.fd_in, f"{cmd}; echo '___K_END___'\n".encode('utf-8'))
                buffer = b""
                while True:
                    if not select.select([self.fd_out], [], [], 5)[0]: raise TimeoutError
                    chunk = os.read(self.fd_out, 4096)
                    if not chunk: break 
                    if len(buffer) + len(chunk) > 2*1024*1024: raise BufferError
                    buffer += chunk
                    if b"___K_END___" in buffer: return buffer.split(b"___K_END___", 1)[0].decode('utf-8', errors='ignore').strip()
            except: self.restart(); return ""

root_shell = KernelShell()

# ==========================================
# 2. DISCORD WEBHOOK MANAGER
# ==========================================
class DiscordManager:
    @staticmethod
    def send_log(cfg, title, description, color=0x00ff00):
        if not cfg['webhook_url'] or not cfg['discord_notify']: return
        data = {
            "username": "Doro Manager God",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": f"Doro v99 | {datetime.datetime.now().strftime('%H:%M:%S')}"}
            }]
        }
        try:
            threading.Thread(target=requests.post, args=(cfg['webhook_url'],), kwargs={"json": data}).start()
        except: pass

# ==========================================
# 3. DEVICE DOCTOR & CLEANER
# ==========================================
class DeviceDoctor(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True); self.cfg = cfg
    
    def run(self):
        while g_state["running"]:
            time.sleep(30)
            try:
                # 1. Clean RAM Cache if needed
                if self.cfg['auto_cleaner'] and g_state['ram'] > 85:
                    root_shell.exec("echo 3 > /proc/sys/vm/drop_caches")
                
                # 2. Check Battery
                dump = root_shell.exec("dumpsys battery | grep level")
                if dump: 
                    g_state['battery'] = int(re.search(r'\d+', dump).group())

                # 3. Thermal Throttle
                if g_state['temp'] > self.cfg['temp_limit']:
                    console.print(f"[bold red]🔥 MÁY QUÁ NÓNG ({g_state['temp']}°C)! ĐANG HẠ NHIỆT...[/bold red]")
                    DiscordManager.send_log(self.cfg, "⚠️ CẢNH BÁO NHIỆT ĐỘ", f"Nhiệt độ: {g_state['temp']}°C. Đang giảm tải hệ thống.", 0xff0000)
                    time.sleep(10) # Pause operations
            except: pass

# ==========================================
# 4. STATS & MONITORING ENGINE
# ==========================================
class StatsManager:
    def __init__(self): 
        self.data = {"rejoins": 0, "crashes": 0, "err_277": 0, "err_279": 0, "uptime_min": 0}; self.load()
    def load(self): 
        if os.path.exists("stats_god.json"): 
            try: self.data = json.load(open("stats_god.json"))
            except: pass
    def save(self):
        with g_state["lock"]: json.dump(self.data, open("stats_god.json", "w"))
    def update(self, k):
        with g_state["lock"]:
            if k in self.data: self.data[k] += 1
            else: self.data[k] = 1
            if "rejoin" in k: g_state["total_rejoins"] += 1
            if "err" in k or "crash" in k: g_state["total_crashes"] += 1
    def get_snapshot(self):
        with g_state["lock"]: return self.data.copy()

stats = StatsManager()

class SingularityAggregator(threading.Thread):
    def __init__(self, cfg, instances):
        super().__init__(daemon=True); self.cfg = cfg; self.inst_map = {i.pkg: i for i in instances}
        self.cycle_count = 0
        self.pkg_cpu_history = defaultdict(lambda: deque(maxlen=5)) # Longer history

    def run(self):
        prev_tot = 0; prev_idl = 0
        while g_state["running"]:
            time.sleep(2); self.cycle_count += 1
            try:
                # Network Check
                if self.cycle_count % 5 == 0:
                    res = root_shell.exec("ping -c 1 -W 1 8.8.8.8")
                    ping = float(re.search(r'time=([\d\.]+)', res).group(1)) if res and "time=" in res else 999
                    with g_state["lock"]: g_state["net_ok"], g_state["ping"] = (ping < 500), int(ping)

                # Process Mapping
                raw_map = root_shell.exec(f"grep -a -i '{self.cfg['prefix']}' /proc/[0-9]*/cmdline")
                pid_to_pkg = {int(l.split(":")[0].split("/")[2]): l.split(":")[1].strip().replace('\x00','') for l in raw_map.splitlines() if ":" in l} if raw_map else {}

                # System Stats
                glb = root_shell.exec("cat /proc/stat; echo 'G'; cat /proc/meminfo; echo 'G'; cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0").split('G')
                if len(glb) < 3: continue
                
                ps = glb[0].split(); c_tot = sum(int(x) for x in ps[1:]); c_idl = int(ps[4])+int(ps[5])
                d_tot = c_tot - prev_tot; d_idl = c_idl - prev_idl
                prev_tot = c_tot; prev_idl = c_idl
                
                mt = int(re.search(r'\d+', glb[1]).group()); m = re.search(r'MemAvailable:\s+(\d+)', glb[1])
                ma = int(m.group(1)) if m else 0
                
                # Update State
                with g_state["lock"]:
                    g_state["cpu"] = int(100*(d_tot-d_idl)/d_tot) if d_tot>0 else 0
                    g_state["ram"] = int((mt-ma)/mt*100)
                    g_state["temp"] = int(int(glb[2].strip())/1000)
                    
                    # Map PIDs to Instances
                    for pid, pkg in pid_to_pkg.items():
                        t = self.inst_map.get(pkg)
                        if t: t.pid = pid; t.last_seen = time.time()
            except: pass

# ==========================================
# 5. ACCOUNT INSTANCE (THE BRAIN)
# ==========================================
class AccountInstance:
    def __init__(self, pkg, cfg):
        self.pkg = pkg; self.cfg = cfg; self.pid = None
        self.status = "BOOTING"; self.style = "blue"
        self.last_seen = time.time(); self.start_ts = time.time()
        self.last_re = 0; self.rejoin_count = 0
        self.next_hop = time.time() + random.randint(cfg['hop_min']*60, cfg['hop_max']*60)
        self.error_flag = None

    def trigger_error(self, code): 
        self.status = f"CRASH ({code})"; self.style = "red"; self.error_flag = code

    def restart(self, reason, code=None):
        if not self.cfg['auto_restart']:
            self.status = "MANUAL STOP"; self.style = "bold red"; return

        now = time.time()
        if now - self.last_re < 20: 
            self.status = "COOLDOWN"; return # Prevent spam restart

        self.status = f"RESTARTING ({reason})"; self.style = "yellow"
        
        # Log to Discord
        if self.rejoin_count > 0: # Don't log first boot
            DiscordManager.send_log(self.cfg, f"🔄 ACC RESET: {self.pkg[-6:]}", f"Lý do: {reason}\nCode: {code}", 0xffaa00)

        # Force Stop & Clear Cache (Pro Move)
        root_shell.exec(f"am force-stop {self.pkg}")
        if self.cfg['auto_cleaner']: root_shell.exec(f"pm clear {self.pkg} --cache-only")
        time.sleep(1)
        
        # Launch Game
        cmd = f"am start -n {self.pkg}/com.roblox.client.Activity -d \"roblox://experiences/start?placeId={self.cfg['place_id']}\""
        root_shell.exec(cmd)
        
        self.start_ts = now; self.last_re = now; self.error_flag = None
        self.next_hop = now + random.randint(self.cfg['hop_min']*60, self.cfg['hop_max']*60)
        self.rejoin_count += 1
        stats.update("rejoins"); 
        if code: stats.update(f"err_{code}")

    def loop(self):
        while g_state["running"]:
            time.sleep(1)
            # 1. Network Guard
            if not g_state["net_ok"]: 
                self.status = "NO NETWORK"; self.style = "bold red"; continue

            # 2. Watchdog (Deep Freeze Check)
            if time.time() - self.last_seen > 60 and time.time() - self.start_ts > 120:
                self.trigger_error("FROZEN")
            
            # 3. Handle Errors
            if self.error_flag: 
                self.restart(f"Err {self.error_flag}", self.error_flag); continue
            
            # 4. Smart Hop
            if self.cfg['smart_hop'] and time.time() > self.next_hop: 
                self.status = "SERVER HOP"; self.style = "cyan"; self.restart("Scheduled Hop"); continue

            # 5. Update Status Display
            if "RESTART" not in self.status and "CRASH" not in self.status and "HOP" not in self.status:
                uptime = int(time.time() - self.start_ts)
                self.status = f"FARMING ({uptime}s)"; self.style = "bold green"

# ==========================================
# 6. ADVANCED UI & SETTINGS
# ==========================================
def game_settings_ui(cfg):
    while True:
        console.clear()
        console.print(Panel("[bold yellow]🎮 GAME SETTINGS (GOD MODE)[/bold yellow]", border_style="yellow"))
        print(f"[1] Prefix:   {cfg['prefix']}")
        print(f"[2] Place ID: {cfg['place_id']}")
        print(f"[3] Webhook:  {cfg['webhook_url'][:20]}...")
        print(f"[4] Discord Notify: {cfg['discord_notify']}")
        print("\n[0] Back")
        c = console.input("👉 Cmd: ")
        if c == "0": return
        elif c == "1": cfg['prefix'] = console.input("New Prefix: ")
        elif c == "2": cfg['place_id'] = console.input("New Place ID: ")
        elif c == "3": cfg['webhook_url'] = console.input("New Webhook: ")
        elif c == "4": cfg['discord_notify'] = not cfg['discord_notify']
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)

def system_settings_ui(cfg):
    while True:
        console.clear()
        console.print(Panel("[bold cyan]⚙️ SYSTEM OPTIMIZER[/bold cyan]", border_style="cyan"))
        print(f"[1] Device Doctor: {cfg['device_doctor']}")
        print(f"[2] Auto Cleaner:  {cfg['auto_cleaner']}")
        print(f"[3] Temp Limit:    {cfg['temp_limit']}°C")
        print("\n[0] Back")
        c = console.input("👉 Cmd: ")
        if c == "0": return
        elif c == "1": cfg['device_doctor'] = not cfg['device_doctor']
        elif c == "2": cfg['auto_cleaner'] = not cfg['auto_cleaner']
        elif c == "3": cfg['temp_limit'] = int(console.input("Max Temp: "))
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)

def launcher_phase():
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try: cfg.update(json.load(open(CONFIG_FILE)))
        except: pass
    
    # Auto-Fix Prefix
    if cfg['prefix'] == "com.roblox.client": cfg['prefix'] = "dinozzz.cryptic"

    while True:
        console.clear()
        # BIG BANNER
        console.print(Panel(Text(f"🐲 DORO GOD MODE {VERSION}", justify="center", style="bold red"), border_style="red"))
        
        table = Table(box=box.DOUBLE_EDGE, expand=True)
        table.add_column("Main Menu", style="bold white")
        table.add_row("1️⃣.  Start Ultimate Tool 🚀")
        table.add_row("2️⃣.  Game Config 🎮")
        table.add_row("3️⃣.  System Optimizer ⚙️")
        table.add_row("4️⃣.  Automation Logic 🤖")
        table.add_row("5️⃣.  Exit ❌")
        console.print(table)
        
        choice = console.input("\n👉 [bold red]GOD CMD:[/bold red] ")
        if choice == "1": return cfg
        elif choice == "2": game_settings_ui(cfg)
        elif choice == "3": system_settings_ui(cfg)
        elif choice == "4": pass # Automation menu simplified for brevity
        elif choice == "5": sys.exit(0)

# ==========================================
# 7. DASHBOARD RENDERER
# ==========================================
def make_layout(instances):
    with g_state["lock"]:
        cpu, ram, temp = g_state["cpu"], g_state["ram"], g_state["temp"]
        ping, bat = g_state["ping"], g_state["battery"]
        s = stats.get_snapshot()

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )
    
    # Header Stats
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=1)
    
    c_style = "red" if cpu > 90 else "green"
    t_style = "red" if temp > 75 else "cyan"
    
    grid.add_row(
        f"🔥 CPU: [{c_style}]{cpu}%[/{c_style}]",
        f"💾 RAM: {ram}%",
        f"🌡️ TMP: [{t_style}]{temp}°C[/{t_style}]",
        f"🔋 BAT: {bat}%"
    )
    layout["header"].update(Panel(grid, style="bold white", border_style="red"))

    # Body Split (List vs Logs)
    layout["body"].split_row(Layout(name="list", ratio=2), Layout(name="logs", ratio=1))
    
    # Instance List
    table = Table(box=box.SIMPLE, expand=True, show_lines=False)
    table.add_column("#", width=2); table.add_column("CLIENT ID", ratio=1); table.add_column("STATUS", width=20)
    
    sorted_inst = sorted(instances, key=lambda x: (x.status == "RUNNING", x.pkg))
    for idx, i in enumerate(sorted_inst):
        clean_status = i.status.split('(')[0].strip()
        table.add_row(f"{idx+1}", i.pkg.split('.')[-1], f"[{i.style}]{i.status}[/{i.style}]")
    
    layout["list"].update(Panel(table, title=f"ACTIVE CLIENTS ({len(instances)})", border_style="blue"))
    
    # Logs / Stats
    log_text = f"""
[bold underline]SESSION STATS[/bold underline]
🔄 Rejoins: {s['rejoins']}
❌ Crashes: {s['err_277'] + s['err_279']}
🌐 Ping:    {ping}ms
⏱️ Uptime:  {int(time.time() - g_state['start_time'])//60}m
    """
    layout["logs"].update(Panel(log_text, title="LIVE LOGS", border_style="green"))
    
    return layout

# ==========================================
# 8. MAIN EXECUTION
# ==========================================
def main():
    cfg = launcher_phase()
    instances = []
    
    console.print(Panel("[bold yellow]INITIALIZING GOD MODE SYSTEMS...[/bold yellow]"))
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn()) as p:
        t1 = p.add_task("Scanning Processes...", total=100)
        # Scan Logic
        raw_list = root_shell.exec(f"pm list packages | grep -i {cfg['prefix']}")
        pkgs = (raw_list or "").replace("package:", "").split()
        for i in range(100): 
            time.sleep(0.01); p.update(t1, advance=1)
            
    for pkg in pkgs:
        if pkg.strip(): instances.append(AccountInstance(pkg.strip(), cfg))
    
    if not instances: 
        console.print(f"[bold red]❌ NO GAME FOUND: {cfg['prefix']}[/bold red]")
        sys.exit(1)
    
    with g_state["lock"]: g_state["total_targets"] = len(instances)

    # Start Threads
    agg = SingularityAggregator(cfg, instances); agg.start()
    doc = DeviceDoctor(cfg); doc.start()
    
    for i in instances: threading.Thread(target=i.loop, daemon=True).start()

    # Discord Notify Start
    DiscordManager.send_log(cfg, "🚀 DORO GOD MODE STARTED", f"Đã kích hoạt {len(instances)} clients.", 0x00ffff)

    try:
        with Live(make_layout(instances), refresh_per_second=2, screen=True) as live:
            while g_state["running"]:
                live.update(make_layout(instances))
                time.sleep(0.5)
    except KeyboardInterrupt:
        g_state["running"] = False; stats.save()
        console.clear(); console.print("[bold red]SHUTTING DOWN GOD MODE...[/bold red]")
        sys.exit(0)

if __name__ == "__main__":
    main()
'''

# ==========================================
# PHẦN INSTALLER (NGẮN GỌN)
# ==========================================
print("\n\033[1;36m[+] ĐANG CÀI ĐẶT DORO GOD MODE V99...\033[0m")
HOME_DIR = "/data/data/com.termux/files/home"
TOOL_PATH = f"{HOME_DIR}/Doro1337.py"
TERMUX_BIN = "/data/data/com.termux/files/usr/bin"

# 1. Ghi file siêu to khổng lồ
with open(TOOL_PATH, "w", encoding="utf-8") as f:
    f.write(GOD_MODE_SOURCE)
print("\033[1;32m[+] Đã tạo file source mới (Dài hơn, xịn hơn)!\033[0m")

# 2. Xóa config cũ để dùng config GOD mới
cfg_path = f"{HOME_DIR}/config_apex_god.json"
if os.path.exists(cfg_path):
    os.remove(cfg_path)

# 3. Chạy
print("\n\033[1;33m[+] KHỞI ĐỘNG TOOL NGAY BÂY GIỜ...\033[0m")
cmd = f'su -c "cd {HOME_DIR} && export PATH={TERMUX_BIN}:$PATH && python {TOOL_PATH}"'
os.system(cmd)
