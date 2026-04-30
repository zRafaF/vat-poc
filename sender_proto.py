import time
import sys
import socket
import struct
import zlib
import threading
import queue

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.sensor_msgs.msg.dds_ import PointCloud2_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_, SportModeState_
from unitree_sdk2py.idl.geometry_msgs.msg.dds_ import PoseStamped_

# Import the generated proto
import go2_stream_pb2 

PC_IP = "192.168.123.122"
PORT = 5555

class Go2ProtobufStreamer:
    def __init__(self):
        self.count = 0
        self.frame_queue = queue.Queue(maxsize=1)
        self.latest_low = None
        self.latest_sport = None
        self.latest_pose = None
        
        self.net_thread = threading.Thread(target=self._network_loop, daemon=True)
        self.net_thread.start()

    def _network_loop(self):
        sock = None
        while True:
            try:
                if sock is None:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0)
                    sock.connect((PC_IP, PORT))
                    sock.settimeout(None)
                    print("[Network] Connected via Protobuf!")
            except:
                sock = None
                time.sleep(1); continue

            try:
                # Wait for LiDAR frame to trigger the send
                lidar_msg, current_count = self.frame_queue.get(timeout=1.0)
                
                # Build the Master Proto Frame
                frame = go2_stream_pb2.Go2StreamFrame()
                frame.version = 1
                frame.frame_idx = current_count
                
                # 1. LiDAR Cloud
                frame.lidar_cloud.point_step = lidar_msg.point_step
                frame.lidar_cloud.data = zlib.compress(bytes(lidar_msg.data), level=3)
                
                # 2. Low State (Motors/Wheels + IMU)
                if self.latest_low:
                    for m in self.latest_low.motor_state:
                        ms = frame.low_state.motor_state.add()
                        ms.q = m.q; ms.dq = m.dq; ms.ddq = m.ddq
                        ms.tau_est = m.tau_est; ms.temperature = m.temperature
                    
                    frame.low_state.imu_state.quaternion.extend(self.latest_low.imu_state.quaternion)
                    frame.low_state.imu_state.gyroscope.extend(self.latest_low.imu_state.gyroscope)
                    frame.low_state.bms_state.soc = self.latest_low.bms_state.soc
                
                # 3. Sport Mode State[cite: 5]
                if self.latest_sport:
                    frame.sport_mode_state.mode = self.latest_sport.mode
                    frame.sport_mode_state.gait_type = self.latest_sport.gait_type
                    frame.sport_mode_state.foot_force.extend(self.latest_sport.foot_force)
                
                # Serialize and Send
                serialized_data = frame.SerializeToString()
                sock.sendall(struct.pack(">I", len(serialized_data)) + serialized_data)
                
            except queue.Empty: pass
            except Exception as e:
                print(f"Conn lost: {e}"); sock.close(); sock = None

    def Init(self):
        # Existing subscribers from dds topics[cite: 2]
        ChannelSubscriber("rt/utlidar/cloud", PointCloud2_).Init(self.LidarHandler, 10)
        ChannelSubscriber("rt/lowstate", LowState_).Init(self.LowHandler, 10)
        ChannelSubscriber("rt/lf/sportmodestate", SportModeState_).Init(self.SportHandler, 10)

    def LidarHandler(self, msg):
        self.count += 1
        if self.frame_queue.full(): self.frame_queue.get_nowait()
        self.frame_queue.put((msg, self.count))

    def LowHandler(self, msg): self.latest_low = msg
    def SportHandler(self, msg): self.latest_sport = msg

if __name__ == '__main__':
    ChannelFactoryInitialize(0)
    streamer = Go2ProtobufStreamer()
    streamer.Init()
    while True: time.sleep(1)