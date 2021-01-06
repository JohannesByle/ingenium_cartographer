# ingenium_cartographer
Bash scripts and config files for recording and slamming data for the Wheaton College Tel Shimron lidar project

## Installation Instructions
The order of these steps is very important, and not following this order can lead to irreparable problems with the installation.

1. Install ROS Noetic using their [guide](http://wiki.ros.org/noetic/Installation/Ubuntu)
2. Install Cartographer ROS their [guide](https://google-cartographer-ros.readthedocs.io/en/latest/compilation.html). This step can be skipped if cartographer is not needed and the repo is only being used to record data.
    1. At the end of this process you should have a directory called `catkin_ws` in your home directory, i.e `~/catkin_ws/`
    2. This directory should have the following structure\
      catkin_ws/\
      ├─ build_isolated/\
      ├─ devel_isolated/\
      ├─ install_isolated/\
      ├─ src/
3. Download the binaries for the MSCL library. This [link](https://github.com/LORD-MicroStrain/MSCL/releases/download/v61.0.16/c++-mscl_61.0.16_amd64.deb) will start the download. Once the download has finished install the binaries using dpgk.
    ```
    cd ~/Downloads
    sudo dpkg -i c++-mscl_61.0.16_amd64.deb
    sudo apt install -f     
    ```
4. Clone the ingenium_cartographer repository into your home directory
    ```
    cd ~
    git clone https://github.com/JohannesByle/ingenium_cartographer
    ```
5. Run the custom installation script within ingenium_cartographer to finish installing the rest of the dependencies
    ```
    cd ~/ingenium_cartographer
    . ./install.sh
    ```
