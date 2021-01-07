#!/bin/bash

# Get bag file from args
file1=$(realpath "$1")
file2=$(realpath "$2")
file3="$file1.registered.ply"
echo CloudCompare -SILENT -AUTO_SAVE OFF -C_EXPORT_FMT PLY -O "$file1" -O "$file2" -ICP -SAVE_CLOUDS FILE \""$file3 $file2.registered.ply"\"
CloudCompare -SILENT -AUTO_SAVE OFF -C_EXPORT_FMT PLY -O "$file1" -O "$file2" -ICP -SAVE_CLOUDS FILE "$file3 $file2.registered.ply"
CloudCompare -SILENT -O "$file3" -O "$file2" -c2c_dist -split_xyz -model HF SPHERE 0.01
