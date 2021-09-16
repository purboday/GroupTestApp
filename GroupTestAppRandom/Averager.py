#
from riaps.run.comp import Component
import logging
import uuid
import time
import os
import netifaces
from datetime import datetime
import random

# Averager algorithm
# Continuous time update equation (for node i)
# dx_i/dt = - Sum_{j} a_{ij} (x_{i} - x_{j} 
# Discretized
# x_{i,k+1} = x_{i,k} - (1 / T_{S}) Sum_{j} a_{ij} (x_{i,k} - x_{j,k})  

class Averager(Component):
    def __init__(self,Ts,iface):
        super(Averager, self).__init__()
        self.Ts = Ts
        self.uuid = uuid.uuid4().int
        self.pid = os.getpid()
        self.dataValues = { }
        self.sensorTime = 0.0
        self.sensorValue = 0.0
        self.ownValue = 0.0
        self.sensorUpdate = False
        self.logger.info("%s - starting" % str(self.pid))
        self.id = None
        self.ip = None
        self.iface = iface
        self.ipList = ['192.168.57.1','192.168.57.2','192.168.57.3','192.168.57.4','192.168.57.5','192.168.57.6']
        self.currNbr = []
        self.msgCount = 0
        self.bcast = 0
        
    # riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.id = self.getUUID()
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
        self.logger.info("[%s:%s]" %(self.ip, self.id))
# riaps:keep_handleactivate:end

    def shuffleNbr(self):
        temp_list = [ip for ip in self.ipList if ip !=self.ip]
        sampledList=random.sample(temp_list,3)
        return sampledList

    def on_sensorReady(self):
        msg = self.sensorReady.recv_pyobj() # Receive (timestamp,value)
        self.logger.info("on_sensorReady():%s" % str(msg[1]))
        self.sensorTime, self.sensorValue = msg
        self.sensorUpdate = True

    def on_nodeReady(self):
        msg = self.nodeReady.recv_pyobj()  # Receive (actorID,timestamp,value)
        # self.logger.info("on_otherReady():%s",str(msg[2]))
        otherId,otherTimestamp,otherIP,otherValue = msg
        if otherId != self.uuid:
            if otherIP in self.currNbr:
                self.dataValues[otherId] = otherValue
                self.msgCount += 1
    
    def on_update(self):
        msg = self.update.recv_pyobj()      # Receive timestamp 
        # self.logger.info("on_update():%s",str(msg))
        if self.sensorUpdate:
            self.ownValue = self.sensorValue
            self.sensorUpdate = False
        if len(self.dataValues) != 0:
            sum = 0.0
            for value in self.dataValues.values():
                sum += (self.ownValue - value)
            der = sum / self.Ts
            self.ownValue -= der
        now = time.time()
        self.bcast += 1
        self.currNbr = self.shuffleNbr()
        msg = (self.uuid,now,self.ip,self.ownValue)
        self.thisReady.send_pyobj(msg)        

    def on_display(self):
        msg = self.display.recv_pyobj()
        self.logger.info('broadcast: %d, curr_val: %f' %(self.bcast, self.ownValue))
        
    
        
    def handlePeerStateChange(self,state,uuid):
        self.logger.info("peer %s is %s" % (uuid,state))
        
    def __destroy__(self):
        self.logger.info("terminated")
        
        
