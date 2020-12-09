// Include the ROS C++ APIs
#include <ros/ros.h>
#include <rosbag/bag.h>
#include <rosbag/view.h>
#include <std_msgs/Int32.h>
#include <std_msgs/String.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/PointCloud2.h>
#include <velodyne_msgs/VelodyneScan.h>
#include <velodyne_pointcloud/rawdata.h>
#include <velodyne_pointcloud/pointcloudXYZIRT.h>
#include <velodyne_pointcloud/transform.h>
#include <cmath>

#include <boost/foreach.hpp>

#define foreach BOOST_FOREACH

// Standard C++ entry point
int main(int argc, char **argv) {
    std::string x(argv[1]);
    std::string y(argv[2]);
    velodyne_rawdata::RawData data;
    double min_range = 0.0;
    double max_range = 120.0;
    data.setParameters(min_range, max_range, 0, 2 * M_PI);
    data.setupOffline("/home/johannes/catkin_ws/src/velodyne/velodyne_pointcloud/params/VeloView-VLP-32C.yaml",
                      max_range, min_range);
    rosbag::Bag new_bag;
    new_bag.open(y, rosbag::bagmode::Write);

    rosbag::Bag bag;
    bag.open(x, rosbag::bagmode::Read);
    boost::shared_ptr <velodyne_rawdata::DataContainerBase> container_ptr;
    rosbag::View view(bag);
    foreach(rosbag::MessageInstance
    const m, view)
    {

        velodyne_msgs::VelodyneScan::ConstPtr s = m.instantiate<velodyne_msgs::VelodyneScan>();
        if (s != NULL) {
            sensor_msgs::PointCloud2Ptr pts = data.unpackOffline(s->packets[0], s->header.stamp);
            new_bag.write("/velodyne_points", s->header.stamp, *pts);
        }
        sensor_msgs::Imu::ConstPtr r = m.instantiate<sensor_msgs::Imu>();
        if (r != NULL) {
            new_bag.write("/gx5/imu/data", r->header.stamp, *r);
        }

    }
    std::cout << "completely done";
    bag.close();
}