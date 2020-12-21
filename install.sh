cwd=$(pwd)
cd ~/catkin_ws_test/src || exit

git clone https://github.com/ros-drivers/velodyne
cd velodyne || exit
# This stage of the repo was tested to be working, but may not work with future ROS releases
git reset --hard f235ac6
git pull
cd .. || exit

git clone https://github.com/LORD-MicroStrain/ROS-MSCL
cd ROS-MSCL || exit
# This stage of the repo was tested to be working, but may not work with future ROS releases
git reset --hard ecf15a7
git pull
cd .. || exit

cd ~/catkin_ws_test/ || exit
catkin_make_isolated --install --use-ninja
cd ~/catkin_ws_test/src || exit

sudo rm -r velodyne
git clone https://github.com/JohannesByle/velodyne

cd ~/catkin_ws_test/ || exit
catkin_make_isolated --install --use-ninja
cd "$cwd" || exit
