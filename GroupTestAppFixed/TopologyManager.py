# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp

# riaps:keep_import:end

class TopologyManager(Component):

# riaps:keep_constr:begin
    def __init__(self):
        super(TopologyManager, self).__init__()
        self.cmdFlag = False
# riaps:keep_constr:end

# riaps:keep_handleactivate:begin
    def handleActivate(self):
        self.trigger.setDelay(5.0)
        self.trigger.launch()
# riaps:keep_handleactivate:end	



# riaps:keep_trigger:begin
    def on_trigger(self):
        now = self.trigger.recv_pyobj()
        self.trigger.halt()
        if not self.cmdFlag:
            self.cmdFlag = True
            self.logger.info('sending discover peers message')
            self.discoverPeers.send_pyobj('start')
            self.trigger.setDelay(60.0)
            self.trigger.launch()
        else:
            self.logger.info('sending group update message')
            self.groupUpdate.send_pyobj('start')
#             self.trigger.setDelay(300.0)
#             self.cmdFlag = False
#             self.trigger.launch()
# riaps:keep_trigger:end

# riaps:keep_impl:begin

# riaps:keep_impl:end