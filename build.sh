#!/usr/bin/env bash
# Build FDS 6.11.1 with the preCICE adapter (GNU + OpenMPI, Linux).
# Requirements: gfortran, OpenMPI (mpifort), git, libprecice 3.x (with pkg-config file).
# Usage: ./build.sh [install_dir]     -> produces <install_dir>/fds_precice
set -euo pipefail

FDS_TAG=FDS-6.11.1
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/build}"
PREFIX="${1:-$HERE/bin}"
JOBS="${JOBS:-$(nproc)}"

pkg-config --exists libprecice || { echo "libprecice not found by pkg-config"; exit 1; }
echo "preCICE $(pkg-config --modversion libprecice)"

mkdir -p "$WORK" "$PREFIX"
if [ ! -d "$WORK/fds" ]; then
  git clone --quiet --depth 1 --branch "$FDS_TAG" https://github.com/firemodels/fds.git "$WORK/fds"
  git -C "$WORK/fds" apply "$HERE/patches/fds-6.11.1.patch"
  cp "$HERE/src/prci.f90" "$WORK/fds/Source/"
fi

mkdir -p "$WORK/fds/Build/ompi_gnu_linux_precice"
cd "$WORK/fds/Build/ompi_gnu_linux_precice"
# HYPRE/SUNDIALS are optional in FDS; set FFLAGS_HYPRE/LFLAGS_HYPRE etc. to use them
make -j"$JOBS" VPATH="../../Source" -f ../makefile ompi_gnu_linux_precice COMP_FC=mpifort \
     FFLAGS_HYPRE="${FFLAGS_HYPRE:-}" LFLAGS_HYPRE="${LFLAGS_HYPRE:-}" \
     FFLAGS_SUNDIALS="${FFLAGS_SUNDIALS:-}" LFLAGS_SUNDIALS="${LFLAGS_SUNDIALS:-}" > build.log 2>&1 \
  || { tail -30 build.log; exit 1; }

cp fds_ompi_gnu_linux_precice "$PREFIX/fds_precice"
echo "Built $PREFIX/fds_precice"
