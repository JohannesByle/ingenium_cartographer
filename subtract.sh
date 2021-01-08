#!/bin/bash

# Get bag file from args
file1=$(realpath "$1")
file2=$(realpath "$2")
if [ $(wc -c <"$file1") -gt $(wc -c <"$file2") ]; then
  switch="-REFERENCE_IS_FIRST"
else
  switch=""
fi

CloudCompare -SILENT -AUTO_SAVE OFF -C_EXPORT_FMT PLY -O "$file1" -O "$file2" -ICP $switch -SAVE_CLOUDS FILE "$file1.registered.ply $file2.registered.ply"
CloudCompare -SILENT -AUTO_SAVE OFF -C_EXPORT_FMT BIN -O "$file1.registered.ply" -SS RANDOM 5000000 -O "$file2.registered.ply" -SS RANDOM 5000000 -c2c_dist -split_xyz -model HF SPHERE 0.01 -SAVE_CLOUDS FILE "$file1.color_distance.bin $(mktemp)"
echo "Subtraction completed, press any key to exit"
read -r
