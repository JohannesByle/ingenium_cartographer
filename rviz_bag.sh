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

roscore &
sleep 2

rosbag play "$file" &
sleep 2

rosrun nodelet nodelet standalone velodyne_pointcloud/TransformNodelet &
sleep 2

rviz
