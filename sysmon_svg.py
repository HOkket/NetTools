#!/usr/bin/env python3
"""Coleta uso de recursos do Linux e exporta um gráfico SVG.

Uso:
    ./sysmon_svg.py                      # 30s, coleta a cada 1s -> sysmon.svg
    ./sysmon_svg.py -d 60 -i 2 -o cpu.svg
"""
import argparse
import time

import matplotlib

matplotlib.use("Agg")  # sem precisar de display/X11
import matplotlib.pyplot as plt
import psutil


def coletar(intervalo, duracao):
    psutil.cpu_percent(interval=None)  # primeira leitura serve de baseline
    t, cpu, mem, swp, dr, dw, nr, nw = [], [], [], [], [], [], [], []
    inicio = time.time()

    while time.time() - inicio < duracao:
        time.sleep(intervalo)
        cpu.append(psutil.cpu_percent(interval=None))
        mem.append(psutil.virtual_memory().percent)
        swp.append(psutil.swap_memory().percent)

        d1 = psutil.disk_io_counters()
        n1 = psutil.net_io_counters()
        time.sleep(intervalo)

        d2, n2 = psutil.disk_io_counters(), psutil.net_io_counters()
        dt = time.time() - inicio
        t.append(dt)
        dr.append((d2.read_bytes - d1.read_bytes) / intervalo / 1e6)   # MB/s
        dw.append((d2.write_bytes - d1.write_bytes) / intervalo / 1e6)
        nr.append((n2.bytes_recv - n1.bytes_recv) / intervalo / 1e6)
        nw.append((n2.bytes_sent - n1.bytes_sent) / intervalo / 1e6)

    return t, cpu, mem, swp, dr, dw, nr, nw


def grafico(t, cpu, mem, swp, dr, dw, nr, nw, saida):
    fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    fig.suptitle("Uso de recursos do sistema", fontsize=14, weight="bold")

    ax[0].plot(t, cpu, color="#d62728", label="CPU %")
    ax[0].plot(t, mem, color="#1f77b4", label="RAM %")
    ax[0].plot(t, swp, color="#9467bd", label="Swap %", alpha=0.7)
    ax[0].set_ylabel("Percentual (%)")
    ax[0].set_ylim(0, 100)
    ax[0].legend(loc="upper right", ncol=3, fontsize=9)
    ax[0].grid(alpha=0.3)

    ax[1].plot(t, dr, color="#2ca02c", label="Disco leitura")
    ax[1].plot(t, dw, color="#ff7f0e", label="Disco escrita")
    ax[1].set_ylabel("MB/s")
    ax[1].legend(loc="upper right", fontsize=9)
    ax[1].grid(alpha=0.3)

    ax[2].plot(t, nr, color="#17becf", label="Rede RX")
    ax[2].plot(t, nw, color="#e377c2", label="Rede TX")
    ax[2].set_ylabel("MB/s")
    ax[2].set_xlabel("Tempo (s)")
    ax[2].legend(loc="upper right", fontsize=9)
    ax[2].grid(alpha=0.3)

    for a in ax:
        a.margins(x=0)
    fig.tight_layout()
    fig.savefig(saida, format="svg", bbox_inches="tight")
    print(f"SVG salvo em: {saida}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--intervalo", type=float, default=1.0, help="segundos entre amostras")
    p.add_argument("-d", "--duracao", type=float, default=30.0, help="duração total em segundos")
    p.add_argument("-o", "--saida", default="sysmon.svg", help="arquivo SVG de saída")
    a = p.parse_args()

    print(f"Coletando por {a.duracao:.0f}s (intervalo {a.intervalo}s)...")
    grafico(*coletar(a.intervalo, a.duracao), a.saida)
