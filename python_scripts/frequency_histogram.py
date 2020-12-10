import os
import matplotlib.pyplot as plt
from rosbag import Bag
import numpy as np
import sys


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
        if not os.path.exists("images"):
            os.makedirs("images")
        plt.savefig(os.path.join("images/", "{}.{}.png".format(os.path.basename(bag_file), topic.replace("/", ""))))
        plt.cla()
        # plt.show()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        get_info(sys.argv[1], sys.argv[2])
    else:
        get_info(sys.argv[1])
