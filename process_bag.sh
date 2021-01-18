#!/bin/bash

# Get bag file from args
cwd=$(pwd)
file=$(realpath "$1")
if [ "$2" = "-v" ]; then
  visualize=true
else
  visualize=false
fi
if [ ! -f "$file" ]; then
  echo "$file is not a file."
  return 1
fi
if [ ! "${file##*.}" = "bag" ]; then
  echo "$file is not a bag file"
  return 1
fi

# Move to catkin workspace
cd ~/catkin_ws/ || exit
# Run ros setup
source /opt/ros/noetic/setup.bash
# Run cartographer setup
source install_isolated/setup.bash

config_files=("slam.launch" "slam.lua" "localization.launch" "localization.lua" "lidar_stick.urdf" "slam_visualize.launch")
for config_file in "${config_files[@]}"; do
  directory="${config_file##*.}"
  if [ "$directory" == "lua" ]; then
    directory="configuration_files"
  fi
  cp "$HOME/ingenium_cartographer/cartographer_config/$config_file" "install_isolated/share/cartographer_ros/$directory/ingenium_$config_file"
done

# Check if bag contains point or packets, if packets forcefully convert
if ! [[ $(rosbag info "$file") =~ \/velodyne_points\ *[0-9]*\ msgs ]]; then
  echo "Bag does not contain pointcloud, forcefully converting"
  new_file="${file%.*}_pointcloud.bag"
  $(find . -name inquisitor) "$file" "$new_file"
  file="$new_file"
fi

filename="$(basename -- "$file" .bag)"
# Validate bag
cartographer_rosbag_validate -bag_filename "$file"
# Remove old .pbstream file
if [ -f "$file.pbstream" ]; then
  echo -e ".pbstream file already exists, will be deleted"
  rm "$file.pbstream"
fi
# Start slam
if $visualize; then
  roslaunch cartographer_ros ingenium_slam_visualize.launch bag_filename:="$file" urdf_filename:="~/ingenium_cartographer/cartographer_config/lidar_stick.urdf" &
else
  roslaunch cartographer_ros ingenium_slam.launch bag_filenames:="$file" urdf_filename:="~/ingenium_cartographer/cartographer_config/lidar_stick.urdf" &
fi
# Wait for slam to finish
while [ ! -f "$file.pbstream" ]; do
  sleep 5
done

roslaunch cartographer_ros ingenium_localization.launch pose_graph_filename:="$file.pbstream" bag_filenames:="$file"

# Move back to old directory
cd "$(dirname "$file")" || exit

# Make directory for new files
output_dir="$filename"
if [ ! -d "$output_dir" ]; then
  mkdir "$output_dir"
fi

# Move files into new directory, and then move the .pbstream file and the original bag file back
mv "$file"* "$output_dir"
cd "$output_dir" || exit
mv "$(basename "$file").pbstream" "$(dirname "$file")"
mv "$(basename "$file")" "$(dirname "$file")"

# Save a small copy of pointcloud
CloudCompare -SILENT -C_EXPORT_FMT PLY -O "$filename.bag_point_cloud.ply" -SS RANDOM 5000000

# Return to original directory
cd "$cwd" || exit

echo "Bag fully processed, press any key to exit"
read -r
