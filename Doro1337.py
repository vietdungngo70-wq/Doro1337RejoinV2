#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍊 DORO ULTIMATE MANAGER - v55.0 (AUTOMATION MASTER)
Changelog:
1. Automation Menu: Dedicated submenu for Smart Hop & Auto Restart settings.
2. Auto-Restart Toggle: Option to disable auto-reboot (useful for debugging).
3. Organized CMD: Grouped Game/Webhook settings to clean up the main interface.
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
from collections import deque, defaultdict

try:
    from rich.live import Live
    from rich.table import Table
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.console import Console
    from rich.align import Align
    from rich import box
    from rich.text import Text
except ImportError:
    print("❌ Thiếu thư viện 'rich'. Chạy: pip install rich")
    sys.exit(1)

CONFIG_FILE = "config_apex_v55.json"
VERSION = "v55.0 AUTO-MASTER"
console = Console()

# Global Shared State
g_state = {
    "start_time": time.time(),
    "cpu": 0, "ram": 0, "temp": 0, "ping": 0,
    "lock": threading.Lock(),
    "running": True,
    "restart_log": deque(maxlen=200),
    "pid_map": {}, "pkg_state": {}, "total_targets": 0,
    "net_ok": True, "core_count": os.cpu_count() or 8
}

DEFAULT_CONFIG = {
    "place_id": "2753915549", "place_name": "Blox Fruit", "prefix": "com.roblox.client", 
    "webhook_url": "", "smart_hop": True, "hop_min": 15, "hop_max": 25,
    "auto_restart": True, "ram_limit": 90, "cpu_limit": 95,
    "clone_ram_limit": 4096, "clone_cpu_limit": 90,
    "check_interval": 5, "net_recovery": True, "max_hourly_restarts": 10
}

# ==========================================
# 1. KERNEL SHELL
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

class StatsManager:
    def __init__(self): self.data = {"rejoins": 0, "crashes": 0, "err_277": 0, "err_279": 0}; self.load()
    def load(self): 
        if os.path.exists("stats.json"): 
            try: self.data = json.load(open("stats.json"))
            except: pass
    def save(self):
    with g_state["lock"]:
        json.dump(self.data, open("stats.json", "w"))

def update(self, k):
    with g_state["lock"]:
        self.data[k] += 1

def get_snapshot(self):
    with g_state["lock"]:
        return self.data.copy()

stats = StatsManager()

# ==========================================
# 2. LOGIC ENGINE
# ==========================================
class SingularityAggregator(threading.Thread):
    def __init__(self, cfg, instances):
        super().__init__(daemon=True); self.cfg = cfg; self.inst_map = {i.pkg: i for i in instances}
        self.prev_global_total = 0; self.prev_global_idle = 0; self.prev_proc_ticks = {}; self.cycle_count = 0
        self.pkg_cpu_history = defaultdict(lambda: deque(maxlen=3))

    def run(self):
        while g_state["running"]:
            time.sleep(3); self.cycle_count += 1
            try:
                if self.cycle_count % 10 == 0:
                    res = root_shell.exec("ping -c 1 -W 1 8.8.8.8")
                    ping = float(re.search(r'time=([\d\.]+)', res).group(1)) if res and "time=" in res else 999
                    with g_state["lock"]: g_state["net_ok"], g_state["ping"] = (ping < 500), int(ping)

                raw_map = root_shell.exec(f"grep -a '{self.cfg['prefix']}' /proc/[0-9]*/cmdline")
                pid_to_pkg = {int(l.split(":")[0].split("/")[2]): l.split(":")[1].strip().replace('\x00','') for l in raw_map.splitlines() if ":" in l} if raw_map else {}

                active = list(pid_to_pkg.keys())
                proc_raw = ""
                for i in range(0, len(active), 30):
                    proc_raw += root_shell.exec("".join([f"cat /proc/{p}/stat /proc/{p}/status 2>/dev/null; echo 'PRC:{p}';" for p in active[i:i+30]])) + "\n"

                glb = root_shell.exec("cat /proc/stat; echo 'G'; cat /proc/meminfo; echo 'G'; cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0").split('G')
                if len(glb) < 3: continue
                
                ps = glb[0].split(); c_tot = sum(int(x) for x in ps[1:]); c_idl = int(ps[4])+int(ps[5])
                if self.prev_global_total == 0: self.prev_global_total = c_tot; self.prev_global_idle = c_idl; continue
                d_tot = c_tot - self.prev_global_total; d_idl = c_idl - self.prev_global_idle
                self.prev_global_total = c_tot; self.prev_global_idle = c_idl
                
                mt = int(re.search(r'\d+', glb[1]).group()); m = re.search(r'MemAvailable:\s+(\d+)', glb[1])
ma = int(m.group(1)) if m else 0
                
                pkg_m = defaultdict(lambda: {"c":0, "r":0, "pids":[]})
                seen = set()
                for b in proc_raw.split("PRC:"):
                    if not b.strip(): continue
                    l = b.strip().splitlines()
                    stat = next((x for x in l if ")" in x), None); rss = next((x for x in l if "VmRSS" in x), None)
                    if not stat: continue
                    pid = int(stat.split()[0]); pkg = pid_to_pkg.get(pid); seen.add(pid)
                    
                    ticks = int(stat.split()[13]) + int(stat.split()[14])
                    prev = self.prev_proc_ticks.get(pid, 0)
                    delta = max(0, ticks - prev) if prev > 0 else 0
                    self.prev_proc_ticks[pid] = ticks
                    
                    pkg_m[pkg]["c"] += delta; pkg_m[pkg]["r"] += int(re.search(r'\d+', rss).group()) if rss else 0
                    pkg_m[pkg]["pids"].append(pid)

                for p in list(self.prev_proc_ticks): 
                    if p not in seen: del self.prev_proc_ticks[p]

                final = {}
                for pkg, m in pkg_m.items():
                    raw_c = int(100 * m["c"] / d_tot * g_state["core_count"]) if d_tot > 0 else 0
                    self.pkg_cpu_history[pkg].append(raw_c)
                    final[pkg] = {"cpu": int(sum(self.pkg_cpu_history[pkg])/len(self.pkg_cpu_history[pkg])), "ram": m["r"]//1024, "ts": time.time(), "pids": m["pids"]}

                with g_state["lock"]:
                    g_state["cpu"] = int(100*(d_tot-d_idl)/d_tot) if d_tot>0 else 0
                    g_state["ram"] = int((mt-ma)/mt*100)
                    g_state["temp"] = int(int(glb[2].strip())/1000)
                    for pkg, d in final.items():
                        t = self.inst_map.get(pkg)
                        if t and d["pids"] and t.pid != d["pids"][0]: t.pid = d["pids"][0]; self.pkg_cpu_history[pkg].clear()
                        g_state["pkg_state"][pkg] = d
                        for pid in d["pids"]: g_state["pid_map"][pid] = t
            except: pass

class LogStreamer(threading.Thread):
    def __init__(self): super().__init__(daemon=True)
    def run(self):
        while g_state["running"]:
            try:
                subprocess.run(["su", "-c", "logcat -c"], timeout=2)
                p = subprocess.Popen(["su", "-c", "logcat -v brief *:E"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, text=False)
                fd = p.stdout.fileno(); buf = b""
                while g_state["running"]:
                    if not select.select([fd], [], [], 2)[0]: continue
                    c = os.read(fd, 4096)
                    if not c: break
                    buf += c; 
                    if len(buf) > 2*1024*1024: buf = b""
                    while b'\n' in buf:
                        l, buf = buf.split(b'\n', 1)
                        try:
                            s = l.decode('utf-8', 'ignore')
                            if "Error Code" in s or "ConnectionLost" in s:
                                m = re.search(r'\((\s*\d+)\)', s)
                                if m: 
                                    with g_state["lock"]: i = g_state["pid_map"].get(int(m.group(1)))
                                    if i: i.trigger_error(277 if "277" in s or "ConnectionLost" in s else 279)
                        except: pass
                p.terminate()
            except: time.sleep(1)

class AccountInstance:
    def __init__(self, pkg, cfg):
        self.pkg = pkg; self.cfg = cfg; self.pid = None
        self.status = "WARMUP"; self.style = "blue"
        self.mem_usage = 0; self.cpu_usage = 0
        self.start_ts = time.time(); self.last_re = 0
        self.next_hop = time.time() + random.randint(cfg['hop_min']*60, cfg['hop_max']*60)
        self.error_flag = None

    def trigger_error(self, code): 
        self.status = f"DISCONNECT ({code})"; self.style = "red"
        self.error_flag = code

    def restart(self, reason, code=None):
        # [NEW] Check Auto Restart Flag
        if not self.cfg['auto_restart']:
            self.status = "STOPPED (MANUAL)"; self.style = "bold red"
            return # Stop here, do not exec restart

        now = time.time()
        if now - self.last_re < 15: return
        self.status = "REJOINING"; self.style = "yellow"
        
        with g_state["lock"]:
            l = max(5, int(g_state["total_targets"]*0.1)+5)
            if len(g_state["restart_log"]) >= l and now - g_state["restart_log"][0] < 60: 
                self.status = "WAIT QUEUE"; return
            g_state["restart_log"].append(now)

        self.last_re = now
        root_shell.exec(f"am force-stop {self.pkg}; sleep 0.5; am start -n {self.pkg}/com.roblox.client.Activity -d \"roblox://experiences/start?placeId={self.cfg['place_id']}\"")
        self.start_ts = now; self.error_flag = None; self.next_hop = now + random.randint(self.cfg['hop_min']*60, self.cfg['hop_max']*60)
        stats.update("rejoins"); 
        if code: stats.update(f"err_{code}")

    def loop(self):
        while g_state["running"]:
            time.sleep(1)
            if not g_state["net_ok"]: self.status = "NET LOST"; self.style = "bold red"; continue
            
            with g_state["lock"]: d = g_state["pkg_state"].get(self.pkg)
            if d: self.cpu_usage = d['cpu']; self.mem_usage = d['ram']; ts = d['ts']
            else: ts = 0

            if time.time() - ts > 45 and time.time() - self.start_ts > 60: 
                self.status = "DIED"; self.style = "red"; self.restart("Died"); continue

            if self.error_flag: self.restart(f"Err {self.error_flag}", self.error_flag); continue
            
            if self.cpu_usage > self.cfg['clone_cpu_limit']: self.restart("CPU High"); continue
            if self.mem_usage > self.cfg['clone_ram_limit']: self.restart("RAM Leak"); continue
            
            if self.cfg['smart_hop'] and time.time() > self.next_hop: 
                self.status = "HOPPING"; self.style = "cyan"; self.restart("Hop"); continue
            
            if "REJOIN" not in self.status and "DISC" not in self.status and "HOP" not in self.status and "STOP" not in self.status:
                self.status = "RUNNING"; self.style = "bold green"

# ==========================================
# 3. MENUS & UI
# ==========================================
def delete_package_ui(prefix):
    while True:
        console.clear()
        console.print(Panel("🔥 [bold red]DELETE PACKAGE MANAGER[/bold red] 🔥", border_style="red"))
        raw = root_shell.exec(f"pm list packages | grep {prefix}").replace("package:", "")
        pkgs = [p.strip() for p in raw.splitlines() if p.strip()]
        
        if not pkgs:
            console.print("[yellow]No packages found![/yellow]"); console.input("\n[Enter]..."); return

        table = Table(box=box.SIMPLE)
        table.add_column("#", style="cyan"); table.add_column("Package Name", style="white")
        for idx, p in enumerate(pkgs): table.add_row(str(idx+1), p)
        console.print(table); console.print("\n[0] Back")
        
        choice = console.input("👉 [bold red]Select # to DELETE:[/bold red] ")
        if choice == "0": return
        try:
            target = pkgs[int(choice)-1]
            if console.input(f"⚠️ Uninstall {target}? (y/n): ") == 'y':
                root_shell.exec(f"pm uninstall {target}"); console.print("[green]Done![/green]"); time.sleep(1)
        except: pass

def game_settings_ui(cfg):
    while True:
        console.clear()
        console.print(Panel("🎮 [bold blue]GAME SETTINGS[/bold blue] 🎮", border_style="blue"))
        print(f"[1] Prefix:   {cfg['prefix']}")
        print(f"[2] Place ID: {cfg['place_id']}")
        print(f"[3] Webhook:  {cfg['webhook_url'][:30]}...")
        print("\n[0] Back")
        c = console.input("👉 Option: ")
        if c == "0": return
        elif c == "1": cfg['prefix'] = console.input("New Prefix: ")
        elif c == "2": cfg['place_id'] = console.input("New Place ID: ")
        elif c == "3": cfg['webhook_url'] = console.input("New Webhook: ")
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)

def automation_ui(cfg):
    while True:
        console.clear()
        console.print(Panel("🤖 [bold magenta]AUTOMATION CONFIG[/bold magenta] 🤖", border_style="magenta"))
        
        hop_state = "[green]ON[/green]" if cfg['smart_hop'] else "[red]OFF[/red]"
        ar_state = "[green]ON[/green]" if cfg['auto_restart'] else "[red]OFF[/red]"
        
        print(f"[1] Smart Hop:    {hop_state}")
        print(f"[2] Hop Time:     {cfg['hop_min']} - {cfg['hop_max']} min")
        print(f"[3] Auto Restart: {ar_state}")
        print("\n[0] Back")
        
        c = console.input("👉 Option: ")
        if c == "0": return
        elif c == "1": cfg['smart_hop'] = not cfg['smart_hop']
        elif c == "2": 
            cfg['hop_min'] = int(console.input("Min (m): "))
            cfg['hop_max'] = int(console.input("Max (m): "))
        elif c == "3": cfg['auto_restart'] = not cfg['auto_restart']
        
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)

def launcher_phase():
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try: cfg.update(json.load(open(CONFIG_FILE)))
        except: pass

    while True:
        console.clear()
        console.print(Panel(Text(f"🍊 DORO MANAGER {VERSION}", justify="center", style="bold orange1"), border_style="orange1"))
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, expand=True)
        table.add_column("Option", width=25); table.add_column("Description", style="dim")
        
        table.add_row("1️⃣. Start Tool 🎃", "[bold green]Launch Dashboard[/bold green]")
        table.add_row("2️⃣. Game Settings 🎮", "Prefix, PlaceID, Webhook")
        table.add_row("3️⃣. Automation 🤖", "Smart Hop, Auto Restart")
        table.add_row("4️⃣. System Limits 📉", f"CPU: {cfg['cpu_limit']}%, RAM: {cfg['ram_limit']}%")
        table.add_row("5️⃣. Delete Package 🔥", "Uninstall Clones")
        table.add_row("6️⃣. Stop Tool 🥀", "Exit")
        
        console.print(table)
        choice = console.input("\n👉 [bold cyan]Command:[/bold cyan] ")
        
        if choice == "1": return cfg
        elif choice == "2": game_settings_ui(cfg)
        elif choice == "3": automation_ui(cfg)
        elif choice == "4": 
            cfg['cpu_limit'] = int(console.input("CPU Limit: "))
            cfg['ram_limit'] = int(console.input("RAM Limit: "))
            with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)
        elif choice == "5": delete_package_ui(cfg['prefix'])
        elif choice == "6": sys.exit(0)

# ==========================================
# 4. DASHBOARD UI
# ==========================================
def make_layout(instances):
    with g_state["lock"]:
        cpu, ram, temp = g_state["cpu"], g_state["ram"], g_state["temp"]
        ping, net = g_state["ping"], g_state["net_ok"]
        s = stats.get_snapshot(); lim = len(g_state["restart_log"])

    layout = Layout()
    layout.split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=3))

    sys_table = Table(box=None, expand=True)
    sys_table.add_column("Metric", style="bold white"); sys_table.add_column("Value", justify="right")
    
    c_col = "red" if cpu > 90 else "green"; r_col = "red" if ram > 90 else "blue"
    sys_table.add_row("🔥 CPU", f"[{c_col}]{cpu}%[/{c_col}]")
    sys_table.add_row("💾 RAM", f"[{r_col}]{ram}%[/{r_col}]")
    sys_table.add_row("🌡️ TMP", f"{temp}°C")
    sys_table.add_row("🌐 NET", f"[{'green' if net else 'red'}]{ping}ms[/{'green' if net else 'red'}]")
    
    layout["left"].split_column(
        Layout(Panel(Align.center(sys_table), title="[bold]VITALS[/bold]", border_style="orange1"), ratio=2),
        Layout(Panel(f"Rej: {s['rejoins']}\nErr: {s['err_277']}", title="LOGS", border_style="blue"), ratio=1)
    )

    table = Table(box=box.SIMPLE_HEAD, expand=True, show_lines=False)
    table.add_column("ID", width=3, style="dim")
    table.add_column("Package", ratio=1)
    table.add_column("Status", width=18)

    sorted_inst = sorted(instances, key=lambda x: (x.status == "RUNNING", x.pkg))
    
    for idx, i in enumerate(sorted_inst):
        icon = "🟢"
        if "REJOIN" in i.status: icon = "🔄"
        elif "DISC" in i.status: icon = "🔌"
        elif "HOP" in i.status: icon = "🐰"
        elif "WARM" in i.status: icon = "⏳"
        elif "DIED" in i.status: icon = "💀"
        elif "NET" in i.status: icon = "📡"
        elif "STOP" in i.status: icon = "⛔" # New Icon for Stopped

        clean_status = i.status.split('(')[0].strip()
        table.add_row(str(idx+1), i.pkg.split('.')[-1][:12], f"{icon} [{i.style}]{clean_status}[/{i.style}]")

    layout["right"].update(Panel(table, title=f"📱 Active: {len(instances)}", border_style="white"))
    return layout

# ==========================================
# 5. ENTRY POINT
# ==========================================
def main():
    cfg = launcher_phase()
    instances = []
    
    with console.status("[bold green]Booting System...[/bold green]"):
        raw = root_shell.exec(f"grep -l '{cfg['prefix']}' /proc/[0-9]*/cmdline")
        pkgs = root_shell.exec(f"pm list packages | grep {cfg['prefix']}").replace("package:", "").split()
        for p in pkgs:
            if p.strip(): instances.append(AccountInstance(p.strip(), cfg))
    
    if not instances: console.print("[red]No clones found![/red]"); sys.exit(1)
    with g_state["lock"]: g_state["total_targets"] = len(instances)

    agg = SingularityAggregator(cfg, instances); agg.start()
    log = LogStreamer(); log.start()
    for i in instances: threading.Thread(target=i.loop, daemon=True).start()

    try:
        with Live(make_layout(instances), refresh_per_second=2, screen=True) as live:
            while g_state["running"]:
       
       live.update(make_layout(instances))
                time.sleep(0.5)
    except KeyboardInterrupt:
        g_state["running"] = False
        stats.save(); root_shell.exec("pkill logcat")
        console.clear(); console.print("[bold red]System Halted.[/bold red]")
        sys.exit(0)

if __name__ == "__main__":
    main()