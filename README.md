# ingenium_cartographer
Bash scripts and config files for recording and slamming data for the Wheaton College Tel Shimron lidar project

## Installation Instructions
The order of these steps is very important, and not following this order can lead to irreparable problems with the installation.

1. Install ROS Noetic using their [guide](http://wiki.ros.org/noetic/Installation/Ubuntu)
2. Install Cartographer ROS their [guide](https://google-cartographer-ros.readthedocs.io/en/latest/compilation.html)
    1. At the end of this process you should have a directory called `catkin_ws` in your home directory, i.e `~/catkin_ws/`
    2. This directory should have the following structure\
      catkin_ws/\
      ├─ build_isolated/\
      ├─ devel_isolated/\
      ├─ install_isolated/\
      ├─ src/
3. Clone the ingenium_cartographer repository into your home directory
    ```
    cd ~
    git clone https://github.com/JohannesByle/ingenium_cartographer
    ```
4. Run the custom installation script within ingenium_cartographer to finish installing the rest of the dependencies
    ```
    cd ~/ingenium_cartographer
    . ./install.sh
    ```
