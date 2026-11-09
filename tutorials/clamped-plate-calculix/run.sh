#!/usr/bin/env bash
# FDS (fire) + CalculiX (coupled temperature-displacement) through preCICE.
# FDS_PRECICE: coupled FDS binary (build.sh); CalculiX adapter: ccx_preCICE in PATH.
set -euo pipefail
cd "$(dirname "$0")"
FDS_PRECICE="${FDS_PRECICE:-../../bin/fds_precice}"
NP="${NP:-2}"
rm -rf precice-run
(cd solid && [ -f plate.msh ] || python3 make_mesh.py)
(cd fluid && OMP_NUM_THREADS=1 mpirun -np "$NP" "$FDS_PRECICE" plate_fire.fds > fds.log 2>&1) &
(cd solid && OMP_NUM_THREADS=1 ccx_preCICE -i plate -precice-participant Solid > ccx.log 2>&1) &
wait
echo "Done: fluid/plate_fire_devc.csv, solid/plate.dat, solid/plate.frd"
