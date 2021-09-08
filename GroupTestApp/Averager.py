# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import time
import netifaces
from datetime import datetime

# riaps:keep_import:end

class Averager(Component):

# riaps:keep_constr:begin
    def __init__(self, Ts, send_grp, recv_grp):
        super(Averager, self).__init__()
# riaps:keep_constr:end
# riaps:keep_toplinkmgrinit:begin
        self.joined = {}
        self.send_grp = send_grp.split(',')
        self.recv_grp = recv_grp.split(',')
        self.id = None
        self.ip = None
        self.iface = 'eth1'
        self.graph = {}
        self.thresh = 3
        self.reqRec = []
        self.newGrp = {}
# riaps:keep_toplinkmgrinit:end
	

# riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.id = self.getUUID()
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
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
        pass
# riaps:keep_sensorready:end

# riaps:keep_display:begin
    def on_display(self):
        now = self.display.recv_pyobj()
# riaps:keep_display:end

# riaps:keep_update:begin
    def on_update(self):
        now = self.update.recv_pyobj()
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
        return min(memberInfo, key=memberInfo.get())
    
    def sendInfo(self, content):
        for gname in self.recv_grp:
            self.logger.info('sending to %s' %(gname))
            self.joined[gname].send_pyobj(('toplink',content))
            
    def handleTopo(self, content):
        if content['grp'] in self.send_grp:
            now = self.curr_time()
            self.logger.info('[%s:%s] received message %s' % (self.ip, now, str(content)))
            length = content['length'] + 1
            if content['id'] in self.graph:
                if length < self.graph[content['id']]['length']:
                    self.graph[content['id']]['length'] = length
                    self.graph[content['id']]['grp'] = content['grp']
                    self.logger.info('[%s:%s] updated path %s' %(self.ip,now,str(self.graph)))
            else:
                self.graph[content['id']]={'length' : length , 'grp' : content['grp']}
                content['length'] = length
                self.sendInfo(content)
        else:
            self.logger.info('discarding received toplink info')
            
    def handleUpdate(self, content):
        now = self.curr_time()
        if content['length'] < self.thresh - 1:
            content['length'] += 1
            self.logger.info('[%s:%s] forwarding group update message %s' (self.ip,now,str(content)))
            self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
            
        elif content['length'] == self.thresh - 1:
            content['length'] += 1
            content['grp'] = self.send_grp[0]
            self.logger.info('[%s:%s] forwarding group update message %s' %(self.ip,now, str(content)))
            self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
            
        else:
            if content['id'] == self.id and content['grp'] != '':
                if content['req'] not in self.reqRec:
                    self.reqRec.append(content['req'])
                    self.recv_grp.append(content['grp'])
                    self.logger.info('[%s:%s] updating group %s' %(self.ip,now, content['grp']))
                    self.joined[content['grp']]= self.joinGroup('TopLinkGrp',content['grp'])
                    self.logger.info('[%s:%s] initiating discover peers' %(self.ip,now))
                    new_content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp}
                    self.sendInfo(new_content)
                    
    def handleJoinReq(self, content):
        now = self.curr_time()
        if content['grp_type'] == 'recv_grp':
            content['grp'] = self.send_grp[0]
            content['size'] = self.joined[self.send_grp[0]].groupSize()
            self.logger.info('[%s:%s] sending join response %s' % (self.ip,now,str(content)))
            self.joined['leader_grp'].send_pyobj(('join_rep', content))
            
        elif content['grp_type'] == 'send_grp':
            min_group = findMinGrp(self.recv_grp)
            content['grp'] = min_group
            content['size'] = self.joined[min_group].groupSize()
            self.logger.info('[%s:%s] sending join response %s' % (self.ip,now,str(content)))
            self.joined['leader_grp'].send_pyobj(('join_rep', content))
            
    def handleJoinRep(self, content):
        if content['req'] == self.id:
            now = self.curr_time()
            self.logger.info('[%s:%s] received join response %s' % (self.ip, now, str(content)))
            self.newGrp[content['grp']] = content
            responses = {grp:entry['size'] for grp, entry in self.newGrp.items() if entry['grp_type'] == content['grp_type']}
            if len(responses) == self.joined['leader_grp'].groupSize() - 1:
                self.logger.info('[%s:%s] received all join responses' %(self.ip,now))
                min_grp = min(responses, key=responses.get())
                if content['grp_type'] == 'recv_grp':
                    self.recv_grp.append(min_grp)
                    self.logger.info('[%s:%s] joining group %s as %s' %(self.ip,now,min_grp,content['grp_type']))
                    self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
                if content['grp_type'] == 'send_grp':
                    self.send_grp = [min_grp]
                    self.logger.info('[%s:%s] joining group %s as %s' %(self.ip,now,min_grp,content['grp_type']))
                    self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
                self.logger.info('[%s:%s] initiating discover peers' %(self.ip,now))
                new_content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp[0]}
                self.sendInfo(new_content)
                for grp in responses:
                    self.newGrp.pop(grp)
    
    def on_discoverPeers(self):
        sig = self.discoverPeers.recv_pyobj()
        now = self.curr_time()
        self.logger.info('[%s:%s] started peer discovery' %(self.ip, now))
        content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp[0]}
        self.sendInfo(content)
        
    def on_groupUpdate(self):
        sig = self.groupUpdate.recv_pyobj()
        now = self.curr_time()
        self.logger.info('[%s:%s] started group update' %(self.ip, now))
        for node, path_to_node in self.graph.items():
            if path_to_node['length'] > self.thresh:
                self.logger.info('[%s:%s] sending group update to %s' % (self.ip,now,node))
                content = {'req': self.id, 'id' : node, 'length' : 0, 'grp': ''}
                self.joined[self.send_grp[0]].send_pyobj(('group_update', content))
                

    def appAlgorithm(self):
        pass
    
    def handleGroupMessage(self, _group):
        msg = _group.recv_pyobj()
        self.logger.info('received msg %s from group %s' %(msg,_group.getGroupName()))
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
                
        elif _group in self.recv_grp:
            type, content = msg
            if type == 'app':
                self.appAlgorithm()
                
        else:
            type, content = msg
            if type == 'toplink':
                self.handleTopo(content)
            if type == 'group_update':
                self.handleUpdate(content)
                
    def handleMemberLeft(self, group, memberId):
        now = self.curr_time()
        for gname, grp in self.joined.items():
            if grp == group:
                group = gname
                break
        self.logger.info('[%s:%s] group member left group %s' % (self.ip,now, memberId, group))
        if group.groupSize() == 2:
            if group in self.send_grp:
                grp_type = 'send_grp'
            if group in self.recv_grp:
                grp_type = 'recv_grp'
            content = {'req' : self.id, 'grp': '', 'grp_type': grp_type}
            if group.isLeader():
                self.logger.info('[%s:%s send join request to leader_grp %s]' %(self.ip,now,str(content)))
                self.joined['leader_grp'].send_pyobj(('join_req', content))
            else:
                if 'leader_grp' not in self.joined:
                    self.joined['leader_grp']= self.joinGroup('TopLinkLeaderGrp','leader_grp')
                    self.logger.info('[%s:%s] joining leader_grp' % (self.ip,now))
                    time.sleep(0.1)
                self.logger.info('[%s:%s send join request to leader_grp %s]' %(self.ip,now,str(content)))
                self.joined['leader_grp'].send_pyobj(('join_req', content))
                
    def handleMemberJoined(self, group, memberId):
        self.logger.info('member joined group %s, size = %d' %(group.getGroupName(), group.groupSize()))

# riaps:keep_impl:end