#!/usr/bin/env python3
"""Structured C3D20R mesh of a steel plate for the FDS-CalculiX tutorial.

Plate: x in [X0, X1], y in [Y0, Y1], z in [Z0, Z0+H]. The face z = Z0 is exposed to
the fire (FDS ceiling). Writes:
  plate.msh   nodes + elements (Eall)
  plate.nam   node sets: Nfix (both clamped ends), Ninterface (exposed face), Nmid (mid-span line)
  plate.sur   element surface Sinterface (exposed faces, face S1)
"""
import numpy as np

X0, X1, Y0, Y1, Z0, H = 0.2, 1.8, 0.8, 1.2, 2.0, 0.005
NX, NY, NZ = 32, 8, 2

# Quadratic grid: node indices on a (2NX+1)(2NY+1)(2NZ+1) lattice, skipping unused
# lattice points (face/volume centres) that C3D20 does not have.
xs = np.linspace(X0, X1, 2 * NX + 1)
ys = np.linspace(Y0, Y1, 2 * NY + 1)
zs = np.linspace(Z0, Z0 + H, 2 * NZ + 1)

def used(i, j, k):
    odd = (i % 2) + (j % 2) + (k % 2)
    return odd <= 1

nid = {}
lines = ["*NODE, NSET=Nall"]
n = 0
for k in range(2 * NZ + 1):
    for j in range(2 * NY + 1):
        for i in range(2 * NX + 1):
            if used(i, j, k):
                n += 1
                nid[(i, j, k)] = n
                lines.append(f"{n}, {xs[i]:.8f}, {ys[j]:.8f}, {zs[k]:.8f}")

lines.append("*ELEMENT, TYPE=C3D20R, ELSET=Eall")
e = 0
bottom = []
for k in range(NZ):
    for j in range(NY):
        for i in range(NX):
            I, J, K = 2 * i, 2 * j, 2 * k
            c = [(I, J, K), (I + 2, J, K), (I + 2, J + 2, K), (I, J + 2, K),
                 (I, J, K + 2), (I + 2, J, K + 2), (I + 2, J + 2, K + 2), (I, J + 2, K + 2)]
            m = [(I + 1, J, K), (I + 2, J + 1, K), (I + 1, J + 2, K), (I, J + 1, K),
                 (I + 1, J, K + 2), (I + 2, J + 1, K + 2), (I + 1, J + 2, K + 2), (I, J + 1, K + 2),
                 (I, J, K + 1), (I + 2, J, K + 1), (I + 2, J + 2, K + 1), (I, J + 2, K + 1)]
            ids = [nid[p] for p in c + m]
            e += 1
            if k == 0:
                bottom.append(e)
            # 20 nodes: CalculiX allows max 16 entries per line, continue on next line
            lines.append(f"{e}, " + ", ".join(map(str, ids[:15])) + ",")
            lines.append(", ".join(map(str, ids[15:])))
open("plate.msh", "w").write("\n".join(lines) + "\n")

def nset(name, keys):
    ids = sorted(nid[p] for p in keys)
    out = [f"*NSET, NSET={name}"]
    for a in range(0, len(ids), 10):
        out.append(", ".join(map(str, ids[a:a + 10])) + ",")
    return out

keys = list(nid)
nam = []
nam += nset("Nfix", [p for p in keys if p[0] in (0, 2 * NX)])
nam += nset("Ninterface", [p for p in keys if p[2] == 0])
nam += nset("Nmid", [p for p in keys if p[0] == NX and p[1] == NY])          # mid-span, centre line
nam += nset("Nquarter", [p for p in keys if p[0] == NX // 2 and p[1] == NY])  # quarter span
open("plate.nam", "w").write("\n".join(nam) + "\n")

sur = ["*SURFACE, NAME=Sinterface, TYPE=ELEMENT"] + [f"{el}, S1" for el in bottom]
open("plate.sur", "w").write("\n".join(sur) + "\n")

print(f"{n} nodes, {e} C3D20R elements, {len(bottom)} interface faces")
