# Container for the analysis pipeline

`pfc-layer-wm-replication.def` defines an Apptainer container with only the software used by the pipeline
(steps 00–23), with all versions pinned. It replaces the general-purpose `gfae` containers, whose unpinned recipe
no longer produces a working ciftify: later `pip` installs (e.g. pydeface 2.1.0, which requires
nibabel ≥ 5.3) upgrade nibabel beyond the 3.2.2 required by ciftify 2.3.3.

## Software versions

Steps 00–02 (anatomy) use the versions of the `gfae_20240902T132553Z` container, steps 03–23 those of the
`gfae_20260509T025235Z` container (with which the functional analyses were run); both containers have identical
versions of most packages.

| Software | Used in steps | Version | Source |
|---|---|---|---|
| Ubuntu | all | 22.04 | `ubuntu:jammy-20260410` (by digest), apt packages from the Ubuntu snapshot archive of 2026-05-09 |
| conda base environment (ciftify) | 00, 02 | python 3.11.9, nibabel 3.2.2, … | Miniforge 24.3.0-0, all packages pinned to the base environment of `gfae_20240902` (`base_env_*_pins.txt`) |
| ciftify | 00, 02 | 2.3.3 | PyPI |
| MSM (HCP) | 02 | v3.0FSL | `msm_ubuntu_v3` release binary (replaces FSL's `msm`) |
| FreeSurfer | 01, 02, 04, 11, 12 | 7.3.2 | release package |
| Connectome Workbench | 00, 02, 07–10, 20 | 2.0.0 | HCP release zip |
| FSL (incl. fsleyes 1.12.4) | 00, 03, 10–12 | 6.0.7.13 | `fslinstaller.py -V 6.0.7.13` |
| AFNI | 03, 06, 11 | 26.1.02 | built from the source tag (command line programs only) |
| ANTs | 04, 11, 12 | 2.5.3 | release zip |
| LAYNII | 03 | 2.7.0 | release zip |
| MATLAB Runtime, SPM12 with CAT12 | 01, 03 | R2017b (v93), CAT12.8.2 r2166 | MathWorks installer, CAT12 standalone release |
| GNU parallel, bc, tcsh, jq | 03, 06 | 20210822, 1.07.1, 6.21.00, 1.7.1 | apt snapshot, jq release binary |

Two components differ from what the respective `gfae` container used:
- Connectome Workbench is 2.0.0 for all steps (steps 07–10 and 20 were run with 2.1.0), and it is the HCP's own
  build instead of the NeuroDebian package.
- AFNI is compiled from source instead of AFNI's precompiled binaries of the same version.

The Python environment of the analysis steps is not part of the container, see `../environment.yml`.

## Building on nyx

Without root access, from this directory (the definition file includes the pin files from it):

```bash
./build.sh pfc-layer-wm-replication.def
```

`build.sh` runs `apptainer build --fakeroot` (with `APPTAINER_TMPDIR` and `APPTAINER_CACHEDIR` in `~/ptmp/tmp`, which
needs enough space for the build) and names the image `pfc-layer-wm-replication_<build time>_md5<checksum>.sif`.

The `%test` section of the definition file (run at the end of the build, or with `apptainer test`) checks the
versions of the main software and that all programs used by the pipeline are available.

## Files

- `pfc-layer-wm-replication.def`: the container definition
- `base_env_conda_pins.txt`, `base_env_pip_pins.txt`: pinned packages of the conda base environment, taken from
  the base environment of the `gfae_20240902` container (the dependency closure of ciftify and conda)
- `build.sh`: builds and names the image
