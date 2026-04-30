import time
import sys

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_

class CustomLidarReader:
    def __init__(self):
        self.point_cloud = None  
        self.firstRun = True
        self.count = 0
        
        # Performance tracking variables
        self.start_time = time.time()
        self.last_stats_time = time.time()
        self.interval_count = 0
        self.interval_bytes = 0

    def Init(self):
        # Create subscriber
        self.lidar_subscriber = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
        self.lidar_subscriber.Init(self.LidarMessageHandler, 10)

    def Start(self):
        print("LiDAR Reader Started. Waiting for data...")

    def LidarMessageHandler(self, msg: PointCloud2_):
        curr_time = time.time()
        self.point_cloud = msg
        self.count += 1
        
        # Track data for throughput calculation
        frame_bytes = len(msg.data)
        self.interval_bytes += frame_bytes
        self.interval_count += 1

        if self.firstRun:
            print("\n--- Successfully Connected to LiDAR! ---")
            self.firstRun = False
            self.last_stats_time = curr_time

        # Calculate stats every 1 second to keep the terminal readable
        elapsed_stats = curr_time - self.last_stats_time
        if elapsed_stats >= 1.0:
            hz = self.interval_count / elapsed_stats
            # Throughput calculation: (Bytes * 8 bits) / (1,000,000 for Megabits) / seconds
            mbps = (self.interval_bytes * 8) / 1_000_000 / elapsed_stats
            
            print(f"[{self.count}] Hz: {hz:.2f} | Throughput: {mbps:.2f} Mbps | Frame Size: {frame_bytes} bytes")
            
            # Reset interval counters
            self.interval_bytes = 0
            self.interval_count = 0
            self.last_stats_time = curr_time

if __name__ == '__main__':
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    custom = CustomLidarReader()
    custom.Init()
    custom.Start()

    try:
        while True:   
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)