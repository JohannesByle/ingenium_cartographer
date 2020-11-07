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

# Copy config file
cp "$cwd/config.lua" install_isolated/share/cartographer_ros/configuration_files/my_robot.lua
# Copy launch file
#cp install_isolated/share/cartographer_ros/launch/demo_backpack_3d.launch install_isolated/share/cartographer_ros/launch/demo_my_robot.launch
cp "$cwd"/custom.launch install_isolated/share/cartographer_ros/launch/demo_my_robot.launch
# Validate bag
cartographer_rosbag_validate -bag_filename "$file"
# Start slam
roslaunch cartographer_ros demo_my_robot.launch bag_filename:="$file" pose_graph_filename:="$file".pbstream

# Move back to old directory
cd - || exit
