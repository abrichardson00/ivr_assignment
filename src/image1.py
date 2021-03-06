#!/usr/bin/env python3

import roslib
import sys
import rospy
import cv2
import numpy as np
from std_msgs.msg import String
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray, Float64
from cv_bridge import CvBridge, CvBridgeError


class image_converter:

  # Defines publisher and subscriber
  def __init__(self):
    # initialize the node named image_processing
    rospy.init_node('image_processing', anonymous=True)
    # initialize a publisher to send images from camera1 to a topic named image_topic1
    self.image_pub1 = rospy.Publisher("image_topic1",Image, queue_size = 1)
    # initialize a subscriber to recieve messages rom a topic named /robot/camera1/image_raw and use callback function to recieve data
    self.image_sub1 = rospy.Subscriber("/camera1/robot/image_raw",Image,self.callback1)
    # initialize the bridge between openCV and ROS
    self.bridge = CvBridge()
    
    self.joint2_pub = rospy.Publisher("/robot/joint2_position_controller/command",Float64, queue_size = 10)
    self.joint3_pub = rospy.Publisher("/robot/joint3_position_controller/command",Float64, queue_size = 10)
    self.joint4_pub = rospy.Publisher("/robot/joint4_position_controller/command",Float64, queue_size = 10)


  # Recieve data from camera 1, process it, and publish
  def callback1(self,data):
    # Recieve the image
    try:
      self.cv_image1 = self.bridge.imgmsg_to_cv2(data, "bgr8")
    except CvBridgeError as e:
      print(e)
    
    # Uncomment if you want to save the image
    #cv2.imwrite('image_copy.png', cv_image)

    #im1=cv2.imshow('window1', self.cv_image1)
    #cv2.waitKey(1)
    
    current_time = rospy.get_time()
    joint2 = (np.pi/2)*np.sin(np.array([(np.pi/15)*current_time]))
    joint3 = (np.pi/2)*np.sin(np.array([(np.pi/18)*current_time]))
    joint4 = (np.pi/2)*np.sin(np.array([(np.pi/20)*current_time]))
    
    joint2_payload = Float64()
    joint2_payload.data = joint2
    
    joint3_payload = Float64()
    joint3_payload.data = joint3
    
    joint4_payload = Float64()
    joint4_payload.data = joint4
    
    # Publish the results
    try: 
      self.joint2_pub.publish(joint2_payload)
      self.joint3_pub.publish(joint3_payload)
      self.joint4_pub.publish(joint4_payload)
      
      self.image_pub1.publish(self.bridge.cv2_to_imgmsg(self.cv_image1, "bgr8"))
    except CvBridgeError as e:
      print(e)

# call the class
def main(args):
  ic = image_converter()
  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting down")
  cv2.destroyAllWindows()

# run the code if the node is called
if __name__ == '__main__':
    main(sys.argv)


