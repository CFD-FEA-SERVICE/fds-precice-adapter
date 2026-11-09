# FDS + CalculiX: clamped steel plate heated by a fire

Thermo-fluid-structure coupling. FDS computes the fire. CalculiX (`ccx_preCICE`, preCICE CalculiX adapter 2.20) runs a transient coupled temperature–displacement analysis: heat flux from FDS → conduction in the steel → thermal expansion → restraint stresses. CalculiX returns the surface temperature to FDS.

- **Plate:** 1600 × 400 × 5 mm steel, both short ends clamped (all displacements fixed), exposed underside forming the ceiling of a 2 × 2 × 2 m box. 512 C3D20R elements (`solid/make_mesh.py`).
- **Fire:** 300 kW propane burner, FDS on 2 meshes (8000 cells, 0.1 m), 2 MPI processes, 180 s.
- **Coupling:**
  - FDS writes `Heat-Flux` on its WALL cells; CalculiX reads it on face centres (`*DFLUX`).
  - CalculiX writes `Temperature` on the surface nodes; FDS reads it.
  - Serial-explicit, 0.5 s window, nearest-neighbour mapping.
- **Material:** elastic steel, E = 210 GPa, ν = 0.3, α = 1.2e-5 1/K. No plasticity and no temperature-dependent properties (yet).

## Run
```bash
FDS_PRECICE=../../bin/fds_precice ./run.sh     # needs ccx_preCICE (calculix-precice3 package) in PATH
python3 post.py                                # history.png, contours.png, midspan_history.csv
```

## Check (t = 180 s)
With both ends fixed, the axial force is the same in every section. It is set by the mean temperature rise over the whole plate: σ = −E·α·mean(ΔT).

| | Value |
|---|---|
| Mean ΔT over the plate | 67.9 K |
| −E·α·mean(ΔT) | −171.0 MPa |
| CalculiX section-mean σxx at mid-span | −173.3 MPa (+1.3 %) |
| Mid-span exposed face temperature | 137 °C (front–back difference 0.4 K) |
| Peak compressive σxx (clamped corners) | −421 MPa |

The mid-span stress is lower than the local −E·α·ΔT(mid) (−294 MPa). The cooler ends allow the hot central part to expand into them. The peak at the clamped corners exceeds the yield strength of common structural steels, so for a real assessment the next step is a temperature-dependent elastic–plastic material (EN 1993-1-2).
