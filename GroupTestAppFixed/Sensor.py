# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp
import random

# riaps:keep_import:end

class Sensor(Component):

# riaps:keep_constr:begin
    def __init__(self, value):
        super(Sensor, self).__init__()
        if value == 0.0: 
            self.myValue = (10.0 * random.random()) - 5.0
        else:
            self.myValue = value
# riaps:keep_constr:end
	



# riaps:keep_clock:begin
    def on_clock(self):
        now = self.clock.recv_pyobj()   # Receive time (as float)
        # self.logger.info('on_clock():%s',msg)
        msg = (now,self.myValue)        # Send (timestamp,value) 
        self.sensorReady.send_pyobj(msg)
# riaps:keep_clock:end

# riaps:keep_impl:begin

# riaps:keep_impl:end