# Run cartographer setup
source ~/catkin_ws/install_isolated/setup.bash

# Start the connection to the imu (and start roscore in the background)
roslaunch ros_mscl microstrain.launch&
sleep 2

# Start the connection to the lidar
rosrun velodyne_driver velodyne_node _model:=32C _npackets:=1 _rpm:=300&
sleep 2

# Start recording specific nodes from the lidar and the imu
rosbag record /gx5/imu/data /velodyne_packets&
sleep 2

# Wait for user input and then attempt to kill gracefully
exit_code="n"
while [[ "$exit_code" != "y" ]]; do
  read -r -s -p "Stop recording (y/n): " exit_code
  printf '\n'
done
echo "$exit_code"
echo "Exiting gracefully:"
rosnode kill -a &
sleep 5
pkill roscore 
