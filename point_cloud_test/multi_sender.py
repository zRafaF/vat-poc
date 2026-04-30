import time
import sys
import socket
import struct
import json
import zlib
import threading
import queue

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
from unitree_sdk2py.idl.geometry_msgs.msg.dds_ import PoseStamped_

PC_IP = "192.168.123.122"
PORT = 5555

class LidarTCPStreamer:
    def __init__(self):
        self.count = 0
        self.frame_queue = queue.Queue(maxsize=1) 
        
        # State variables to hold the latest data
        self.latest_lowstate = None
        self.latest_pose = None
        
        # Start the persistent network thread
        self.net_thread = threading.Thread(target=self._network_loop, daemon=True)
        self.net_thread.start()

    def _network_loop(self):
        sock = None
        while True:
            try:
                if sock is None:
                    print(f"[Network] Attempting to connect to {PC_IP}:{PORT}...")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0)
                    sock.connect((PC_IP, PORT))
                    sock.settimeout(None)
                    print("[Network] Successfully connected to PC!")
            except Exception:
                sock = None
                time.sleep(1)
                continue

            try:
                # Wait for a frame from the LiDAR callback
                msg, current_count = self.frame_queue.get(timeout=1.0)
                
                raw_bytes = bytes(msg.data)
                compressed_data = zlib.compress(raw_bytes, level=3)
                
                # Bundle the latest motor, IMU, and pose data into the JSON header
                header_dict = {
                    "frame": current_count,
                    "point_step": msg.point_step,
                    "robot_state": self.latest_lowstate,
                    "robot_pose": self.latest_pose
                }
                
                header_bytes = json.dumps(header_dict).encode('utf-8')
                
                # Frame the message: [Header Size] [Payload Size] [Header JSON] [Compressed LiDAR]
                sizes_frame = struct.pack(">II", len(header_bytes), len(compressed_data))
                
                sock.sendall(sizes_frame + header_bytes + compressed_data)
                
            except queue.Empty:
                pass 
            except Exception as e:
                print(f"[Network] Connection lost ({e}). Retrying...")
                sock.close()
                sock = None

    def Init(self):
        # 1. LiDAR Subscriber
        self.lidar_subscriber = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
        self.lidar_subscriber.Init(self.LidarMessageHandler, 10)
        
        # 2. Motor & IMU Subscriber
        self.state_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.state_subscriber.Init(self.StateHandler, 10)

        # 3. Robot Pose Subscriber
        self.pose_subscriber = ChannelSubscriber("rt/utlidar/robot_pose", PoseStamped_)
        self.pose_subscriber.Init(self.PoseHandler, 10)

    def Start(self):
        print("Multimodal Streamer Started. Waiting for data...")

    def StateHandler(self, msg: LowState_):
        # Extract the joint angles (q) for all 12 motors
        motors = [msg.motor_state[i].q for i in range(12)]
        
        # Extract the IMU data
        imu = {
            "quaternion": list(msg.imu_state.quaternion),
            "gyroscope": list(msg.imu_state.gyroscope),
            "accelerometer": list(msg.imu_state.accelerometer)
        }
        
        self.latest_lowstate = {
            "motors": motors,
            "imu": imu
        }

    def PoseHandler(self, msg: PoseStamped_):
        self.latest_pose = {
            "position": [msg.pose.position.x, msg.pose.position.y, msg.pose.position.z],
            "orientation": [msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w]
        }

    def LidarMessageHandler(self, msg: PointCloud2_):
        self.count += 1
        
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        self.frame_queue.put((msg, self.count))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    streamer = LidarTCPStreamer()
    streamer.Init()
    streamer.Start()

    try:
        while True:   
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)