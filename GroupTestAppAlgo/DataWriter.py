# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import time
from datetime import datetime
import csv
import os
import netifaces
# riaps:keep_import:end

class DataWriter(Component):

# riaps:keep_constr:begin
    def __init__(self, filename, iface):
        super(DataWriter, self).__init__()
        self.logger.info("started DataWriter")
        self.iface = iface
        self.ip = ''
        self.first = True
        self.filename = filename
# riaps:keep_constr:end

# riaps:keep_writelog:begin
    def writetoFile(self, globalStats):
        self.logger.info('writing %d records to file' % (len(globalStats)))
        if not os.path.exists(os.path.dirname(self.filename)):
            try:
                os.makedirs(os.path.dirname(self.filename), exist_ok = True)
            except PermissionError as exc:
                self.logger.error('unable to create directory : permission denied')
        
        with open(self.filename, 'a', newline='') as csvfile:
            fieldnames = list(globalStats[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if self.first:
                writer.writeheader()
                self.first = False
            writer.writerows(globalStats)
        
            
    def on_writeLog(self):
        msg = self.writeLog.recv_pyobj()
        globalStats = msg
        self.writetoFile(globalStats)

# riaps:keep_writelog:end

# riaps:keep_impl:begin
    def handleActivate(self):
        self.ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']

# riaps:keep_impl:end