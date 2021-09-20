# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
import grouptestapp_capnp

# riaps:keep_import:end

class Sensor(Component):

# riaps:keep_constr:begin
    def __init__(self, value):
        super(Sensor, self).__init__()
# riaps:keep_constr:end
	



# riaps:keep_clock:begin
    def on_clock(self):
        pass
# riaps:keep_clock:end

# riaps:keep_impl:begin

# riaps:keep_impl:end