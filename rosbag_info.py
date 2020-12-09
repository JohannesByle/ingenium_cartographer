import os
import matplotlib.pyplot as plt
from rosbag import Bag
import numpy as np


def get_info(bag_file, topic_filter=None):
    bag = Bag(bag_file)
    topics = bag.get_type_and_topic_info().topics
    for topic in topics:
        if topic_filter and topics[topic].msg_type not in topic_filter:
            continue
        print("{}: {} Hz".format(topic, round(topics[topic].frequency, 3)))
        print(topics[topic].message_count)
        times = np.ones(shape=bag.get_message_count(topic_filters=topic))
        n = 0
        for _, msg, t in bag.read_messages(topics=topic):
            times[n] = msg.header.stamp.to_sec()
            n += 1
        times = 1 / np.gradient(times)
        times = times[np.where((times > np.percentile(times, 10)) & (times < np.percentile(times, 90)))]
        print("mean: {}, median: {}".format(np.mean(times), np.median(times)))
        print("min: {}, max: {}".format(np.min(times), np.max(times)))
        # plt.scatter(times, np.gradient(times))
        plt.hist(times)
        plt.yscale("log")
        plt.title("{}: {}".format(os.path.basename(bag_file), topic))
        plt.savefig(os.path.join("with_filter/", "{}.{}.png".format(os.path.basename(bag_file), topic[1:])))
        plt.cla()
        # plt.show()


# get_info("bags/2020-11-18-20-32-47.bag")
folder = "/home/johannes/Downloads"
# for file in os.listdir(folder):
#     if not file.endswith("bag") or not (file.startswith("b3") or file.startswith("2020")):
#         continue
#     print()
#     print(file)
#     try:
#         get_info(os.path.join(folder, file), topic_filter=["sensor_msgs/PointCloud2", "velodyne_msgs/VelodyneScan"])
#     except Exception as e:
#         print("{}: {}".format(file, e))
get_info("bags/test.bag", topic_filter=["sensor_msgs/PointCloud2", "velodyne_msgs/VelodyneScan"])
