#!/usr/bin/env python3

import rospy
import numpy as np
from std_msgs.msg import String
from std_msgs.msg import Float64
from std_msgs.msg import Float64MultiArray
from sensor_msgs.msg import JointState

class robot_control:

    def __init__(self):
        rospy.init_node('robot_control', anonymous=True)
        rate = rospy.Rate(30) # 30hz
        self.joints = []
        self.target_position = []
        self.base_joint_location = []
        # initialize publishers to send joint angles to the robot
        self.joint1_pub = rospy.Publisher("/robot/joint1_position_controller/command", Float64, queue_size=10)
        self.joint2_pub = rospy.Publisher("/robot/joint2_position_controller/command", Float64, queue_size=10)
        self.joint3_pub = rospy.Publisher("/robot/joint3_position_controller/command", Float64, queue_size=10)
        self.joint4_pub = rospy.Publisher("/robot/joint4_position_controller/command", Float64, queue_size=10)
        
        # publish end effector Forward Kinematics results
        self.fk_results_pub = rospy.Publisher("/forward_kinematics_result", Float64MultiArray, queue_size=1)
        
        # initialize subscriber to get joint angles from robot
        # if one wants real joint states, uncomment this instead
        #self.joint_states_sub = rospy.Subscriber("/robot/joint_states", JointState,callback=self.joint_callback)
        # computer vision joint angles:
        self.joint_states_sub = rospy.Subscriber("/joint_angles", Float64MultiArray,callback=self.joint_callback)

        # target location subscriber
        #self.target_sub = rospy.Subscriber("/target/joint_states", JointState,callback=self.target_callback) # real world location
        self.target_sub = rospy.Subscriber("/target_location", Float64MultiArray,callback=self.target_callback) # computer vision result
        
        # initialize time variables
        self.start_time = rospy.get_time()
        self.time_prev = self.start_time
        self.time = None

        # other kinematics variables
        self.error_prev = np.array([0,0,0],dtype='float64')

    def joint_callback(self,data):
        # need to have fixed joint 0 before 3 angles from vision i.e. [0, data.position]
        self.joints = np.concatenate((np.array([0]),np.array(data.data)),axis=0) # update joint angles from ros subscriber
        #self.joints = np.array(data.position) # if using actual robot joint angles
    def target_callback(self,data):
        #self.target_position = np.array(data.position)
        self.target_position = np.array(data.data)
    
    def publishFKResult(self):
        fk_result_payload = Float64MultiArray()
        fk_result_payload.data = self.getEndFKPos()
        self.fk_results_pub.publish(fk_result_payload)

    def getEndFKPos(self):
        # to save space
        q = self.joints
        def s(angle):
            return np.sin(angle)
        def c(angle):
            return np.cos(angle)

        x = 3.5*(c(q[0])*s(q[2]) + s(q[0])*s(q[1])*c(q[2])) + 3*(s(q[0])*c(q[1])*s(q[3]) + c(q[3])*(c(q[0])*s(q[2]) + s(q[0])*s(q[1])*c(q[2])))
        y = 3.5*(s(q[0])*s(q[2]) - c(q[0])*s(q[1])*c(q[2])) + 3*(c(q[3])*( s(q[0])*s(q[2]) - c(q[0])*s(q[1])*c(q[2]) ) - c(q[0])*c(q[1])*s(q[3]))
        z = 3.5*c(q[1])*c(q[2]) + 3*(c(q[1])*c(q[2])*c(q[3]) - s(q[1])*s(q[3])) + 2.5
        return np.array([x,y,z])

    def getJacobian(self):

        # to save space:
        q = self.joints
        def s(angle):
            return np.sin(angle)
        def c(angle):
            return np.cos(angle)
        
        # get partial derivatives:
        dx_dq0 = 3.5*(-s(q[2])*s(q[0]) + s(q[1])*c(q[2])*c(q[0])) + 3*(c(q[1])*s(q[3])*c(q[0]) + c(q[3])*(-s(q[2])*s(q[0]) + s(q[1])*c(q[2])*c(q[0])))
        dx_dq1 = 3.5*(s(q[0])*c(q[2])*c(q[1])) + 3*(-s(q[0])*s(q[3])*s(q[1]) + c(q[3])*s(q[0])*c(q[2])*c(q[1]))
        dx_dq2 = 3.5*(c(q[0])*c(q[3]) - s(q[0])*s(q[1])*s(q[2])) + 3*c(q[3])*(c(q[0])*c(q[2]) - s(q[0])*s(q[1])*s(q[2]))
        dx_dq3 = 3*(s(q[0])*c(q[1])*c(q[3]) - s(q[3])*(c(q[0])*s(q[2]) + s(q[0])*c(q[2])*s(q[1])))

        dy_dq0 = 3.5*(s(q[2])*c(q[0]) + s(q[1])*c(q[2])*s(q[0])) + 3*(c(q[3])*( s(q[2])*c(q[0]) + s(q[1])*c(q[2])*s(q[0]) ) + c(q[1])*s(q[3])*s(q[0]))
        dy_dq1 = -3.5*c(q[0])*c(q[2])*c(q[1]) + 3*(-c(q[3])*c(q[0])*c(q[2])*c(q[1]) + c(q[0])*s(q[3])*s(q[1]))
        dy_dq2 = 3.5*(s(q[0])*c(q[2]) + c(q[0])*s(q[1])*s(q[2])) + 3*c(q[3])*( s(q[0])*c(q[2]) + c(q[0])*s(q[1])*s(q[2]) )
        dy_dq3 = 3*(-s(q[3])*( s(q[0])*s(q[2]) - c(q[0])*c(q[2])*s(q[1])) - c(q[0])*c(q[1])*c(q[3]))

        dz_dq0 = 0
        dz_dq1 = 3*(-s(q[1])*c(q[2])*c(q[3]) - c(q[1])*s(q[3])) - 3.5*s(q[1])*c(q[2])
        dz_dq2 = -3.5*c(q[1])*s(q[2]) - 3*c(q[1])*s(q[2])*c(q[3])
        dz_dq3 = 3*(-c(q[1])*c(q[2])*s(q[3]) - s(q[1])*c(q[3]))

        # use partial derivatives to return the Jacobian
        return np.array([[dx_dq0,dx_dq1,dx_dq2,dx_dq3],
                         [dy_dq0,dy_dq1,dy_dq2,dy_dq3],
                         [dz_dq0,dz_dq1,dz_dq2,dz_dq3]])

    def getClosedLoopMovement(self,target):
        # target is np.array([x,y,z])

        # get vector from end effector to the target position
        error = target - self.getEndFKPos()


        J = self.getJacobian()
        # if q0 is fixed, we should account for this in the Jacobian
        # dx,dy,dz can't be affected by change in q0, so set dx_dq0,dy_dq0,dz_dq0 to zero
        J[0,0] = 0
        J[1,0] = 0
        J[2,0] = 0
        # get pseudo-inverse of Jacobian
        J_pinv = np.linalg.pinv(J)

        # get current time and dt
        self.time = rospy.get_time() - self.start_time
        dt = self.time - self.time_prev
        self.time_prev = self.time

        # get error derivative
        de_dt = (error - self.error_prev)/dt # might need changing, see lab 3 solution


        # proportinal gain and derivative gain
        K_p = np.eye(3)*10
        K_d = np.eye(3)*0.1
        
        # desired changes in joint angles q
        dq = J_pinv @ (K_p @ error + K_d @ de_dt)
        # angular velocity of joints
        #dq = np.dot(J_pinv,(np.dot(K_p,error.T) + np.dot(K_d,de_dt.T))) 

        # note that joint 1 can go from -pi -> pi (has full 360 degree freedom)
        # need to handle this?

        #q = self.joints + dt*dq # angular position of joints
        q = self.joints + dt*dq
        #q[0] = (q[0] + np.pi)%(2*np.pi) - np.pi
        '''
        print("J: " + str(self.getJacobian()))
        print("J_pinv: " + str(J_pinv))
        print("error: " + str(error))
        print("dt: " + str(dt))
        print("de_dt: " + str(de_dt))
        print("dq: " + str(dq))
        '''
        return q

    def moveToTarget(self):

        #target = np.array([-5.0,-3.0,2.0])
        q = self.getClosedLoopMovement(self.target_position)

        joint1 = Float64()
        joint1.data = q[0]
        joint2 = Float64()
        joint2.data = q[1]
        joint3 = Float64()
        joint3.data = q[2]
        joint4 = Float64()
        joint4.data = q[3]

        # publish the new desired joint angles
        self.joint1_pub.publish(joint1)
        self.joint2_pub.publish(joint2)
        self.joint3_pub.publish(joint3)
        self.joint4_pub.publish(joint4)

        # delay before updating movement again
        # otherwise the robot starts uncontrollably shaking/dancing/flying
        rospy.sleep(0.05)
        
    def run(self):
        while not rospy.is_shutdown():
            if self.joints != [] and self.target_position != []:# and self.base_joint_location != []:
                #print(self.base_joint_location)
                self.moveToTarget()
                #self.publishFKResult()

# run the code if the node is called
if __name__ == '__main__':
  try:
    rc = robot_control()
    rc.run()
  except rospy.ROSInterruptException:
    pass


