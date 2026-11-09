#!/usr/bin/env bash
# Coupled run: FDS (2 MPI processes) + Python 1-D steel plate, then the FDS-only reference.
# FDS_PRECICE: path to the coupled FDS binary; FDS: path to a standard FDS 6.11.1 binary (optional).
set -euo pipefail
cd "$(dirname "$0")"
FDS_PRECICE="${FDS_PRECICE:-../../bin/fds_precice}"
NP="${NP:-2}"
export OMP_NUM_THREADS=1
rm -rf precice-run

(cd fluid && mpirun -np "$NP" "$FDS_PRECICE" plate_precice.fds > fds.log 2>&1) &
(cd solid && python3 -u solid_1d.py > solid.log 2>&1) &
wait
echo "Coupled run done: fluid/plate_precice_devc.csv, solid/solid_log.csv"

if [ -n "${FDS:-}" ]; then
  (cd reference && mpirun -np "$NP" "$FDS" plate_ref.fds > fds.log 2>&1)
  echo "Reference done: reference/plate_ref_devc.csv"
fi
