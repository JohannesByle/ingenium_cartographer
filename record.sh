source devel/setup.bash

roslaunch ros_mscl microstrain.launch&
sleep 5
rosrun velodyne_driver velodyne_node _model:=32C&
sleep 5
rosbag record /gx5/imu/data /velodyne_packets&
sleep 5
exit_code="n"
while [[ "$exit_code" != "y" ]]
do
	read -r -s -p "Stop recording (y/n): " exit_code
	printf '\n'
done
echo "$exit_code"
echo "Exiting gracefully:"
rosnode kill -a&
sleep 5
kill -9