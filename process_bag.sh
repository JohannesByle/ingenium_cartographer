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

# Copy config lua file
cp "$cwd/cartographer_config/config.lua" install_isolated/share/cartographer_ros/configuration_files/ingenium.lua
# Copy backpack launch file
cp "$cwd"/cartographer_config/backpack_3d.launch install_isolated/share/cartographer_ros/launch/ingenium_backpack_3d.launch
# Copy backpack urdf file
cp "$cwd"/cartographer_config/backpack_3d.urdf install_isolated/share/cartographer_ros/urdf/ingenium_backpack_3d.urdf
# Copy rviz config file
cp "$cwd"/cartographer_config/demo_3d.rviz install_isolated/share/cartographer_ros/configuration_files/ingenium.rviz
# Copy main launch file
cp "$cwd"/cartographer_config/main.launch install_isolated/share/cartographer_ros/launch/ingenium.launch

# Validate bag
cartographer_rosbag_validate -bag_filename "$file"
# Start slam
roslaunch cartographer_ros ingenium.launch bag_filename:="$file" pose_graph_filename:="$file".pbstream

# Move back to old directory
cd - || exit
