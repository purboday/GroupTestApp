# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import time
import netifaces

# riaps:keep_import:end

class Logger(Component):

# riaps:keep_constr:begin
    def __init__(self, iface):
        super(Logger, self).__init__()
        self.logger.info('started Logger')
        self.globalStats = []
        self.iface = iface
        self.ip = ''
            
# riaps:keep_constr:end

# riaps:keep_getlog:begin
    def on_getLog(self):
        msg = self.getLog.recv_pyobj()
        self.logger.info('received log data')
        self.globalStats.extend(msg)
# riaps:keep_getlog:end

# riaps:keep_update:begin
    def on_update(self):
        msg = self.update.recv_pyobj()
        if len(self.globalStats) > 0:
            self.writeLog.send_pyobj(self.globalStats)
            self.logger.info('sent to DataWriter')
            self.globalStats = []
        
# riaps:keep_update:end

# riaps:keep_impl:begin
    def handleActivate(self):
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
        

# riaps:keep_impl:end