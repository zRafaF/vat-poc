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

PC_IP = "192.168.123.122"
PORT = 5555

class LidarTCPStreamer:
    def __init__(self):
        self.count = 0
        # Queue size 1 ensures we drop old frames and only send the newest
        # if the network is slower than the sensor.
        self.frame_queue = queue.Queue(maxsize=1) 
        
        # Start the persistent network thread
        self.net_thread = threading.Thread(target=self._network_loop, daemon=True)
        self.net_thread.start()

    def _network_loop(self):
        sock = None
        while True:
            # 1. Reconnection Logic
            try:
                if sock is None:
                    print(f"[Network] Attempting to connect to {PC_IP}:{PORT}...")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0) # 2-second timeout so it doesn't hang forever
                    sock.connect((PC_IP, PORT))
                    sock.settimeout(None) # Back to blocking mode for sending
                    print("[Network] Successfully connected to PC!")
            except Exception:
                sock = None
                time.sleep(1) # Wait before retrying
                continue

            # 2. Sending Logic
            try:
                # Wait for a frame from the LiDAR callback
                msg, current_count = self.frame_queue.get(timeout=1.0)
                
                raw_bytes = bytes(msg.data)
                compressed_data = zlib.compress(raw_bytes, level=3)
                
                header_dict = {
                    "frame": current_count,
                    "point_step": msg.point_step
                }
                header_bytes = json.dumps(header_dict).encode('utf-8')
                
                # Frame the message
                sizes_frame = struct.pack(">II", len(header_bytes), len(compressed_data))
                
                # Send it all
                sock.sendall(sizes_frame + header_bytes + compressed_data)
                
            except queue.Empty:
                pass # No data from LiDAR yet, just loop
            except Exception as e:
                print(f"[Network] Connection lost ({e}). Retrying...")
                sock.close()
                sock = None

    def Init(self):
        self.lidar_subscriber = ChannelSubscriber("rt/utlidar/cloud", PointCloud2_)
        self.lidar_subscriber.Init(self.LidarMessageHandler, 10)

    def Start(self):
        print("LiDAR Streamer Started. Waiting for data...")

    def LidarMessageHandler(self, msg: PointCloud2_):
        self.count += 1
        
        # Push to queue. If queue is full, drop the oldest frame.
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