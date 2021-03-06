#!/usr/bin/env python3

import roslib
import sys
import rospy
import cv2
import numpy as np
import message_filters
from std_msgs.msg import String
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray, Float64
from cv_bridge import CvBridge, CvBridgeError

class joint_angles:

  def __init__(self):
    rospy.init_node('joint_angles_node', anonymous = True)
    self.img1_subscriber = message_filters.Subscriber("/image_topic1", Image)
    self.img2_subscriber = message_filters.Subscriber("/image_topic2", Image)
        
    time_sync = message_filters.TimeSynchronizer([self.img1_subscriber, self.img2_subscriber], 1)
    time_sync.registerCallback(self.callback)
    
    self.bridge = CvBridge()
    
    self.joint_angles_publisher = rospy.Publisher("joint_angles", Float64MultiArray, queue_size=1)
    

  def callback(self, yz_image_msg, xz_image_msg):
    try:
      self.yz_image = self.bridge.imgmsg_to_cv2(yz_image_msg, "bgr8")
      self.xz_image = self.bridge.imgmsg_to_cv2(xz_image_msg, "bgr8")
      
      #yz_image_normalized = self.normalizeRGB(self.yz_image)
      #xz_image_normalized = self.normalizeRGB(self.xz_image)
      
      #cv2.imshow('yz_view', yz_image_normalized)
      #cv2.imshow('xz_view', xz_image_normalized)
      #cv2.waitKey(1)
      
      detected_centroids_yz = self.get_black_joint_centers(self.yz_image)
      detected_centroids_xz = self.get_black_joint_centers(self.xz_image)
      
      
      red_centroid_yz = detected_centroids_yz[1]
      green_centroid_yz = detected_centroids_yz[0]
      blue_centroid_yz = np.array([398,470])
      yellow_centroid_yz = np.array([398,535])
      
      red_centroid_xz = detected_centroids_xz[1]
      green_centroid_xz = detected_centroids_xz[0]
      blue_centroid_xz = np.array([398,470])
      yellow_centroid_xz = np.array([398,535])
      
      yz_centroids = np.array([yellow_centroid_yz, blue_centroid_yz, green_centroid_yz, red_centroid_yz])
      xz_centroids = np.array([yellow_centroid_xz, blue_centroid_xz, green_centroid_xz, red_centroid_xz])
      
      centered_yz_centroids = self.center_image_coordinates_around_first_joint(yz_centroids[0],yz_centroids[1:])
      centered_xz_centroids = self.center_image_coordinates_around_first_joint(xz_centroids[0],xz_centroids[1:])
      
      coordinates_3d = self.merge_plane_coordinates(centered_yz_centroids, centered_xz_centroids)
      
      self.compute_joint_angles(coordinates_3d)
      
      joint_angles = self.compute_joint_angles(coordinates_3d)
      
      #print(joint_angles)
      
      joint_angles_payload = Float64MultiArray()
      joint_angles_payload.data = joint_angles
      self.joint_angles_publisher.publish(joint_angles_payload)
      
    except CvBridgeError as e:
      print(e)
  
  
  def get_black_joint_centers(self, image):
    
    binary_image = cv2.inRange(image, (0, 0, 0), (10, 10, 10))
    
    joint_1_coordinates = np.array([398,535])
    joint_2_coordinates = np.array([398,470])
    
    joint_matches = cv2.HoughCircles(binary_image, cv2.HOUGH_GRADIENT, dp=1.0, minDist=0.78, maxRadius=18, param1=100, param2=7)
    
    if(len(joint_matches) == 0 or len(joint_matches[0,:]) < 1):
      return np.array([joint_2_coordinates, joint_2_coordinates], dtype=np.int64)
    
    joint_matches = joint_matches.astype(np.int64)
    joint_matches = joint_matches[0,:]
    
    minimum_distance = 50
    
    if(len(joint_matches) >= 2):
      joint_centers = []
      joints_found = False
      
      while(True):
        for joint_match in joint_matches:
          
          match_to_joint_1_vector = joint_1_coordinates - joint_match[0:2]
          match_to_joint_2_vector = joint_2_coordinates - joint_match[0:2]
          
          distance_of_match_from_joint_1 = np.linalg.norm(match_to_joint_1_vector)
          distance_of_match_from_joint_2 = np.linalg.norm(match_to_joint_2_vector)
          
          if(distance_of_match_from_joint_1 >= minimum_distance and distance_of_match_from_joint_2 >= minimum_distance):
            if(len(joint_centers) < 2):
              joint_centers.append(joint_match[0:2])
            if(len(joint_centers) >= 2):
            
              match_distances_from_joint_2 = np.array( [ np.linalg.norm(joint_centers[0]-joint_2_coordinates) , np.linalg.norm(joint_centers[1]-joint_2_coordinates)] )
              
              joint_3_center = joint_centers[ np.argmin(match_distances_from_joint_2) ]
              joint_4_center = joint_centers[ np.argmax(match_distances_from_joint_2) ]
              
              joint_centers[0] = joint_3_center
              joint_centers[1] = joint_4_center
              
              joints_found = True
              break
        if(joints_found == True):
          return np.array(joint_centers, dtype=np.int64)
        else:
          minimum_distance = minimum_distance - 5
          
    elif(len(joint_matches) == 1):
      return np.array([joint_matches[0,0:2], joint_matches[0,0:2]], dtype=np.int64)
  
  
  def compute_joint_angles(self, joint_coordinates):
    blue_coordinates = joint_coordinates[1]
    green_coordinates = joint_coordinates[2]
    
    blue_green_vector = green_coordinates - blue_coordinates
    joint_2_angle = -np.arctan2(blue_green_vector[1],blue_green_vector[2])
    
    joint_coordinates_rotated_around_x = self.rotate_around_x_axis(-joint_2_angle, joint_coordinates)
    
    blue_coordinates_rotated_around_x = joint_coordinates_rotated_around_x[1]
    green_coordinates_rotated_around_x = joint_coordinates_rotated_around_x[2]
    
    blue_green_vector_rotated_around_x = green_coordinates_rotated_around_x - blue_coordinates_rotated_around_x
    joint_3_angle = np.arctan2(blue_green_vector_rotated_around_x[0], blue_green_vector_rotated_around_x[2])
    
    joint_coordinates_rotated_around_x_and_y = self.rotate_around_y_axis(joint_3_angle, joint_coordinates_rotated_around_x)
    
    #print(joint_coordinates_rotated_around_x_and_y)
    
    green_coordinates_rotated_around_x_and_y = joint_coordinates_rotated_around_x_and_y[2]
    red_coordinates_rotated_around_x_and_y = joint_coordinates_rotated_around_x_and_y[3]
    
    green_red_vector_rotated_around_x_and_y = red_coordinates_rotated_around_x_and_y - green_coordinates_rotated_around_x_and_y
    joint_4_angle = -np.arctan2(green_red_vector_rotated_around_x_and_y[1], green_red_vector_rotated_around_x_and_y[2])
    
    
    joint_angles = np.array([joint_2_angle, joint_3_angle, joint_4_angle])
    
    #print(joint_angles)
    
    return joint_angles
  
  
  def rotate_around_y_axis(self, angle, coordinates):
    new_coordinates = np.zeros((len(coordinates),3), dtype=np.int64)
    rotation_matrix = np.array([[np.cos(angle), 0, -np.sin(angle)],[0, 1, 0],[np.sin(angle), 0, np.cos(angle)]])
    
    for i in range(len(coordinates)):
      new_coordinates[i] = rotation_matrix.dot(coordinates[i])
      
    return new_coordinates
  
  def rotate_around_x_axis(self, angle, coordinates):
    
    new_coordinates = np.zeros((len(coordinates),3), dtype=np.int64)
    rotation_matrix = np.array([[1, 0, 0],[0, np.cos(angle), -np.sin(angle)],[0, np.sin(angle), np.cos(angle)]])
    
    for i in range(len(coordinates)):
      new_coordinates[i] = rotation_matrix.dot(coordinates[i])
      
    return new_coordinates
    
  
  def merge_plane_coordinates(self, yz_coordinates, xz_coordinates):
    coordinates_3d = np.zeros((len(yz_coordinates),3))
    
    for i in range(len(yz_coordinates)):
      xz = xz_coordinates[i]
      yz = yz_coordinates[i]
      
      if(xz[0] == None):
        xz = self.infer_coordinates(i, xz_coordinates, yz_coordinates)
      
      elif(yz[0] == None):
        yz = self.infer_coordinates(i, yz_coordinates, xz_coordinates)
        
      coordinates_3d[i] = np.array([xz[0], yz[0], yz[1]])
    
    return coordinates_3d
    
      
  def infer_coordinates(self, i, loss_coordinates, coordinates_for_inference):
    the_same_point_in_different_plane = coordinates_for_inference[i]
    
    closest_point_index_on_z_axis = None
    
    for j in range(len(coordinates_for_inference)):
      if(j == i):
        continue
      
      if(closest_point_index_on_z_axis == None):
        closest_point_index_on_z_axis = j
        continue
      elif(abs(the_same_point_in_different_plane[1]-coordinates_for_inference[j,1]) < abs(the_same_point_in_different_plane[1]-coordinates_for_inference[closest_point_index_on_z_axis,1])):
        closest_point_index_on_z_axis = j
        continue
    
    inferred_coordinates = np.array([loss_coordinates[closest_point_index_on_z_axis, 0],coordinates_for_inference[i,1]])
    
    return inferred_coordinates
        
  
  def center_image_coordinates_around_first_joint(self, first_joint, other_joints):
    
    new_coordinates = np.zeros((len(other_joints)+1,2))
    new_coordinates[0] = np.array([0,0])
    
    for i in range(len(other_joints)):
      if(other_joints[i,0] == None):
        new_coordinates[i+1] = other_joints[i]
        continue
      
      new_coordinates[i+1] = other_joints[i]-first_joint
      new_coordinates[i+1,1] = new_coordinates[i+1,1]*(-1)
    
    return new_coordinates
      
    
  
  def get_joint_center(self, image, thresholds, color_name, erosion=0, dilation=0):
    binary_image = cv2.inRange(image, thresholds[0], thresholds[1])
    
    kernel = np.ones((2, 2), np.uint8)
    eroded_image = cv2.erode(binary_image, kernel, iterations=erosion)
    dilated_image = cv2.dilate(eroded_image, kernel, iterations=dilation)
    final_image = dilated_image
    
    #cv2.imshow(color_name, final_image)
    #cv2.waitKey(1)
    
    #contours,hierarchy = cv2.findContours(final_image, 1, 2)
    
    #if(len(contours) == 0):
      #return np.array([None,None])
    
    #contour = contours[0]
    #M = cv2.moments(contour)
    
    M = cv2.moments(final_image)
    
    #compactness = (2*np.sqrt(M['m00']*np.pi))/cv2.arcLength(contour,True)
    
    if(M['m00'] == 0):
      return np.array([None, None])
    
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    centroid = np.array([cx, cy])
    
    #print(color_name, 'centroid', centroid)
    # return final_image, centroid
    return centroid
  
  def normalizeRGB(self, img):
  
    height, width = img.shape[:2]
  
    normalized_rgb = np.zeros((height,width,3),np.float64)
    
    img_float = img.astype(np.float64)
    
    b = img_float[:,:,0]
    g = img_float[:,:,1]
    r = img_float[:,:,2]
    
    rgb_sum = b + g + r
    rgb_sum[rgb_sum == 0] = 1
    
    normalized_rgb[:,:,0]=(b/rgb_sum)*255.0
    normalized_rgb[:,:,1]=(g/rgb_sum)*255.0
    normalized_rgb[:,:,2]=(r/rgb_sum)*255.0
    
    #print(normalized_rgb)
    
    normalized_rgb = normalized_rgb.astype(np.uint8)
    
    #normalized_rgb=cv2.convertScaleAbs(normalized_rgb)
    return normalized_rgb
    
    
  ### DO NOT USE
  def normalizeRGB_slow(self, img):
    for row in img:
      for pixel in row:
        rgb_sum = int(pixel[0])+int(pixel[1])+int(pixel[2])
        if(rgb_sum==0):
          continue
        pixel[0] = np.uint8(round((int(pixel[0])*255)/rgb_sum))
        pixel[1] = np.uint8(round((int(pixel[1])*255)/rgb_sum))
        pixel[2] = np.uint8(round((int(pixel[2])*255)/rgb_sum))
        
        


if __name__ == '__main__':
  joint_angles()
  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting Down")
