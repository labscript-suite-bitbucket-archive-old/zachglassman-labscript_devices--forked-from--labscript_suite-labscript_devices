from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript import TriggerableDevice, LabscriptError, set_passed_properties
import numpy as np

@labscript_device
class Agilent33521A(TriggerableDevice):
    allowed_children=[]
    description = "Agilent33521A arbitrary function generator"

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

def exp_ramp(t,
             initial_value,
             ramp_up_time,
             exp_init_value,
             first_t_c,
             second_ramp_amp_frac,
             second_t_c,
             time_to_final,
             final_value,
             ramp_start,
             ramp_value,
             ramp_dur,
             final_extent):
    # get amplitudes for ramps
    first_exp = np.exp(-time_to_final / first_t_c)
    second_exp = np.exp(-time_to_final / second_t_c)
    a = first_exp + second_exp * \
        second_ramp_amp_frac / (1 - second_ramp_amp_frac)
    b = 1 / (1 - second_ramp_amp_frac) - a
    amp_first_ramp = (exp_init_value - final_value) / \
        b  # amplitude of first ramp
    amp_sec_ramp = amp_first_ramp * \
        second_ramp_amp_frac / (1 - second_ramp_amp_frac)
    first_ramp = amp_first_ramp * np.exp(-t / first_t_c)
    second_ramp = amp_sec_ramp * np.exp(-t / second_t_c)
    return first_ramp + second_ramp + exp_init_value - amp_first_ramp - amp_sec_ramp


def ramp_func(t,
              initial_value,
              ramp_up_time,
              exp_init_value,
              first_t_c,
              second_ramp_amp_frac,
              second_t_c,
              time_to_final,
              final_value,
              ramp_start,
              ramp_value,
              ramp_dur,
              final_extent):
    # first ramp up
    ramp_up = np.linspace(initial_value, exp_init_value, 10)  # + np.linspace()
    ramp_up_t = np.linspace(0, ramp_up_time, 10)
    # now do the exponential ramp from ramp_up_time to ramp_start
    tf = ramp_start
    ramp_t = np.linspace(ramp_up_time, ramp_start, 10000)
    ramp = exp_ramp(ramp_t - ramp_up_time, initial_value,
                    ramp_up_time,
                    exp_init_value,
                    first_t_c,
                    second_ramp_amp_frac,
                    second_t_c,
                    time_to_final,
                    final_value,
                    ramp_start,
                    ramp_value,
                    ramp_dur,
                    final_extent)
    final_ramp = np.linspace(final_value, ramp_value, 1000)
    final_ramp_t = np.linspace(ramp_start, ramp_start + ramp_dur, 1000)
    # now stack answers
    ans = np.hstack((ramp_up, ramp, final_ramp, np.zeros(10) + ramp_value))
    t_ans = np.hstack((ramp_up_t, ramp_t,
                       final_ramp_t,
                       np.linspace(ramp_start + ramp_dur, np.max(t), 10)))
    return np.interp(t, t_ans, ans)

class OldRamp(RampFunction):
    def func(self,
            t,
            initial_value,
            ramp_up_time,
            exp_init_value,
            first_t_c,
            second_ramp_amp_frac,
            second_t_c,
            time_to_final,
            final_value,
            ramp_start,
            ramp_value,
            ramp_dur,
            final_extent):
        try:
            return ramp_func(t,
                initial_value,
                ramp_up_time,
                exp_init_value,
                first_t_c,
                second_ramp_amp_frac,
                second_t_c,
                time_to_final,
                final_value,
                ramp_start,
                ramp_value,
                ramp_dur,
                final_extent )
        except:
            return np.zeros(t.shape)

    def __repr__(self):
        _str = """
        1. Linear ramp from
        """
        return _str

@BLACS_tab
class Agilent33521ATab(DeviceTab):
    def initialise_GUI(self):
        self.base_units = 'V'
        self.base_min = -5
        self.base_step = 0.01
        self.base_max = 5
        self.base_decimals = 2
        self.device = self.settings['connection_table'].find_by_name(self.device_name)
        self.ramp = OldRamp()
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
        self.supports_smart_programming(True)

    def _update_plot(self):
        self.plot_widget.clear()
        param_dict = self.get_front_panel_values()
        self._y = self.ramp.func(self._x,**param_dict)
        self.plot_widget.plot(x=self._x,y=self._y)

    def create_plot_widget(self):
        self._x = np.linspace(0,10,1000)
        self.plot_widget = pg.PlotWidget()
        self._update_plot()
        button = QPushButton('Plot')
        button1 = QPushButton('Update')
        text = QLabel(str(self.ramp))
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
        self.ramp = OldRamp()
        inst_params = self.inst.query(u'*LRN?').split(';')
        #now make into nested dictionary
        params = {}
        for i in inst_params:
            key, value = i.split()
            try:
                params[key] = float(value)
            except:
                params[key] = value
        self._srat = params[u':SOUR1:FUNC:ARB:SRAT']

    def _program_waveform(self, values):
        n_samps = values['final_extent'] * self._srat
        t = np.linspace(0, values['final_extent'], n_samps)
        ramp = self.ramp.func(t, **values)
        min_ramp = np.min(ramp)
        max_ramp = np.max(ramp)
        vpp = 1
        ramp = (vpp)/(max_ramp-min_ramp)*(ramp - max_ramp) + vpp
        ramp = ramp/vpp
        self.inst.write(u'VOLT {:.3f}'.format(max_ramp))
        #write out waveform
        data_string = ''.join(',' + '{:.3f}'.format(i) for i in ramp)
        self.inst.write(u'DATA:VOL:CLEAR')
        self.inst.write(u'DATA:ARB DIP' + data_string)
        self.inst.write(u'FUNC:ARB DIP')

    def program_manual_button(self, values):
        self._program_waveform(values)

    def check_remote_values(self):
        return self.inst.query(u'*LRN?').split(';')

    def program_manual(self, values):
        print("nothing to do here")

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        """get values from file and reprogram device
        if not same as initial values """
        with h5py.File(h5file, 'r') as f:
            attrs = dict(f['globals'].attrs)
        values = {k:float(v) for k,v in attrs.iteritems() if k in initial_values.keys()}
        if values != initial_values or fresh:
            self._program_waveform(values)

        return values

    def transition_to_manual(self):
        return True

    def abort_buffered(self):
        return True

    def abort_transition_to_buffered(self):
        return True

    def shutdown(self):
        self.connection.close()
