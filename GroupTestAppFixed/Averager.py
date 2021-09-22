# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import time
import netifaces
from datetime import datetime
import uuid
import os

# riaps:keep_import:end

class Averager(Component):

# riaps:keep_constr:begin
    def __init__(self, Ts, iface, send_grp, recv_grp):
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
        self.nic = 'up'
        self.bcast = 0
        self.netStats = []
        self.otherId = []
# riaps:keep_constr:end
# riaps:keep_toplinkmgrinit:begin
        self.joined = {}
        self.send_grp = send_grp.split(',')
        self.recv_grp = recv_grp.split(',')
# riaps:keep_toplinkmgrinit:end
	

# riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.id = self.getUUID()
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
        self.logger.info("[%s:%s]" %(self.ip, self.id))
# riaps:keep_handleactivate:end
# riaps:keep_toplinkmgrjoin:begin
        for grp in self.send_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
            self.logger.info('joined group %s' %(grp))
        for grp in self.recv_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
            self.logger.info('joined group %s' %(grp))
# riaps:keep_toplinkmgrjoin:end

    def curr_time(self):
        current_time = datetime.now()
        dt_string = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return dt_string


# riaps:keep_nodeready:begin
    def on_nodeReady(self):
        pass
# riaps:keep_nodeready:end

# riaps:keep_sensorready:begin
    def on_sensorReady(self):
        msg = self.sensorReady.recv_pyobj() # Receive (timestamp,value)
        self.logger.info("on_sensorReady():%s" % str(msg[1]))
        self.sensorTime, self.sensorValue = msg
        self.sensorUpdate = True
# riaps:keep_sensorready:end

# riaps:keep_display:begin
    def on_display(self):
        now = self.display.recv_pyobj()
        rel = len(self.otherId)/6
        self.logger.info('broadcast: %d, curr_val: %f, rel: %f' %(self.bcast, self.ownValue, rel))
        self.netStats.append({'ip': self.ip, 'round': self.bcast, 'value': self.ownValue, 'rel': rel})
# riaps:keep_display:end

# riaps:keep_display:begin
    def on_logUpdate(self):
        now = self.logUpdate.recv_pyobj()
        self.logger.info('sending logging data')
        self.sendLog.send_pyobj(self.netStats)
        self.netStats=[]
# riaps:keep_display:end

# riaps:keep_update:begin
    def on_update(self):
        now = self.update.recv_pyobj()
        self.bcast += 1
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
        msg = (self.uuid,self.otherId,now,self.ownValue)
        for grp in self.send_grp:
            self.joined[grp].send_pyobj(('app',msg))
        
# riaps:keep_update:end

# riaps:keep_impl:begin

 
    
    def on_discoverPeers(self):
        sig = self.discoverPeers.recv_pyobj()
        self.logger.info('on discover peers')
        
    def on_groupUpdate(self):
        sig = self.groupUpdate.recv_pyobj()
        self.logger.info('on group update')
                

    def appAlgorithm(self, content):
        otherId,otherRoute,otherTimestamp,otherValue = content
        if otherId != self.uuid:
            self.dataValues[otherId] = otherValue
            if otherId not in self.otherId:
                self.otherId.append(otherId)
            for nodeId in otherRoute:
                if nodeId not in self.otherId:
                    self.otherId.append(nodeId)
    
    def handleGroupMessage(self, _group):
        msg = _group.recv_pyobj()
        #self.logger.info('received msg %s from group %s' %(msg,_group.getGroupName()))
        for gname, grp in self.joined.items():
            if grp == _group:
                _group = gname
                break
                
        if _group in self.recv_grp:
            type, content = msg
            if type == 'app':
                self.appAlgorithm(content)
            
                
                
    def handleMemberLeft(self, group, memberId):
        now = self.curr_time()
        gname = group.getGroupName().split('.')[1]
        if group.isLeader():
            self.logger.info('I am the leader!')
        self.logger.info('[%s:%s] group member left group %s, size %d' % (self.ip,now, gname, group.groupSize()))

                
    def handleMemberJoined(self, group, memberId):
        self.logger.info('member %s joined group %s, size = %d' %(memberId,group.getGroupName(), group.groupSize()))
        
    def handleLeaderElected(self, group, leaderId):
        if group.isLeader():
            if 'leader_grp' not in self.joined:
                self.joined['leader_grp'] = self.joinGroup('TopLinkLeaderGrp','leader_grp')
                self.logger.info('joined group leader_grp')
                
    def handleNICStateChange(self, state):
        self.nic = state
        self.logger.info('nic state changed %s' %(state))

# riaps:keep_impl:end