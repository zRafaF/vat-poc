import cv2
import numpy as np

# Create a black image (height, width, channels)
# 500x500 pixels, 3 color channels
window_name = "Red Window Test"
img = np.zeros((500, 500, 3), np.uint8)

# Fill the image with Red (BGR: Blue=0, Green=0, Red=255)
img[:] = (0, 0, 255)

try:
    # Create the window explicitly
    cv2.namedWindow(window_name)
    
    # Show the image
    cv2.imshow(window_name, img)

    print("Window created. Press any key to close.")
    cv2.waitKey(0) # Wait indefinitely for a key press

finally:
    # Cleanup properly to avoid the Null pointer error
    cv2.destroyAllWindows()