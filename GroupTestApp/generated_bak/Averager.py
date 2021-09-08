# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import time

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
        self.graph = {}
        self.thresh = 6
        self.reqRec = []
        self.newGrp = {}
# riaps:keep_toplinkmgrinit:end
    

# riaps:keep_handleactivate:begin
    def handleActivate(self):
# riaps:keep_handleactivate:end
# riaps:keep_toplinkmgrjoin:begin
        for grp in self.send_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
        for grp in self.recv_grp:
            self.joined[grp] = self.joinGroup('TopLinkGrp',grp)
        if any(g.isLeader() for gname, g in self.joined.items()):
            self.joined['leader_grp'] = self.joinGroup('TopLinkLeaderGrp','leader_grp')
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
        pass
# riaps:keep_display:end

# riaps:keep_update:begin
    def on_update(self):
        pass
# riaps:keep_update:end

# riaps:keep_impl:begin

    def findMinGrp(self, grpList):
        memberInfo = {}
        for grp in grpList:
            if grp in self.joined:
                memberInfo[grp]['size'] = self.joined['grp'].groupSize()
        return min(memberInfo, key=memberInfo.get())
    
    def sendInfo(self, content):
        for gname in self.recv_grp:
            self.joined[gname].send_pyobj('toplink',content)
            
    def handleTopo(self, content):
        if content['grp'] in self.send_grp:
            length = content['length'] + 1
            if content['id'] in self.graph:
                if length < self.graph[content['id']]['length']:
                    self.graph[content['id']]['length'] = length
                    self.graph[content['id']]['grp'] = content['grp']
            else:
                self.graph[content['id']]={'length' : length , 'grp' : content['grp']}
                content['length'] = length
                self.sendInfo(content)
        else:
            self.logger.info('discarding received toplink info')
            
    def handleUpdate(self, content):
        if content['length'] < self.thresh - 1:
            content['length'] += 1
            self.joined[self.send_grp].send_pyobj('group_update', content)
            
        elif content['length'] == self.thresh - 1:
            content['length'] += 1
            content['grp'] = self.send_grp
            self.joined[self.send_grp].send_pyobj('group_update', content)
            
        else:
            if content['id'] == self.id and content['grp'] != '':
                if content['req'] not in self.reqRec:
                    self.reqRec.append(content['req'])
                    self.recv_grp.append(content['grp'])
                    self.joined[content['grp']]= self.joinGroup('TopLinkGrp',content['grp'])
                    new_content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp}
                    self.sendInfo(new_content)
                    
    def handleJoinReq(self, content):
        if content['grp_type'] == 'recv_grp':
            content['grp'] = self.send_grp[0]
            content['size'] = self.joined[self.send_grp[0]].groupSize()
            self.joined['leader_grp'].send_pyobj('join_rep', content)
            
        elif content['grp_type'] == 'send_grp':
            min_group = findMinGrp(self.recv_grp)
            content['grp'] = min_group
            content['size'] = self.joined[min_group].groupSize()
            self.joined['leader_grp'].send_pyobj('join_rep', content)
            
    def handleJoinRep(self, content):
        if content['req'] == self.id:
            self.newGrp[content['grp']] = content
        responses = {grp:entry['size'] for grp, entry in self.newGrp.items() if entry['grp_type'] == content['grp_type']}
        if len(responses) == self.joined['leader_grp'].groupSize() - 1:
            min_grp = min(responses, key=responses.get())
            if content['grp_type'] == 'recv_grp':
                self.recv_grp.append(min_grp)
                self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
            if content['grp_type'] == 'send_grp':
                self.send_grp = [min_grp]
                self.joined[min_grp]= self.joinGroup('TopLinkGrp', min_grp)
            new_content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp}
            self.sendInfo(new_content)
            for grp in responses:
                self.newGrp.pop(grp)
    
    def on_discoverPeers(self):
        sig = self.discoverPeers.recv_pyobj()
        content = {'id' : self.id, 'length' : 0, 'grp' : self.send_grp}
        self.sendInfo(content)
        
    def on_groupUpdate(self):
        sig = self.groupUpdate.recv_pyobj()
        for node, path_to_node in self.graph.items():
            if path_to_node['length'] > self.thresh:
                content = {'req': self.id, 'id' : node, 'length' : 0, 'grp': ''}
                self.joined[self.send_grp].send_pyobj('group_update', content)
                

    def appAlgorithm(self):
        pass
    
    def handleGroupMessage(self, _group):
        msg = _group.recv_pyobj()
        if _group in self.recv_grp:
            type, content = msg
            if type == 'toplink':
                self.handleTopo(content)
            if type == 'group_update':
                self.handleUpdate(content)
            if type == 'app':
                self.appAlgorithm()
        if _group == 'leader_grp':
            type, content = msg
            if type == 'join_req':
                self.handleJoinReq(content)
            if type == 'join_rep':
                self.handleJoinRep(content)
                
    def handleMemberLeft(self, group, memberId):
        if group.groupSize() == 2:
            if group in self.send_grp:
                grp_type = 'send_grp'
            if group in self.recv_grp:
                grp_type = 'recv_grp'
            content = {'req' : self.id, 'grp': '', 'grp_type': grp_type}
            if group.isLeader():
                self.joined['leader_grp'].send_pyobj('join_req', content)
            else:
                if 'leader_grp' not in self.joined:
                    self.joined['leader_grp']= self.joinGroup('TopLinkLeaderGrp','leader_grp')
                    time.sleep(0.1)
                self.joined['leader_grp'].send_pyobj('join_req', content)

# riaps:keep_impl:end