#!/usr/bin/env python3
"""systool - utilitarios READ-ONLY para administracao de Linux.

NAO altera nada no sistema: apenas LE /proc, /sys, sockets, disco e chama
comandos de consulta (journalctl, systemctl status, ss). Seguro para rodar
em qualquer servidor via SSH, inclusive sem pacotes extras.

Comandos:
    systool.py info              Inventario do sistema (host, kernel, CPU, RAM, discos, rede, temp)
    systool.py top [-n 10]       Top processos por CPU e por memoria
    systool.py disk [PATH]       Uso por ponto de montagem + maiores itens de PATH
    systool.py ports             Portas em escuta e o processo dono
    systool.py conns [-n 10]     Conexoes ativas via ss (estados, top talkers, top peers)
    systool.py certs HOST[:PORT] Validade do certificado TLS (pode repetir)
    systool.py logs [-n 15]      Resumo de erros do kernel e logins falhos
    systool.py health            Diagnostico agregado (OK/WARN/CRIT)

Opcionais: psutil (top mais preciso), matplotlib (disk --svg).
"""
import argparse
import heapq
import os
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone

REAL_FS = {
    "ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs", "reiserfs", "jfs",
    "vfat", "exfat", "ntfs", "ntfs3", "zfs", "nfs", "nfs4", "cifs",
    "smb3", "overlay",
}
PSEUDO_TOP = {"/proc", "/sys", "/dev", "/run"}


# ----------------------------------------------------------------- utils
def human(n):
    n = float(n)
    for u in ("B", "K", "M", "G", "T", "P"):
        if abs(n) < 1024:
            return f"{n:6.1f}{u}"
        n /= 1024
    return f"{n:.1f}E"


def read_kv(path):
    d = {}
    try:
        with open(path) as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    d[k.strip()] = v.strip()
    except OSError:
        pass
    return d


def read_env(path):
    """Le arquivos CHAVE=VALOR (ex.: /etc/os-release)."""
    d = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return d


def have(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def run(cmd, timeout=15):
    """Executa um comando de CONSULTA. Nunca altera o sistema."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout or ""
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
        return ""


def human_uptime(seconds):
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    parts = [f"{d}d" if d else "", f"{h}h" if h else "", f"{m}m"]
    return " ".join(p for p in parts if p).strip() or "0m"


def real_mounts():
    out = []
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                dev, mnt, fstype = parts[0], parts[1], parts[2]
                if fstype in REAL_FS:
                    out.append((dev, mnt, fstype))
    except OSError:
        pass
    return out


# ----------------------------------------------------------------- info
def cmd_info(args):
    print("=" * 60)
    print("INVENTARIO DO SISTEMA")
    print("=" * 60)

    host = socket.gethostname()
    fqdn = socket.getfqdn()
    osrel = read_env("/etc/os-release")
    uname = os.uname()
    print(f"Host        : {host}  ({fqdn})")
    print(f"SO          : {osrel.get('PRETTY_NAME', '?')}")
    print(f"Kernel      : {uname.release}  ({uname.machine})")
    try:
        up = float(open("/proc/uptime").read().split()[0])
    except (OSError, ValueError, IndexError):
        up = 0
    print(f"Uptime      : {human_uptime(up)}")
    try:
        l1, l5, l15 = os.getloadavg()
        print(f"Load avg    : {l1:.2f}  {l5:.2f}  {l15:.2f}  (CPUs: {os.cpu_count()})")
    except OSError:
        pass

    # CPU
    model = "?"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    print(f"CPU         : {model}  x {os.cpu_count()}")

    # Memoria
    mi = read_kv("/proc/meminfo")
    def kb(k):
        try:
            return int(mi.get(k, "0 kB").split()[0]) * 1024
        except Exception:
            return 0
    total, avail = kb("MemTotal"), kb("MemAvailable")
    swt, swf = kb("SwapTotal"), kb("SwapFree")
    if total:
        print(f"RAM         : {human(total - avail)} usada / {human(total)} "
              f"({100 * (total - avail) / total:.0f}%)")
    if swt:
        print(f"Swap        : {human(swt - swf)} usada / {human(swt)}")

    # Discos
    print("Discos      :")
    seen = set()
    for dev, mnt, fstype in real_mounts():
        if mnt in seen:
            continue
        seen.add(mnt)
        try:
            u = shutil.disk_usage(mnt)
        except OSError:
            continue
        pct = 100 * u.used / u.total if u.total else 0
        print(f"  {mnt:<24} {fstype:<8} {human(u.used):>10} / {human(u.total):>10}  {pct:4.0f}%")

    # Rede
    print("Rede        :")
    try:
        for ifc in sorted(os.listdir("/sys/class/net")):
            base = f"/sys/class/net/{ifc}"
            try:
                state = open(f"{base}/operstate").read().strip()
            except OSError:
                state = "?"
            try:
                speed = open(f"{base}/speed").read().strip()
            except OSError:
                speed = "-"
            print(f"  {ifc:<12} {state:<8} {speed:>6} Mb/s")
    except OSError:
        pass

    # Temperaturas
    temps = []
    for tz in sorted(os.listdir("/sys/class/thermal")) if os.path.isdir("/sys/class/thermal") else []:
        if not tz.startswith("thermal_zone"):
            continue
        try:
            raw = int(open(f"/sys/class/thermal/{tz}/temp").read().strip())
            label = open(f"/sys/class/thermal/{tz}/type").read().strip()
            temps.append((label, raw / 1000.0))
        except OSError:
            continue
    if temps:
        print("Temperatura :")
        for label, c in temps:
            print(f"  {label:<24} {c:6.1f} C")


# ----------------------------------------------------------------- top
def _have_psutil():
    return have("psutil")


def _top_psutil(n):
    import psutil
    procs = list(psutil.process_iter(["pid", "name"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except Exception:
            pass
    time.sleep(0.4)
    rows = []
    for p in procs:
        try:
            with p.oneshot():
                rows.append({
                    "pid": p.pid, "name": p.name(),
                    "cpu": p.cpu_percent(None),
                    "mem": p.memory_percent(),
                    "rss": p.memory_info().rss,
                })
        except Exception:
            continue
    by_cpu = sorted(rows, key=lambda r: r["cpu"], reverse=True)[:n]
    by_mem = sorted(rows, key=lambda r: r["rss"], reverse=True)[:n]
    return by_cpu, by_mem


def _snap_proc():
    hz = os.sysconf("SC_CLK_TCK")
    page = os.sysconf("SC_PAGE_SIZE")
    snap = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/stat") as f:
                stat = f.read()
        except OSError:
            continue
        r = stat.rfind(")")
        if r < 0:
            continue
        comm = stat[stat.find("(") + 1:r]
        rest = stat[r + 2:].split()
        try:
            ticks = int(rest[11]) + int(rest[12])
        except (IndexError, ValueError):
            continue
        try:
            rss = int(open(f"/proc/{pid}/statm").read().split()[1]) * page
        except (OSError, IndexError):
            rss = 0
        snap[pid] = (comm, ticks, rss, hz)
    return snap


def _top_proc(n, interval=0.5):
    a = _snap_proc()
    time.sleep(interval)
    b = _snap_proc()
    rows = []
    ncpu = os.cpu_count() or 1
    for pid, (comm, ticks, rss, hz) in b.items():
        old = a.get(pid, (comm, ticks, 0, hz))[1]
        cpu = (ticks - old) / hz / interval * 100.0 / ncpu
        rows.append({"pid": int(pid), "name": comm, "cpu": cpu, "rss": rss,
                     "mem": rss / (read_total_mem() or 1) * 100})
    by_cpu = sorted(rows, key=lambda r: r["cpu"], reverse=True)[:n]
    by_mem = sorted(rows, key=lambda r: r["rss"], reverse=True)[:n]
    return by_cpu, by_mem


_TOTAL_MEM = None


def read_total_mem():
    global _TOTAL_MEM
    if _TOTAL_MEM is None:
        try:
            _TOTAL_MEM = int(read_kv("/proc/meminfo").get("MemTotal", "0 kB").split()[0]) * 1024
        except Exception:
            _TOTAL_MEM = 0
    return _TOTAL_MEM


def cmd_top(args):
    n = args.n
    if _have_psutil():
        mode = "psutil"
        by_cpu, by_mem = _top_psutil(n)
    else:
        mode = "/proc (sem psutil)"
        by_cpu, by_mem = _top_proc(n)

    print(f"=== TOP {n} POR CPU  [fonte: {mode}] ===")
    print(f"{'PID':>7}  {'CPU%':>6}  {'RAM%':>6}  {'RSS':>9}  PROCESSO")
    for r in by_cpu:
        print(f"{r['pid']:>7}  {r['cpu']:6.1f}  {r['mem']:6.1f}  {human(r['rss']):>9}  {r['name'][:30]}")
    print()
    print(f"=== TOP {n} POR MEMORIA  [fonte: {mode}] ===")
    print(f"{'PID':>7}  {'RAM%':>6}  {'RSS':>9}  {'CPU%':>6}  PROCESSO")
    for r in by_mem:
        print(f"{r['pid']:>7}  {r['mem']:6.1f}  {human(r['rss']):>9}  {r['cpu']:6.1f}  {r['name'][:30]}")


# ----------------------------------------------------------------- disk
def _scan_dir(path, top):
    root = os.path.abspath(path)
    total = 0
    children = {}
    largest = []
    n = 0
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None, followlinks=False):
        if dirpath == root and root == "/":
            dirnames[:] = [d for d in dirnames if os.path.join("/", d) not in PSEUDO_TOP]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                st = os.lstat(fp)
            except OSError:
                continue
            if not os.path.isfile(fp):
                continue
            sz = st.st_size
            total += sz
            n += 1
            rel = os.path.relpath(fp, root)
            head = rel.split(os.sep, 1)[0]
            children[head] = children.get(head, 0) + sz
            if len(largest) < top:
                heapq.heappush(largest, (sz, fp))
            elif sz > largest[0][0]:
                heapq.heapreplace(largest, (sz, fp))
    return total, children, sorted(largest, reverse=True)


def _disk_svg(saida):
    if not have("matplotlib"):
        print("  (matplotlib ausente: pulando SVG)")
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels, used = [], []
    seen = set()
    for dev, mnt, _ in real_mounts():
        if mnt in seen:
            continue
        seen.add(mnt)
        try:
            u = shutil.disk_usage(mnt)
        except OSError:
            continue
        labels.append(mnt)
        used.append(100 * u.used / u.total if u.total else 0)
    if not labels:
        print("  (nenhum sistema de arquivos real)")
        return
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.8), 4))
    bars = ax.bar(labels, used, color=["#d62728" if v > 85 else "#ff7f0e" if v > 70 else "#2ca02c" for v in used])
    ax.axhline(85, color="red", ls="--", lw=1, alpha=0.6)
    ax.set_ylabel("Uso (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Uso de disco por ponto de montagem")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    for b, v in zip(bars, used):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(saida, format="svg", bbox_inches="tight")
    print(f"  SVG salvo em: {saida}")


def cmd_disk(args):
    print("=== USO POR PONTO DE MONTAGEM ===")
    seen = set()
    for dev, mnt, fstype in real_mounts():
        if mnt in seen:
            continue
        seen.add(mnt)
        try:
            u = shutil.disk_usage(mnt)
        except OSError:
            continue
        pct = 100 * u.used / u.total if u.total else 0
        flag = " <-- ATENCAO" if pct >= 85 else ""
        print(f"  {mnt:<28} {fstype:<8} {human(u.used):>10} / {human(u.total):>10}  {pct:4.0f}%{flag}")

    if args.svg:
        _disk_svg(args.svg)

    if args.path:
        p = args.path
        print(f"\n=== MAIORES ITENS EM {os.path.abspath(p)} ===")
        if not os.path.isdir(p):
            print("  (caminho invalido)")
            return
        t0 = time.time()
        total, children, largest = _scan_dir(p, args.top)
        print(f"  Total: {human(total)}")
        print(f"  Maiores subdiretorios/arquivos:")
        for name, sz in sorted(children.items(), key=lambda kv: kv[1], reverse=True)[:args.top]:
            print(f"    {human(sz):>10}  {name}")
        print(f"  Maiores arquivos:")
        for sz, fp in largest:
            print(f"    {human(sz):>10}  {fp}")
        print(f"  (varredura em {time.time() - t0:.1f}s)")


# ----------------------------------------------------------------- ports
def _inode_pid_map():
    m = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fdir = f"/proc/{pid}/fd"
        try:
            for fd in os.listdir(fdir):
                try:
                    link = os.readlink(f"{fdir}/{fd}")
                except OSError:
                    continue
                if link.startswith("socket:["):
                    m.setdefault(link[8:-1], pid)
        except OSError:
            continue
    return m


def _hex_ip(a):
    try:
        if len(a) == 8:
            return socket.inet_ntoa(struct.pack("<I", int(a, 16)))
        if len(a) == 32:
            words = [int(a[i:i + 8], 16) for i in range(0, 32, 8)]
            return socket.inet_ntop(socket.AF_INET6, b"".join(struct.pack("<I", w) for w in words))
    except (ValueError, OSError):
        pass
    return a


def _listen_ports():
    ino_pid = _inode_pid_map()
    rows = []
    for f, proto, v6 in (("/proc/net/tcp", "tcp", False), ("/proc/net/tcp6", "tcp6", True),
                         ("/proc/net/udp", "udp", False), ("/proc/net/udp6", "udp6", True)):
        try:
            with open(f) as fh:
                next(fh, None)
                for line in fh:
                    p = line.split()
                    if len(p) < 10:
                        continue
                    local, st = p[1], p[3]
                    inode = p[9]
                    if proto.startswith("tcp") and st != "0A":  # 0A = LISTEN
                        continue
                    addr, port = local.rsplit(":", 1)
                    pid = ino_pid.get(inode, "-")
                    name = "-"
                    if pid != "-":
                        try:
                            name = open(f"/proc/{pid}/comm").read().strip()
                        except OSError:
                            name = "?"
                    rows.append((proto, _hex_ip(addr), int(port, 16), str(pid), name))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: r[2])
    return rows


def cmd_ports(args):
    rows = _listen_ports()
    print("=== PORTAS EM ESCUTA ===")
    if not rows:
        print("  (nenhuma; ou sem permissao para ler os sockets)")
        return
    print(f"  {'PROTO':<5} {'ENDEREÇO':<42} {'PORTA':>6}  {'PID':>6}  PROCESSO")
    for proto, ip, port, pid, name in rows:
        print(f"  {proto:<5} {ip:<42} {port:>6}  {pid:>6}  {name}")
    if all(r[3] == "-" for r in rows):
        print("\n  Dica: rode com sudo para ver o dono dos sockets.")


# ----------------------------------------------------------------- conns
NETIDS = ("tcp", "udp", "tcp6", "udp6", "u_str", "netlink", "vsock", "sock")
SS_STATES = {
    "LISTEN", "UNCONN", "ESTAB", "SYN-SENT", "SYN-RECV", "FIN-WAIT-1",
    "FIN-WAIT-2", "TIME-WAIT", "CLOSE-WAIT", "CLOSING", "LAST-ACK", "CLOSED",
}


def _ss_rows(out):
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        t = line.split()
        if t and t[0] in NETIDS:
            t.pop(0)
        if len(t) < 5 or t[0] not in SS_STATES:
            continue
        m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        rows.append({
            "proto": "tcp" if t[3].count(":") == 1 else "?",
            "state": t[0], "local": t[3], "peer": t[4],
            "proc": f"{m.group(1)}({m.group(2)})" if m else "",
        })
    return rows


def _ss_bytes(out):
    """Le bytes_sent/bytes_received de 'ss -tie' (info pode vir na linha seguinte)."""
    blocks, cur = [], None
    for line in out.splitlines():
        if line and not line[0].isspace():
            if cur is not None:
                blocks.append(cur)
            cur = line
        elif cur is not None:
            cur += " " + line.strip()
    if cur is not None:
        blocks.append(cur)
    res = {}
    for b in blocks:
        t = b.split()
        if t and t[0] in NETIDS:
            t = t[1:]
        if len(t) < 5 or t[0] not in SS_STATES:
            continue
        ms = re.search(r"bytes_sent:(\d+)", b)
        mr = re.search(r"bytes_received:(\d+)", b)
        res[(t[3], t[4])] = (int(ms.group(1)) if ms else 0,
                             int(mr.group(1)) if mr else 0)
    return res


def _peer_host(addr):
    host = addr.rsplit(":", 1)[0]
    return host.strip("[]")


def cmd_conns(args):
    ss = shutil.which("ss")
    if not ss:
        print("ss nao encontrado (instale o pacote iproute2).")
        return
    n = args.top
    out = run([ss, "-H", "-t", "-u", "-a", "-n", "-p"])
    if not out.strip():                       # ss antigo sem -H
        out = run([ss, "-t", "-u", "-a", "-n", "-p"])
    rows = _ss_rows(out)
    bmap = _ss_bytes(run([ss, "-H", "-t", "-i", "-e", "-n"])
                     or run([ss, "-t", "-i", "-e", "-n"]))

    # 1) resumo por estado
    print("=== CONEXOES: RESUMO POR ESTADO ===")
    cont = {}
    for r in rows:
        cont[r["state"]] = cont.get(r["state"], 0) + 1
    for st, c in sorted(cont.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {st:<12} {c:>5}")

    # 2) conexoes ativas
    active = [r for r in rows if r["state"] not in ("LISTEN", "UNCONN")]
    if args.estado:
        active = [r for r in active if r["state"] == args.estado.upper()]

    def total(r):
        s, rc = bmap.get((r["local"], r["peer"]), (0, 0))
        return s + rc

    active.sort(key=lambda r: total(r), reverse=True)
    titulo = f"USO POR ESTADO {args.estado.upper()}" if args.estado else "ATIVAS (por trafego)"
    print(f"\n=== TOP {n} CONEXOES {titulo} ===")
    print(f"  {'ENVIADO':>9} {'RECEBIDO':>9}  {'ESTADO':<10} {'LOCAL':<24} {'PEER':<34} PROCESSO")
    for r in active[:n]:
        s, rc = bmap.get((r["local"], r["peer"]), (0, 0))
        print(f"  {human(s):>9} {human(rc):>9}  {r['state']:<10} "
              f"{r['local'][:24]:<24} {r['peer'][:34]:<34} {r['proc'][:20]}")

    # 3) top peers remotos
    peers = {}
    for r in active:
        p = _peer_host(r["peer"])
        if p in ("0.0.0.0", "*", "::"):
            continue
        peers[p] = peers.get(p, 0) + 1
    print(f"\n=== TOP {n} PEERS REMOTOS (por nº de conexoes) ===")
    if not peers:
        print("  (nenhum)")
    for p, c in sorted(peers.items(), key=lambda kv: kv[1], reverse=True)[:n]:
        print(f"  {c:>4}x  {p}")

    if args.listen:
        print(f"\n=== PORTAS EM ESCUTA ===")
        for r in rows:
            if r["state"] in ("LISTEN", "UNCONN"):
                print(f"  {r['proto']:<4} {r['local']:<40} {r['proc']}")


# ----------------------------------------------------------------- certs
def _check_cert(host, port, timeout=5):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ss:
            return ss.getpeercert()


def _cn(name_tuple):
    for rdn in name_tuple or ():
        for k, v in rdn:
            if k in ("commonName",):
                return v
    return "?"


def cmd_certs(args):
    print("=== VALIDADE DE CERTIFICADOS TLS ===")
    now = datetime.now(timezone.utc)
    for item in args.alvos:
        host, _, p = item.partition(":")
        port = int(p) if p else 443
        try:
            cert = _check_cert(host, port)
        except Exception as e:
            print(f"  {item:<40} ERRO: {e}")
            continue
        exp = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        dias = (exp - now).days
        status = "OK" if dias > 30 else "WARN" if dias > 7 else "CRIT"
        print(f"  {item:<40} CN={_cn(cert.get('subject')):<28} "
              f"expira em {dias:>4}d ({exp:%Y-%m-%d})  {status}")


# ----------------------------------------------------------------- logs
def cmd_logs(args):
    n = args.n
    print("=== ERROS RECENTES (kernel/boot) ===")
    j = shutil.which("journalctl")
    if j:
        err = run([j, "-b", "-p", "err", "--no-pager", "-o", "cat", "-n", str(n * 20)])
        lines = [l for l in err.splitlines() if l.strip()]
        print(f"  total de linhas de erro neste boot: {len(lines)}")
        print(f"  ultimas {min(n, len(lines))}:")
        for l in lines[-n:]:
            print(f"    {l[:150]}")
    else:
        tail = run(["tail", "-n", str(n * 20), "/var/log/syslog"])

    print("\n=== LOGINS FALHOS ===")
    if j:
        fails = run([j, "-b", "--no-pager", "-o", "cat", "-g", "Failed password"])
        ipre = re.compile(r"from\s+(\S+)")
        ips = {}
        cnt = 0
        for l in fails.splitlines():
            if "Failed password" in l:
                cnt += 1
                m = ipre.search(l)
                if m:
                    ips[m.group(1)] = ips.get(m.group(1), 0) + 1
        print(f"  total: {cnt}")
        for ip, c in sorted(ips.items(), key=lambda kv: kv[1], reverse=True)[:n]:
            print(f"    {c:>5}x  {ip}")
    else:
        print("  (journalctl indisponivel)")

    print("\n=== OOM / KILL DO KERNEL ===")
    if j:
        oom = run([j, "-k", "-b", "--no-pager", "-o", "cat", "-g", "Out of memory|Killed process"])
        lines = [l for l in oom.splitlines() if l.strip()]
        print(f"  ocorrencias: {len(lines)}")
        for l in lines[-n:]:
            print(f"    {l[:150]}")
    else:
        print("  (journalctl indisponivel)")


# ----------------------------------------------------------------- health
def _line(status, msg):
    s = {"OK": "[ OK ]", "WARN": "[WARN]", "CRIT": "[CRIT]"}[status]
    print(f"  {s} {msg}")
    return status


def cmd_health(args):
    print("=" * 60)
    print("DIAGNOSTICO AGREGADO")
    print("=" * 60)
    worst = "OK"
    def bump(s):
        nonlocal worst
        order = {"OK": 0, "WARN": 1, "CRIT": 2}
        if order[s] > order[worst]:
            worst = s

    # Load
    try:
        l1, l5, l15 = os.getloadavg()
        ncpu = os.cpu_count() or 1
        ratio = l1 / ncpu
        s = "OK" if ratio < 0.7 else "WARN" if ratio < 1.0 else "CRIT"
        bump(s)
        _line(s, f"Load 1min {l1:.2f} em {ncpu} CPUs (uso {ratio * 100:.0f}%)")
    except OSError:
        pass

    # Memoria
    mi = read_kv("/proc/meminfo")
    def kb(k):
        try:
            return int(mi.get(k, "0 kB").split()[0])
        except Exception:
            return 0
    total, avail = kb("MemTotal"), kb("MemAvailable")
    if total:
        pct = 100 * avail / total
        s = "OK" if pct > 20 else "WARN" if pct > 10 else "CRIT"
        bump(s)
        _line(s, f"RAM disponivel {human(avail * 1024)} de {human(total * 1024)} ({pct:.0f}% livre)")

    # Swap
    st, sf = kb("SwapTotal"), kb("SwapFree")
    if st:
        pct = 100 * (st - sf) / st
        s = "OK" if pct < 25 else "WARN" if pct < 60 else "CRIT"
        bump(s)
        _line(s, f"Swap em uso {pct:.0f}%")

    # Discos
    seen = set()
    for dev, mnt, _ in real_mounts():
        if mnt in seen:
            continue
        seen.add(mnt)
        try:
            u = shutil.disk_usage(mnt)
        except OSError:
            continue
        pct = 100 * u.used / u.total if u.total else 0
        s = "OK" if pct < 80 else "WARN" if pct < 90 else "CRIT"
        bump(s)
        _line(s, f"Disco {mnt} em {pct:.0f}% ({human(u.free)} livres)")

    # Unidades systemd falhas
    sc = shutil.which("systemctl")
    if sc:
        out = run([sc, "--failed", "--no-legend", "--no-pager"])
        filded = [l.strip() for l in out.splitlines() if l.strip()]
        s = "OK" if not filded else "WARN"
        bump(s)
        _line(s, f"Unidades systemd falhas: {len(filded)}")
        for l in filded[:10]:
            print(f"          {l[:120]}")

    # Zombies
    zombies = [p for p in os.listdir("/proc") if p.isdigit()]
    zc = 0
    for pid in zombies:
        try:
            st = open(f"/proc/{pid}/stat").read()
            r = st.rfind(")")
            if st[r + 2] == "Z":
                zc += 1
        except OSError:
            continue
    s = "OK" if zc < 5 else "WARN"
    bump(s)
    _line(s, f"Processos zombie: {zc}")

    print("-" * 60)
    print(f"  RESULTADO GERAL: {worst}")
    return 0


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Utilitarios READ-ONLY para sysadmin.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="inventario do sistema").set_defaults(func=cmd_info)

    p = sub.add_parser("top", help="top processos")
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(func=cmd_top)

    p = sub.add_parser("disk", help="uso de disco")
    p.add_argument("path", nargs="?", default=None, help="diretorio para detalhar")
    p.add_argument("-n", "--top", type=int, default=10)
    p.add_argument("--svg", metavar="ARQ", help="gera grafico SVG do uso por montagem")
    p.set_defaults(func=cmd_disk)

    sub.add_parser("ports", help="portas em escuta").set_defaults(func=cmd_ports)

    p = sub.add_parser("conns", help="conexoes ativas via ss")
    p.add_argument("-n", "--top", type=int, default=10)
    p.add_argument("--estado", help="filtra por estado (ex.: ESTAB, TIME-WAIT)")
    p.add_argument("--listen", action="store_true", help="inclui portas em escuta")
    p.set_defaults(func=cmd_conns)

    p = sub.add_parser("certs", help="validade de certificados TLS")
    p.add_argument("alvos", nargs="+", help="host[:porta] (padrao 443)")
    p.set_defaults(func=cmd_certs)

    p = sub.add_parser("logs", help="erros e logins falhos")
    p.add_argument("-n", type=int, default=15)
    p.set_defaults(func=cmd_logs)

    sub.add_parser("health", help="diagnostico agregado").set_defaults(func=cmd_health)

    args = ap.parse_args()
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
