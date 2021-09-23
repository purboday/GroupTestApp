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
        self.bcast = 0
        self.ready = False
        self.netStats = []
        self.otherId = []
# riaps:keep_constr:end
# riaps:keep_toplinkmgrinit:begin
        self.joined = {}
        self.send_grp = send_grp.split(',')
        self.recv_grp = recv_grp.split(',')
        self.id = None
        self.ip = None
        self.iface = iface
        self.graph = {}
        self.thresh = 3
        self.reqRec = []
        self.initDiscoReq = []
        self.initJoinReq = []
        self.newGrp = {}
        self.GrpAns = {}
        self.nic = 'up'
# riaps:keep_toplinkmgrinit:end
	

# riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.id = self.getUUID()
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
        self.logger.info("[%s:%s]" %(self.ip, self.id))
        self.graph[self.id]={'length' : 0 , 'grp' : 'NA', 'order': 0}
# riaps:keep_handleactivate:end
# riaps:keep_toplinkmgrjoin:begin
        for grp in self.send_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
            self.logger.info('joined group %s' %(grp))
        for grp in self.recv_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
            self.logger.info('joined group %s' %(grp))
        if any(g.isLeader() for gname, g in self.joined.items()):
            self.joined['leader_grp'] = self.joinGroup('TopLinkLeaderGrp','leader_grp')
            self.logger.info('joined group leader_grp')
# riaps:keep_toplinkmgrjoin:end


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
        if self.ready:
            rel = len(self.otherId)/6
            self.logger.info('broadcast: %d, curr_val: %f, rel: %f' %(self.bcast, self.ownValue, rel))
            self.netStats.append({'ip': self.ip, 'round': self.bcast, 'value': self.ownValue, 'rel': rel})
# riaps:keep_display:end

# riaps:keep_display:begin
    def on_logUpdate(self):
        now = self.logUpdate.recv_pyobj()
        if self.ready:
            self.logger.info('sending logging data')
            self.sendLog.send_pyobj(self.netStats)
            self.netStats=[]
# riaps:keep_display:end

# riaps:keep_update:begin
    def on_update(self):
        now = self.update.recv_pyobj()
        if self.ready:
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

    def curr_time(self):
        current_time = datetime.now()
        dt_string = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return dt_string

    def findMinGrp(self, grpList):
        memberInfo = {}
        for grp in grpList:
            if grp in self.joined:
                memberInfo[grp]['size'] = self.joined['grp'].groupSize()
        return min(memberInfo, key=memberInfo.get)
    
    def sendInfo(self, content):
        for gname in self.recv_grp:
            self.logger.info('sending to %s' %(gname))
            content['grp']=gname
            self.joined[gname].send_pyobj(('toplink',content))
            
    def handleTopo(self, content):
        if content['grp'] in self.send_grp:
            now = self.curr_time()
            self.logger.info('[%s:%s] received message %s' % (self.ip, now, str(content)))
            length = content['length'] + 1
            if content['id'] in self.graph:
                if self.graph[content['id']]['order'] == content['order']:
                    if length < self.graph[content['id']]['length']:
                        self.graph[content['id']]['length'] = length
                        self.graph[content['id']]['grp'] = content['grp']
                        content['length'] = length
                        self.logger.info('[%s:%s] updated path %s' %(self.ip,now,str(self.graph)))
                        self.sendInfo(content)
                elif self.graph[content['id']]['order'] < content['order']:
                    self.graph[content['id']]['length'] = length
                    self.graph[content['id']]['grp'] = content['grp']
                    self.graph[content['id']]['order'] = content['order']
                    content['length'] = length
                    self.logger.info('[%s:%s] updated path %s' %(self.ip,now,str(self.graph)))
                    self.sendInfo(content)
            else:
                self.graph[content['id']]={'length' : length , 'grp' : content['grp'], 'order': content['order']}
                self.logger.info('[%s:%s] updated path %s' %(self.ip,now,str(self.graph)))
                content['length'] = length
                self.sendInfo(content)
        else:
            self.logger.info('discarding received toplink info')
                    
    def handleUpdate(self, content):
           now = self.curr_time()
           if content['req'] != self.id:
               if content['length'] +1 < self.thresh - 1 and content['grp']=='':
                   if self.id not in content['seq']:
                       content['length'] += 1
                       content['seq'].append(self.id)
                       self.logger.info('[%s:%s] forwarding group update message %s' %(self.ip,now,str(content)))
                       self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
                   
               elif content['length']+1 == self.thresh - 1 and content['grp']=='':
                   if self.id not in content['seq']:
                       content['length'] += 1
                       content['seq'].append(self.id)
                       content['grp'] = self.send_grp[0]
                       self.logger.info('[%s:%s] forwarding group update message %s' %(self.ip,now, str(content)))
                       self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
                   
               elif content['length'] == self.thresh-1 and content['grp']!='' and content['id']!= self.id:
                   if self.id not in content['seq']:
                       content['seq'].append(self.id)
                       self.logger.info('[%s:%s] forwarding group update message %s' %(self.ip,now, str(content)))
                       self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
                   
               else:
                   if content['id'] == self.id and content['grp'] != '':
                       if content['req'] not in self.reqRec:
                           self.reqRec.append(content['req'])
                           self.recv_grp.append(content['grp'])
                           self.logger.info('[%s:%s] updating group %s' %(self.ip,now, content['grp']))
                           self.joined[content['grp']]= self.joinGroup('TopLinkGrp',content['grp'])
                           new_content = {'id' : self.id, 'length' : 0, 'grp' : content['grp'], 'order': self.graph[self.id]['order']}
                           self.initDiscoReq.append(new_content)
                   
    def handleJoinReq(self, content):
        if content['req'] != self.id:
            now = self.curr_time()
            if content['grp_type'] == 'recv_grp':
                content['grp'] = self.send_grp[0]
                content['size'] = self.joined[self.send_grp[0]].groupSize()
                content['rep'] = self.id
                self.logger.info('[%s:%s] sending join response %s' % (self.ip,now,str(content)))
                self.joined['leader_grp'].send_pyobj(('join_rep', content))
                
            elif content['grp_type'] == 'send_grp':
                min_group = self.findMinGrp(self.recv_grp)
                content['grp'] = min_group
                content['size'] = self.joined[min_group].groupSize()
                content['rep'] = self.id
                self.logger.info('[%s:%s] sending join response %s' % (self.ip,now,str(content)))
                self.joined['leader_grp'].send_pyobj(('join_rep', content))
            
    def handleJoinRep(self, content):
        if content['req'] == self.id:
            now = self.curr_time()
            self.logger.info('[%s:%s] received join response %s, groupSize %d' % (self.ip, now, str(content), self.joined['leader_grp'].groupSize()))
            self.newGrp[content['rep']] = content
            responses = {entry['grp']:entry['size'] for rep, entry in self.newGrp.items() if entry['grp_type'] == content['grp_type']}
            if len(responses) == self.joined['leader_grp'].groupSize() - 2:
                self.logger.info('[%s:%s] received all join responses' %(self.ip,now))
                min_grp = min(responses, key=responses.get)
                if content['grp_type'] == 'recv_grp':
                    self.recv_grp.append(min_grp)
                    self.logger.info('[%s:%s] joining group %s as %s' %(self.ip,now,min_grp,content['grp_type']))
                    if min_grp not in self.joined:
                        self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
                if content['grp_type'] == 'send_grp':
                    self.send_grp = [min_grp]
                    self.logger.info('[%s:%s] joining group %s as %s' %(self.ip,now,min_grp,content['grp_type']))
                    if min_grp not in self.joined:
                        self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
                self.graph[self.id]['order'] += 1
                new_content = {'id' : self.id, 'length' : 0, 'grp' : min_grp, 'order': self.graph[self.id]['order']}
                self.initDiscoReq.append(new_content)
                delKeys = []
                for req, content in self.newGrp.items():
                    if content['grp'] in responses:
                        delKeys.append(req)
                for req in delKeys:
                    self.newGrp.pop(req)
       
    def on_discoverPeers(self):
        sig = self.discoverPeers.recv_pyobj()
        now = self.curr_time()
        self.logger.info('[%s:%s] started peer discovery' %(self.ip, now))
        self.graph[self.id]['order'] += 1
        content = {'id' : self.id, 'length' : 0, 'grp' : '', 'order': self.graph[self.id]['order']}
        self.sendInfo(content)
        
    def on_groupUpdate(self):
        sig = self.groupUpdate.recv_pyobj()
        if sig == 'ready':
            self.ready = True
            self.logger.info('ready')
        else:
            now = self.curr_time()
            self.logger.info('[%s:%s] started group update' %(self.ip, now))
            for node, path_to_node in self.graph.items():
                if path_to_node['length'] > self.thresh:
                    self.logger.info('[%s:%s] sending group update to %s' % (self.ip,now,node))
                    content = {'req': self.id, 'id' : node, 'length' : 0, 'grp': '', 'seq':[]}
                    self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
                    
    def on_clearId(self):
        if self.ready:
            msg=self.clearId.recv_pyobj()
            self.otherId = []
                

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
#         self.logger.info('received msg %s from group %s' %(msg,_group.getGroupName()))
        for gname, grp in self.joined.items():
            if grp == _group:
                _group = gname
                break
        if _group == 'leader_grp':
            type, content = msg
            if type == 'join_req':
                self.handleJoinReq(content)
            if type == 'join_rep':
                self.handleJoinRep(content)
                
        if _group in self.recv_grp:
            type, content = msg
            if type == 'app':
                self.appAlgorithm(content)
            if type == 'group_update':
                self.handleUpdate(content)
            if type == 'grp_qry':
                if content['req'] != self.id:
                    content['rep'] = ''
                    self.joined[_group].send_pyobj(('grp_ans',content))
                    
            if type == 'grp_ans':
                self.handleGrpAns(content)
                
        if _group in self.send_grp:
            type, content = msg
            if type == 'toplink':
                self.handleTopo(content)
            if type =='grp_qry':
                if content['req'] != self.id:
                    content['rep'] = self.id
                    self.joined[_group].send_pyobj(('grp_ans',content))
                
    def handleGrpAns(self, content):
        if content['grp'] in self.GrpAns:
            if content['req'] not in self.GrpAns[content['grp']]:
                self.GrpAns[content['grp']].append(content)
        else:
            self.GrpAns[content['grp']]=[content]
        self.logger.info('Group size: %d, responses: %d' %(self.joined[content['grp']].groupSize(),len(self.GrpAns[content['grp']])))
        
        if set(self.recv_grp) == set(list(self.GrpAns.keys())):
            grpAnsAll = True
            for grp, cont in self.GrpAns.items():
                if any(item['req'] == self.id for item in cont):
                    if len(self.GrpAns[grp])==self.joined[grp].groupSize()-2:
                        self.logger.info('all group qry responses received for %s' %(grp))
                        grpAnsAll = grpAnsAll and True
                    else:
                        grpAnsAll = grpAnsAll and False
                else:
                    if len(self.GrpAns[grp])==self.joined[grp].groupSize()-3:
                        self.logger.info('all group qry responses received for %s' %(grp))
                        grpAnsAll = grpAnsAll and True
                    else:
                        grpAnsAll = grpAnsAll and False
                        
            if grpAnsAll:
                    
                if all(resp['rep'] == '' for resp in self.GrpAns[content['grp']]):
                    now = self.curr_time()
                    content = {'req' : self.id, 'grp': '', 'grp_type': 'recv_grp'}
                    if 'leader_grp' in self.joined:
                        self.logger.info('[%s:%s send join request to leader_grp %s]' %(self.ip,now,str(content)))
                        self.joined['leader_grp'].send_pyobj(('join_req', content))
                    else:
                        self.joined['leader_grp']= self.joinGroup('TopLinkLeaderGrp','leader_grp')
                        self.logger.info('[%s:%s] joining leader_grp' % (self.ip,now))
                        self.initJoinReq.append(content)
                    self.GrpAns={}
            else:
                delKeys = []
                for grp, cont in self.GrpAns.items():
                    if any(item['rep'] != '' for item in cont):
                        delKeys.append(grp)
                for key in delKeys:
                    self.GrpAns.pop(key)
            
                
                
    def handleMemberLeft(self, group, memberId):
        now = self.curr_time()
        gname = group.getGroupName().split('.')[1]
        if group.isLeader():
            self.logger.info('I am the leader!')
        self.logger.info('[%s:%s] group member left group %s, size %d' % (self.ip,now, gname, group.groupSize()))
        if self.nic == 'up':
            if gname in self.recv_grp:
                self.logger.info('[%s:%s] sending group query to %s' %(self.ip,now,gname))
                content = {'req' : self.id, 'grp': gname, 'grp_type': 'send_grp'}
                group.send_pyobj(('grp_qry',content))
            elif group.groupSize() == 2:
                proceed = False
                if all(self.joined[gname].groupSize()== 2 for gname in self.send_grp):
                    grp_type = 'recv_grp'
                    proceed = True
                if proceed:
                    content = {'req' : self.id, 'grp': '', 'grp_type': grp_type}
                    if 'leader_grp' in self.joined:
                        self.logger.info('[%s:%s send join request to leader_grp %s]' %(self.ip,now,str(content)))
                        self.joined['leader_grp'].send_pyobj(('join_req', content))
                    else:
                        self.joined['leader_grp']= self.joinGroup('TopLinkLeaderGrp','leader_grp')
                        self.logger.info('[%s:%s] joining leader_grp' % (self.ip,now))
                        self.initJoinReq.append(content)

                
    def handleMemberJoined(self, group, memberId):
        self.logger.info('member %s joined group %s, size = %d' %(memberId,group.getGroupName(), group.groupSize()))
        if group.groupSize() > 2:
            if group.getGroupName().split('.')[1] == 'leader_grp':
                now = self.curr_time()
                for content in self.initJoinReq:
                    self.logger.info(str(content))
                    self.logger.info('[%s:%s send join request to leader_grp %s]' %(self.ip,now,str(content)))
                    self.joined['leader_grp'].send_pyobj(('join_req', content))   
                self.initJoinReq= []
                
    
            else:
                initDiscoReq = []
                now = self.curr_time()
                for i,content in enumerate(self.initDiscoReq):
                    self.logger.info(str(content))
                    if content['grp']== group.getGroupName().split('.')[1]:
                        self.logger.info('recv_grp: %s' %(str(self.recv_grp)))
                        self.logger.info('[%s:%s] initiating discover peers' %(self.ip,now))
                        self.joined[content['grp']].send_pyobj(('toplink',content))
                    else:
                        initDiscoReq.append(content)
                    
                self.initDiscoReq = initDiscoReq
                self.logger.info(str(self.initDiscoReq))
        
    def handleLeaderElected(self, group, leaderId):
        if group.isLeader():
            if 'leader_grp' not in self.joined:
                self.joined['leader_grp'] = self.joinGroup('TopLinkLeaderGrp','leader_grp')
                self.logger.info('joined group leader_grp')
                
    def handleNICStateChange(self, state):
        self.nic = state
        self.logger.info('nic state changed %s' %(state))

# riaps:keep_impl:end