#!/usr/bin/env python3
"""Post-processing of the FDS-CalculiX clamped plate tutorial.

- time histories at mid-span from solid/plate.dat (temperature, deflection, stress)
- check: mid-span axial stress vs. restrained-bar estimate  sigma = -E*alpha*(T_mean - T0)
- contour of axial stress and temperature on the exposed face at the last frd output
"""
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E, ALPHA, NU, T0 = 210e9, 1.2e-5, 0.3, 293.15

# ---------------------------------------------------------------- plate.dat
blocks = re.split(r"\n\s*(temperatures|displacements|stresses) .*?time\s+([0-9.E+-]+)\s*\n", open("solid/plate.dat").read())
rows = {}
for i in range(1, len(blocks) - 1, 3):
    kind, t, body = blocks[i], float(blocks[i + 1]), blocks[i + 2]
    vals = [list(map(float, l.split())) for l in body.strip().splitlines() if l.strip() and l.split()[0].isdigit()]
    r = rows.setdefault(t, {})
    if kind == "temperatures":
        a = np.array(vals)
        r["T_front"] = a[0, 1] - 273.15      # Nmid sorted by node id: bottom (exposed) first
        r["T_back"] = a[-1, 1] - 273.15
        r["T_mean"] = a[:, 1].mean() - 273.15
    elif kind == "displacements":
        a = np.array(vals)
        r["w_mid_mm"] = a[:, 3].mean() * 1e3
    elif kind == "stresses":
        a = np.array(vals)
        r["sxx_mean_MPa"] = a[:, 2].mean() / 1e6
        r["sxx_min_MPa"] = a[:, 2].min() / 1e6
        r["sxx_max_MPa"] = a[:, 2].max() / 1e6
        r["syy_mean_MPa"] = a[:, 3].mean() / 1e6
df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
df.index.name = "t"
df["sxx_bar_MPa"] = -E * ALPHA * df["T_mean"].sub(T0 - 273.15) / 1e6
df.to_csv("midspan_history.csv")

fds = pd.read_csv("fluid/plate_fire_devc.csv", skiprows=1)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
ax[0].plot(fds["Time"], fds["TG_MID"], color="C3", alpha=.5, lw=1, label="Gas 5 cm below plate (FDS)")
ax[0].plot(fds["Time"], fds["TS_MID"], color="C0", lw=2, label="Plate surface seen by FDS")
ax[0].plot(df.index, df["T_front"], "k--", lw=1.5, label="Exposed face (CalculiX)")
ax[0].plot(df.index, df["T_back"], ":", color="gray", lw=1.5, label="Unexposed face (CalculiX)")
ax[0].set(xlabel="Time (s)", ylabel="Temperature (°C)", title="Mid-span temperature"); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)

ax[1].plot(df.index, df["sxx_mean_MPa"], lw=2, label="σxx CalculiX (mean of mid-span points)")
ax[1].fill_between(df.index, df["sxx_min_MPa"], df["sxx_max_MPa"], alpha=.2, label="σxx range over thickness/width")
ax[1].plot(df.index, df["sxx_bar_MPa"], "k--", lw=1.5, label="−E·α·ΔT at mid-span (local bound)")
ax[1].set(xlabel="Time (s)", ylabel="Stress (MPa)", title="Mid-span axial stress"); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8)

ax[2].plot(df.index, df["w_mid_mm"], lw=2, color="C2")
ax[2].set(xlabel="Time (s)", ylabel="Vertical displacement (mm)", title="Mid-span deflection"); ax[2].grid(alpha=.3)
fig.suptitle("FDS 6.11.1 + CalculiX 2.20 via preCICE 3.3.1 — 5 mm steel plate clamped at both ends, 300 kW fire")
fig.tight_layout(); fig.savefig("history.png", dpi=130)

# ---------------------------------------------------------------- last frd block: nodal NT and S on exposed face
def last_block(path, name):
    """Return {node: values} of the last result block called name (fixed-width frd ASCII)."""
    out, cur, inside = None, None, False
    with open(path) as f:
        for line in f:
            if line.startswith(" -4") and line.split()[1] == name:
                cur, inside = {}, True
                continue
            if inside:
                if line.startswith(" -3"):
                    out, inside = cur, False
                elif line.startswith(" -1"):
                    nid = int(line[3:13])
                    v = [float(line[13 + 12 * k: 25 + 12 * k]) for k in range((len(line.rstrip()) - 13) // 12)]
                    cur[nid] = v
    return out

coords = {}
with open("solid/plate.frd") as f:
    inside = False
    for line in f:
        if line.startswith("    2C"):
            inside = True; continue
        if inside:
            if line.startswith(" -3"):
                break
            nid = int(line[3:13]); coords[nid] = [float(line[13 + 12 * k:25 + 12 * k]) for k in range(3)]
NT = last_block("solid/plate.frd", "NDTEMP")
S = last_block("solid/plate.frd", "STRESS")
face = [n for n, c in coords.items() if abs(c[2] - 2.0) < 1e-9 and n in S]
x = np.array([coords[n][0] for n in face]); y = np.array([coords[n][1] for n in face])
sxx = np.array([S[n][0] for n in face]) / 1e6
tt = np.array([NT[n][0] for n in face]) - 273.15

fig, ax = plt.subplots(2, 1, figsize=(10, 5.5))
for a, v, lab, cmap in [(ax[0], tt, "Temperature (°C)", "inferno"), (ax[1], sxx, "σxx (MPa)", "coolwarm")]:
    tc = a.tricontourf(x, y, v, 30, cmap=cmap)
    fig.colorbar(tc, ax=a, label=lab)
    a.set_aspect("equal"); a.set_xlabel("x (m)"); a.set_ylabel("y (m)")
ax[0].set_title(f"Exposed face at t = {df.index.max():.0f} s")
fig.tight_layout(); fig.savefig("contours.png", dpi=130)

last = df.iloc[-1]
print(f"t={df.index[-1]:.1f}s  T_front={last.T_front:.1f}°C T_back={last.T_back:.1f}°C  "
      f"sxx_mid={last.sxx_mean_MPa:.1f} MPa  bar={last.sxx_bar_MPa:.1f} MPa  "
      f"ratio={last.sxx_mean_MPa/last.sxx_bar_MPa:.3f}  w_mid={last.w_mid_mm:.2f} mm  "
      f"sxx face range {sxx.min():.0f}..{sxx.max():.0f} MPa")

# ---------------------------------------------------------------- global check: uniform axial force in a restrained bar
# With both ends fixed, the axial force is the same in every cross-section and is set by the
# MEAN temperature rise over the whole length: N/A = -E*alpha*mean(dT). Compare with the
# section-averaged sigma_xx at mid-span (all nodes of the section x = 1.0).
dT_all = np.mean([NT[n][0] for n in NT]) - T0
sec = [n for n, c in coords.items() if abs(c[0] - 1.0) < 1e-9 and n in S]
sxx_sec = np.mean([S[n][0] for n in sec]) / 1e6
print(f"mean dT over plate = {dT_all:.1f} K -> -E*alpha*mean(dT) = {-E*ALPHA*dT_all/1e6:.1f} MPa ; "
      f"section-mean sxx at mid-span = {sxx_sec:.1f} MPa ; ratio {sxx_sec/(-E*ALPHA*dT_all/1e6):.3f}")
