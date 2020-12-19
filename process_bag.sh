# Get bag file from args
cwd=$(pwd)
file="$cwd/$1"
if [ ! -f "$file" ]; then
  echo "$file is not a file."
  return 1
fi

# Move to catkin workspace
cd ~/catkin_ws/ || exit
# Run ros setup
source /opt/ros/noetic/setup.bash
# Run cartographer setup
source install_isolated/setup.bash

config_files=("slam.launch" "slam.lua" "localization.launch" "localization.lua" "lidar_stick.urdf")
for config_file in "${config_files[@]}"; do
  directory="${config_file##*.}"
  if [ "$directory" == "lua" ]; then
    directory="configuration_files"
  fi
  cp "$cwd/cartographer_config/$config_file" "install_isolated/share/cartographer_ros/$directory/ingenium_$config_file"
done

# Check if bag contains point or packets, if packets forcefully convert
if ! [[ $( rosbag info "$file") =~ \/velodyne_points\ *[0-9]*\ msgs ]]; then
  echo "Bag does not contain pointcloud, forcefully converting"
  new_file="${file%.*}_pointcloud.bag"
  $(find . -name inquisitor) "$file" "$new_file"
  file="$new_file"
fi
return

# Validate bag
cartographer_rosbag_validate -bag_filename "$file"
# Remove old .pbstream file
if [ -f "$file.pbstream" ]; then
  echo -e ".pbstream file already exists, will be deleted"
  rm "$file.pbstream"
fi
# Start slam
roslaunch cartographer_ros ingenium_slam.launch bag_filenames:="$file" urdf_filename:="$file/cartographer_config/lidar_stick.urdf" &
# Wait for slam to finish
while [ ! -f "$file.pbstream" ]; do
  sleep 5
done

roslaunch cartographer_ros ingenium_localization.launch pose_graph_filename:="$file.pbstream" bag_filenames:="$file"

# Move back to old directory
cd "$(dirname "$file")" || exit

# Make directory for new files
output_dir="${file%.*}_output_files"
if [ ! -d "$output_dir" ]; then
  mkdir "$output_dir"
fi

# Move files into new directory, and then move the .pbstream file and the original bag file back
mv "$file"* "$output_dir"
cd "$output_dir" || exit
mv "$(basename "$file").pbstream" "$(dirname "$file")"
mv "$(basename "$file")" "$(dirname "$file")"

# Return to original directory
cd "$cwd" || exit
