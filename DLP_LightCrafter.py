from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript import TriggerableDevice, LabscriptError, set_passed_properties
import numpy as np

@labscript_device
class DLP_LightCrafter(TriggerableDevice):
    allowed_children = []
    description = "DLP lightcrafter DMD"
    @set_passed_properties(
        property_names = {
            "connection_table_properties":["com_port"]})
    def __init__(self, name, parent_device,connection, com_port, **kwargs):
        self.BLACS_connection = com_port
        TriggerableDevice.__init__(self, name, parent_device,connection, **kwargs)


    def trigger(self, t, duration):
        self.trigger_device.trigger(t, duration)

    def generate_code(self, hdf5_file):
        """just need to save the parameters of interest
        Here are there are no parameters that actually matter
        since all parameters are passed from runmanager
        we will just create a snippet for now"""
        data_array = np.zeros(1)
        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('static_values', data = data_array)

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

class DMDFunction(object):
    def func(self, **kwargs):
        pass
    def func_names(self):
        args  = inspect.getargspec(self.func)[0]
        return sorted([i for i in args if i != 'inverse'])

def draw_circle(x0, y0, radius, inverse = False):
    x, y = np.mgrid[:684,:608]
    circle = ((x-x0)/1.75)**2 + (y-y0)**2 < radius**2
    ans = np.ones((684,608))
    ans[circle] = 0
    if not inverse:
        return ans
    if inverse:
        return np.abs(ans-1)

class CircleFunction(DMDFunction):
    def __init__(self):
        self.func = draw_circle

    def __repr__(self):
        _str = """
        draw a circle
        """
        return _str

@BLACS_tab
class DLP_LightCrafterTab(DeviceTab):
    def initialise_GUI(self):
        self.base_units = 'pixels'
        self.base_min = 0
        self.base_step = 1
        self.base_max = 684
        self.base_decimals = 0
        self.device = self.settings['connection_table'].find_by_name(self.device_name)
        self.func = CircleFunction()
        ao_prop = {}
        for i in self.func.func_names():
            ao_prop[i] = {'base_unit':self.base_units,
                                   'min':self.base_min,
                                   'max':self.base_max,
                                   'step':self.base_step,
                                   'decimals':self.base_decimals
                                  }

        #create output objects
        self.create_analog_outputs(ao_prop)
        dds_widgets, ao_widgets, do_widgets = self.auto_create_widgets()
        self.auto_place_widgets(("DLP LightCrafter", ao_widgets))
        self.create_plot_widget()
        self.com_port = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)

        self.supports_remote_value_check(False)
        self.supports_smart_programming(True)

    def _update_plot(self):
        param_dict = self.get_front_panel_values()
        self._image = self.func.func(**param_dict)
        self.plot_widget.setImage(self._image, autoLevels=True)

    def create_plot_widget(self):
        self.plot_widget = pg.ImageView()
        self._update_plot()
        button = QPushButton('Plot')
        button1 = QPushButton('Update')
        text = QLabel(str(self.func))
        self.get_tab_layout().addWidget(button)
        self.get_tab_layout().addWidget(button1)
        button.clicked.connect(self._update_plot)
        button1.clicked.connect(self._program_manual_button)
        self.get_tab_layout().addWidget(self.plot_widget)
        self.get_tab_layout().addWidget(text)

    @define_state(MODE_MANUAL,True,delete_stale_states=True)
    def _program_manual_button(self, *args):
        self._update_plot()
        results = yield(self.queue_work(self._primary_worker,'program_manual_button',self._last_programmed_values))

    def initialise_workers(self):
        self.create_worker("main_worker", DLP_LightCrafterWorker, {"com_port": self.com_port})
        self.primary_worker = 'main_worker'


@BLACS_worker
class DLP_LightCrafterWorker(Worker):
    def init(self):
        self.response_timeout = 45
        global visa; import visa
        global h5py; import labscript_utils.h5_lock, h5py
        global display_bitmap; from dlplc_interface.lightcrafter import display_bitmap
        global imsave; from scipy.misc import imsave

        self.func = CircleFunction()


    def _program_image(self, values):
        """evaluate funciton over values and send to DMD"""
        image = self.func.func(**values)
        save_path = r'C:\Users\spinorbec\Documents\DMDTESTING\todmd.bmp'
        imsave(save_path, image)
        success = display_bitmap(save_path)

    def program_manual_button(self, values):
        self._program_image(values)

    def check_remote_values(self):
        pass

    def program_manual(self, values):
        print("nothing to do here")

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        """get values from file and reprogram device
        if not same as initial values """
        with h5py.File(h5file, 'r') as f:
            attrs = dict(f['globals'].attrs)
        values = {k:float(v) for k,v in attrs.iteritems() if k in initial_values.keys()}
        if values != initial_values or fresh:
            #program here
            self._program_image(values)

        return values

    def transition_to_manual(self):
        return True

    def abort_buffered(self):
        return True

    def abort_transition_to_buffered(self):
        return True

    def shutdown(self):
        self.connection.close()
