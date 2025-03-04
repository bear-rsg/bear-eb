#!/bin/bash
#SBATCH -J Relion
#SBATCH -n XXXmpinodesXXX
#SBATCH -c XXXthreadsXXX
#SBATCH -e XXXerrfileXXX
#SBATCH -o XXXoutfileXXX
#SBATCH XXXqosXXX
#SBATCH -t XXXextra1XXX
#SBATCH -A XXXextra2XXX
#SBATCH XXXextra3XXX
#SBATCH --export=NONE
#SBATCH --get-user-env

module purge; module load baskerville
module load RELION/RELIONVER

srun XXXcommandXXX
