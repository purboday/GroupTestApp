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
        self.ipList = ['10.42.0.116','10.42.0.118','10.42.0.119','10.42.0.120','10.42.0.121','10.42.0.123']
        self.currNbr = self.shuffleNbr(self.ipList,4)
        self.msgCount = 0
        self.bcast = 0
        self.netStats = []
        self.ageList = {nbr : 0 for nbr in self.currNbr}
        self.currView = self.shuffleNbr(self.currNbr,4)
        self.waiting = ''
        self.otherId = []
        
# riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.id = self.getUUID()
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
        self.logger.info("[%s:%s]" %(self.ip, self.id))
# riaps:keep_handleactivate:end

    def shuffleNbr(self,sourceList,count):
        temp_list = [ip for ip in sourceList if ip !=self.ip]
        sampledList=random.sample(temp_list,count)
        return sampledList

    def on_sensorReady(self):
        msg = self.sensorReady.recv_pyobj() # Receive (timestamp,value)
        self.logger.info("on_sensorReady():%s" % str(msg[1]))
        self.sensorTime, self.sensorValue = msg
        self.sensorUpdate = True

    def on_nodeReady(self):
        msg = self.nodeReady.recv_pyobj()  # Receive (actorID,timestamp,value)
        # self.logger.info("on_otherReady():%s",str(msg[2]))
        otherId,otherRoute,otherTimestamp,otherIP,otherValue = msg
        if otherId != self.uuid:
            if otherIP in self.currView:
                self.dataValues[otherId] = otherValue
                self.msgCount += 1
                if otherIP in self.ageList:
                    self.ageList[otherIP] += 1
                else:
                    self.ageList[otherIP] = 1
                if otherId not in self.otherId:
                    self.otherId.append(otherId)
                for nodeId in otherRoute:
                    if nodeId not in self.otherId:
                        self.otherId.append(nodeId)
            
    
    def on_update(self):
        msg = self.update.recv_pyobj()      # Receive timestamp 
        # self.logger.info("on_update():%s",str(msg))
        if self.sensorUpdate:
            self.ownValue = self.sensorValue
            self.sensorUpdate = False
            self.otherId=[]
        if len(self.dataValues) != 0:
            sum = 0.0
            for value in self.dataValues.values():
                sum += (self.ownValue - value)
            der = sum / self.Ts
            self.ownValue -= der
        now = time.time()
        self.bcast += 1
        msg = (self.uuid, self.otherId,now,self.ip,self.ownValue)
        self.thisReady.send_pyobj(msg)
        self.currView = self.shuffleNbr(self.currNbr, 3)        

    def on_display(self):
        msg = self.display.recv_pyobj()
        rel = len(self.otherId)/len(self.ipList)
        self.logger.info('broadcast: %d, curr_val: %f, rel: %f' %(self.bcast, self.ownValue, rel))
        self.netStats.append({'ip': self.ip, 'round': self.bcast, 'value': self.ownValue, 'rel': rel})
        
    def on_shuffle(self):
        now = self.shuffle.recv_pyobj()
        if self.waiting != '':
            self.logger.info('suspected failure of %s' %(self.waiting))
            sourceList = [ip for ip in self.ipList if ip != self.waiting]
            self.currNbr = self.shuffleNbr(sourceList,4)
            temp_ageList = {}
            for ip in self.currNbr:
                if ip in self.ageList:
                    temp_ageList[ip]=self.ageList[ip]
                else:
                    temp_ageList[ip]=0
            self.ageList=temp_ageList
            
        for ip, age in self.ageList.items():
            self.ageList[ip] += 1
        candt=list(self.ageList.keys())[0]
        for ip, age in self.ageList.items():    
            if age < self.ageList[candt]:
                candt = ip
        sample = self.currView + [self.ip]
        self.shuffleReq.send_pyobj(('req',candt,sample))
        self.waiting=candt
        
    def on_shuffleRep(self):
        msg = self.shuffleRep.recv_pyobj()
        type, dst, sample = msg
        if dst == self.ip:
            sourceList = self.currNbr+sample
            self.currNbr=self.shuffleNbr(sourceList, 4)
            temp_ageList = {}
            for ip in self.currNbr:
                if ip in self.ageList:
                    temp_ageList[ip]=self.ageList[ip]
                else:
                    temp_ageList[ip]=0
            self.ageList=temp_ageList
            if type == 'req':
                candt=list(self.ageList.keys())[0]
                for ip, age in self.ageList.items():    
                    if age < self.ageList[candt]:
                        candt = ip
                sample = self.currView + [self.ip]
                self.shuffleReq.send_pyobj(('rep',candt,sample))
            if type == 'rep':
                if dst == self.waiting:
                    self.waiting = ''
                
        
        
# riaps:keep_display:begin
    def on_logUpdate(self):
        now = self.logUpdate.recv_pyobj()
        self.logger.info('sending logging data')
        self.sendLog.send_pyobj(self.netStats)
        self.netStats=[]
# riaps:keep_display:end
        
    def on_discoverPeers(self):
        sig = self.discoverPeers.recv_pyobj()
        self.logger.info('on discover peers')
        
    def on_groupUpdate(self):
        sig = self.groupUpdate.recv_pyobj()
        self.logger.info('on group update')
        
    def handlePeerStateChange(self,state,uuid):
        self.logger.info("peer %s is %s" % (uuid,state))
        
    def __destroy__(self):
        self.logger.info("terminated")
        
        
