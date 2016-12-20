from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript import IntermediateDevice,AnalogOut,StaticAnalogQuantity, Device, LabscriptError, set_passed_properties
import numpy as np


class Agilent33521A(IntermediateDevice):
    allowed_children=[]
    description = "Agilent33521A function generator"

    @set_passed_properties(property_names = {"connection_table_properties":["com_port",'p','b','a','r']})
    def __init__(self, name, parent_device, com_port):
        IntermediateDevice.__init__(self, name, parent_device)
        self.BLACS_connection = com_port

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
import sys
if 'PySide' in sys.modules.copy():
    from PySide.QtCore import *
    from PySide.QtGui import *
else:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
from blacs.device_base_class import DeviceTab
import pyqtgraph as pg

import inspect
class RampFunction(object):
    def func(self,x, **kwargs):
        """write function as a function of x or t"""
        pass

    def __repr__(self):
        """override with representation"""
        return ''

    def func_names(self):
        args  = inspect.getargspec(self.func)[0]
        return sorted([i for i in args if i not in ['self','x','t']])

class ExpRamp(RampFunction):
    def func(self,x, amp, tau, off):
        return amp*np.exp(-x/tau)+off

    def __repr__(self):
        return 'amp*exp(-t/tau) + off'

@BLACS_tab
class Agilent33521ATab(DeviceTab):
    def initialise_GUI(self):
        self.base_units = 'V'
        self.base_min = -5
        self.base_step = 0.01
        self.base_max = 5
        self.base_decimals = 2
        self.device = self.settings['connection_table'].find_by_name(self.device_name)
        self.ramp = ExpRamp()
        ao_prop = {}
        for i in self.ramp.func_names():
            ao_prop[i] = {'base_unit':self.base_units,
                                   'min':self.base_min,
                                   'max':self.base_max,
                                   'step':self.base_step,
                                   'decimals':self.base_decimals
                                  }

        #create output objects
        self.create_analog_outputs(ao_prop)
        dds_widgets, ao_widgets, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("Agilent 33521A", ao_widgets))
        self.create_plot_widget()
        self.com_port = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)

        self.supports_remote_value_check(False)
        self.supports_smart_programming(False)

    def _update_plot(self):
        self.plot_widget.clear()
        param_dict = self.get_front_panel_values()
        self._y = self.ramp.func(self._x,**param_dict)
        self.plot_widget.plot(x=self._x,y=self._y)

    def create_plot_widget(self):
        self._x = np.linspace(0,5,1000)
        self.plot_widget = pg.PlotWidget()
        self._update_plot()
        button = QPushButton('Plot')
        text = QLabel(str(self.ramp))
        self.get_tab_layout().addWidget(text)
        self.get_tab_layout().addWidget(button)
        button.clicked.connect(self._update_plot)
        self.get_tab_layout().addWidget(self.plot_widget)

    def initialise_workers(self):
        self.create_worker("main_worker", Agilent33521AWorker, {"com_port": self.com_port})
        self.primary_worker = 'main_worker'



@BLACS_worker
class Agilent33521AWorker(Worker):
    def init(self):
        self.response_timeout = 45
        global visa; import visa
        global h5py; import labscript_utils.h5_lock, h5py

        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(self.com_port)

    def check_remote_values(self):
        return self.inst.query(u'*LRN?').split(';')

    def program_manual(self, values):
        pass


    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        print "transitionsing"
        #pull values for h5file, compute and 

    def transition_to_manual(self):
        return True

    def abort_buffered(self):
        return True

    def abort_transition_to_buffered(self):
        return True

    def shutdown(self):
        self.connection.close()
