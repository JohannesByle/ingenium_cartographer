#!/bin/bash

# Get bag file from args
ignored_file=mktemp
file1=$(realpath "$1")
file2=$(realpath "$2")
file3="$file1.registered.ply"
file4="$file1.color_distance.ply"
if [ $(wc -c <"$file1") -gt $(wc -c <"$file2") ]; then
  larger_file=$file1
  smaller_file=$file2
else
  larger_file=$file2
  smaller_file=$file1
fi

CloudCompare -SILENT -AUTO_SAVE OFF -C_EXPORT_FMT PLY -O "$smaller_file" -O "$larger_file" -ICP -SAVE_CLOUDS FILE "$file3 $ignored_file"
rm "$(realpath "$(dirname "$file1")")"/"$(basename "$smaller_file" .ply)"_REGISTRATION_MATRIX*.txt
CloudCompare -SILENT -O "$file3" -O "$file2" -c2c_dist -split_xyz -model HF SPHERE 0.1
