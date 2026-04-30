import cv2
import subprocess

# --- CONFIGURATION ---
# Replace with the actual IP address of your Server machine!
SERVER_IP = "127.0.0.1" 
PORT = "8888"

# Open the webcam (0 is usually the default camera)
cap = cv2.VideoCapture(1)

# Get camera properties to tell FFmpeg what to expect
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0.0 or fps == -1.0:
    fps = 30.0 # Fallback if camera doesn't report FPS

# --- FFMPEG COMMAND ---
# This is the secret to low latency. We are instructing FFmpeg to:
# 1. Take raw frames from stdin
# 2. Encode to H.264 using the 'ultrafast' preset and 'zerolatency' tuning
# 3. Stream out via SRT to the listener
ffmpeg_cmd = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f"{width}x{height}",
    '-r', str(fps),
    '-i', '-',          # Read input from stdin (Python pipe)
    '-c:v', 'libx264',  # Use H.264 encoding
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-b:v', '2000k',    # Bitrate (2 Mbps is a good balance of quality/speed)
    '-pix_fmt', 'yuv420p',
    '-f', 'mpegts',
    f'srt://{SERVER_IP}:{PORT}?mode=caller&transtype=live&latency=50'
]

print(f"Connecting to Server at {SERVER_IP}:{PORT}...")

# Start the FFmpeg process
process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame from camera.")
        break

    # Write the raw frame bytes to FFmpeg's standard input
    try:
        process.stdin.write(frame.tobytes())
    except BrokenPipeError:
        print("Server disconnected or FFmpeg crashed.")
        break

    # Optional: Display the video locally on the robot to ensure the camera is working
    cv2.imshow("Robot: Local Camera View", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
if process.stdin:
    process.stdin.close()
process.wait()
cv2.destroyAllWindows()