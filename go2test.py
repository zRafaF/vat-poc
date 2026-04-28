import time
import sys

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
# Import PointCloud2_ from the sensor_msgs IDL 
# (Note: If you get an import error, prefix this with 'unitree_sdk2_python.' like you did earlier)
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_

class CustomLidarReader:
    def __init__(self):
        self.point_cloud = None  
        self.firstRun = True
        self.count = 0

    def Init(self):
        # create subscriber # 
        # Using the deskewed cloud topic we found in your DDS network scan
        self.lidar_subscriber = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
        self.lidar_subscriber.Init(self.LidarMessageHandler, 10)

    def Start(self):
        # Unlike the motor example, we don't need a RecurrentThread here because 
        # we are passively listening, not actively writing commands to the robot at 500Hz.
        # The ChannelSubscriber automatically handles incoming data in the background.
        print("LiDAR Reader Started. Waiting for data...")

    def LidarMessageHandler(self, msg: PointCloud2_):
        self.point_cloud = msg
        self.count += 1
        
        if self.firstRun:
            print("\n--- Successfully Connected to LiDAR! ---")
            self.firstRun = False
            
        # Print basic stats about the incoming point cloud frame
        print(f"[{self.count}] Received Frame | Width: {msg.width}, Height: {msg.height}, Bytes: {len(msg.data)}")


if __name__ == '__main__':
    
    # Initialize network interface exactly like the example
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    # Instantiate, Init, and Start
    custom = CustomLidarReader()
    custom.Init()
    custom.Start()

    # Keep the main thread alive to allow the subscriber to listen
    try:
        while True:   
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)