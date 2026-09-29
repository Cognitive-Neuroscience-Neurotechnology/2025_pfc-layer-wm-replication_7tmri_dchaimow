#!/bin/bash
# Helper script for building the container on nyx
shopt -s extglob

export APPTAINER_TMPDIR=~/ptmp/tmp
export APPTAINER_CACHEDIR=~/ptmp/tmp
export APPTAINER_BINDPATH=

deffile=${1}
container_fname=${2-$(basename $deffile .def)}.sif

# Build the container
apptainer build --fakeroot $container_fname $deffile

# Name the container with the git sha and build date
md5=$(md5sum $container_fname | cut -d' ' -f1)
build_date=$(date -u +"%Y%m%dT%H%M%SZ")
mv ${container_fname} ${container_fname%.sif}_${build_date}_md5${md5}.sif
