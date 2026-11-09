#!/usr/bin/env python3
"""Minimal structural-thermal participant for the FDS-preCICE adapter tests.

Each vertex of a regular grid on the plate surface carries an independent 1-D
transient conduction model through the plate thickness (front: heat flux from
FDS, back: insulated). Implicit (backward Euler) finite differences, one solve
per preCICE time window. Same physics as an FDS thermally-thick SURF with
BACKING='INSULATED', so the coupled run can be checked against FDS alone.
"""
import argparse
import numpy as np
import precice

p = argparse.ArgumentParser()
p.add_argument("--config", default="../precice-config.xml")
p.add_argument("--thickness", type=float, default=0.01)      # m
p.add_argument("--k", type=float, default=45.8)               # W/m/K
p.add_argument("--rho", type=float, default=7850.0)           # kg/m3
p.add_argument("--cp", type=float, default=460.0)             # J/kg/K
p.add_argument("--nodes", type=int, default=21)
p.add_argument("--t0", type=float, default=293.15)            # K
p.add_argument("--spacing", type=float, default=0.05)         # m, surface grid
args = p.parse_args()

# Surface grid on the ceiling plate x,y in [0.5,1.5], z = 2.0
s = args.spacing
xc = np.arange(0.5 + s / 2, 1.5, s)
X, Y = np.meshgrid(xc, xc, indexing="ij")
coords = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, 2.0)])
nv = coords.shape[0]

participant = precice.Participant("Solid", args.config, 0, 1)
ids = participant.set_mesh_vertices("Solid-Mesh", coords)

# 1-D grid through the thickness, node 0 = exposed face
n = args.nodes
dx = args.thickness / (n - 1)
alpha = args.k / (args.rho * args.cp)
T = np.full((nv, n), args.t0)

if participant.requires_initial_data():
    participant.write_data("Solid-Mesh", "Temperature", ids, T[:, 0])
participant.initialize()

# Control-volume widths (half cells at both faces)
vol = np.full(n, dx)
vol[0] = vol[-1] = dx / 2


def step(T, q, dt):
    """Backward Euler on all vertices at once (tridiagonal, Thomas algorithm)."""
    r = alpha * dt / dx
    a = np.zeros(n); b = np.zeros(n); c = np.zeros(n)
    b[:] = vol + 2 * r
    a[1:] = -r
    c[:-1] = -r
    b[0] = vol[0] + r
    b[-1] = vol[-1] + r
    d = T * vol[None, :]
    d[:, 0] += q * dt / (args.rho * args.cp)
    # Thomas, vectorised over vertices
    cp = np.zeros(n); dp = np.zeros_like(d)
    cp[0] = c[0] / b[0]; dp[:, 0] = d[:, 0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[:, i] = (d[:, i] - a[i] * dp[:, i - 1]) / m
    x = np.zeros_like(d)
    x[:, -1] = dp[:, -1]
    for i in range(n - 2, -1, -1):
        x[:, i] = dp[:, i] - cp[i] * x[:, i + 1]
    return x


t = 0.0
log = open("solid_log.csv", "w")
log.write("t,T_front_center_K,T_front_mean_K,q_center_Wm2,q_mean_Wm2\n")
ic = np.argmin(np.sum((coords[:, :2] - [1.0, 1.0]) ** 2, axis=1))
while participant.is_coupling_ongoing():
    dt = participant.get_max_time_step_size()
    q = participant.read_data("Solid-Mesh", "Heat-Flux", ids, dt)
    T = step(T, q, dt)
    participant.write_data("Solid-Mesh", "Temperature", ids, T[:, 0])
    participant.advance(dt)
    t += dt
    log.write(f"{t:.4f},{T[ic,0]:.4f},{T[:,0].mean():.4f},{q[ic]:.2f},{q.mean():.2f}\n")
log.close()
participant.finalize()
