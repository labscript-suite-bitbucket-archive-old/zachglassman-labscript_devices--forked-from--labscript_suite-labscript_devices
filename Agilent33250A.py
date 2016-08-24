from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript import IntermediateDevice,AnalogOut,StaticAnalogQuantity, Device, LabscriptError, set_passed_properties
import numpy as np


class Agilent33250A(IntermediateDevice):
    allowed_children=[AnalogOut]
    description = "Agilent33250A function generator"

    @set_passed_properties(property_names = {"connection_table_properties":["com_port",'p','b','a','r']})
    def __init__(self, name, parent_device, com_port):
        IntermediateDevice.__init__(self, name, parent_device)
        self.BLACS_connection = com_port
        p=64
        b=1080
        a=62
        r=805
        self._scale = (p*b + a)/r

    def add_device(self, device):
        Device.add_device(self, device)

    def generate_code(self, hdf5_file):
        data_dict = {}
        if len(self.child_devices) > 0:
            raise LabscriptError("only one device support")

        for dev in self.child_devices:
            ignore = dev.get_change_times()
            dev.make_timeseries([])
            dev.expand_timeseries()
            data_array = np.zeros(1)
            grp = hdf5_file.create_group('/devices/' + self.name)
            gp.create_dataset('static_values', data = data_array)


import time

from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED

from blacs.device_base_class import DeviceTab

@BLACS_tab
class Agilent33250ATab(DeviceTab):
    def initialise_GUI(self):
        self.base_units = 'GHz'
        self.base_min = 1.5
        self.base_step = 0.00001
        self.base_max = 2
        self.base_decimals = 6
        self.device = self.settings['connection_table'].find_by_name(self.device_name)
        ao_prop = {}
        ao_prop['beat_freq'] = {'base_unit':self.base_units,
                               'min':self.base_min,
                               'max':self.base_max,
                               'step':self.base_step,
                               'decimals':self.base_decimals
                              }

        #create output objects
        self.create_analog_outputs(ao_prop)
        dds_widgets, ao_widgets, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("Agilent 33250A", ao_widgets))

        self.com_port = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)

        self.supports_remote_value_check(False)
        self.supports_smart_programming(False)

    def initialise_workers(self):
        self.create_worker("main_worker", Agilent33250AWorker, {"com_port": self.com_port})
        self.primary_worker = 'main_worker'



@BLACS_worker
class Agilent33250AWorker(Worker):
    def init(self):
        self.response_timeout = 45
        global visa; import visa
        global h5py; import labscript_utils.h5_lock, h5py

        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(self.com_port)
        p=64
        b=1080
        a=62
        r=805
        self._scale = (p*b + a)/r
        #maybe put respones here?

    def check_remote_values(self):
        return self.inst.query(u'*LRN?').split(';')

    def program_manual(self, values):
        val = values['beat_freq']*1e9/ self._scale
        if val < 80e6 and val > 0:
            self.inst.write(u'APPL:sin {0}, 1,0'.format(val))
        #return self.check_remote_values()



    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        print "transitionsing"

    def transition_to_manual(self):
        return True

    def abort_buffered(self):
        return True

    def abort_transition_to_buffered(self):
        return True

    def shutdown(self):
        self.connection.close()
