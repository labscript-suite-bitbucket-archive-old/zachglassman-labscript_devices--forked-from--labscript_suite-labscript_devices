#####################################################################
#                                                                   #
# /NI_PCI_6713.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

from labscript import LabscriptError, AnalogOut, IntermediateDevice, config
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker, runviewer_parser
import labscript_devices.NIBoard as parent

import numpy as np
import labscript_utils.h5_lock, h5py
import labscript_utils.properties
from random import randint
@labscript_device
class NI_PCI_6713(parent.NIBoard):
    description = 'NI-PCI-6713'
    n_analogs = 8
    n_digitals = 0
    n_analog_ins = 0
    clock_limit = 500e3
    digital_dtype = np.uint8

    def _generate_code(self, hdf5_file):
        IntermediateDevice.generate_code(self, hdf5_file)
        analogs = {}
        digitals = {}
        inputs = {}
        for device in self.child_devices:
            if isinstance(device,AnalogOut):
                analogs[device.connection] = device
            elif isinstance(device,DigitalOut):
                digitals[device.connection] = device
            elif isinstance(device,AnalogIn):
                inputs[device.connection] = device
            else:
                raise Exception('Got unexpected device.')

        clockline = self.parent_device
        pseudoclock = clockline.parent_device
        times = pseudoclock.times[clockline]

        analog_connections = analogs.keys()
        analog_connections.sort()
        analog_out_attrs = []
        #KLUGGEEEE
        #get lenth of one output connection
        output_length = len(analogs[analog_connections[0]].raw_output)
        analog_out_table = np.empty((output_length,len(analogs)), dtype=np.float32)
        #analog_out_table = np.empty((len(times),len(analogs)), dtype=np.float32)
        for i, connection in enumerate(analog_connections):
            output = analogs[connection]
            if any(output.raw_output > 10 )  or any(output.raw_output < -10 ):
                # Bounds checking:
                raise LabscriptError('%s %s '%(output.description, output.name) +
                                  'can only have values between -10 and 10 Volts, ' +
                                  'the limit imposed by %s.'%self.name)
            analog_out_table[:,i] = output.raw_output
            analog_out_attrs.append(self.MAX_name +'/'+connection)
        """
        if self.name == 'ni_card_B':
            #kluge to double every cell
            new_out_table = np.empty((output_length*2, len(analogs)), dtype=np.float32)
            for i, row in enumerate(analog_out_table):
                new_out_table[2*i] = row
                new_out_table[2*i+1] = row
            analog_out_table = new_out_table
        """
        #now we know that the last column should be randomized for one of the
        #CHOOSE CHANNEL HERE
        if self.name == 'ni_card_B':
            random_column = 0 #randint(0,6)
        else:
            # CHANGE THIS FOR CARD A
            random_column = 1

        #analog_out_table[:,-1] = analog_out_table[:,random_column]
        input_connections = inputs.keys()
        input_connections.sort()
        input_attrs = []
        acquisitions = []
        for connection in input_connections:
            input_attrs.append(self.MAX_name+'/'+connection)
            for acq in inputs[connection].acquisitions:
                acquisitions.append((connection,acq['label'],acq['start_time'],acq['end_time'],acq['wait_label'],acq['scale_factor'],acq['units']))
        # The 'a256' dtype below limits the string fields to 256
        # characters. Can't imagine this would be an issue, but to not
        # specify the string length (using dtype=str) causes the strings
        # to all come out empty.
        acquisitions_table_dtypes = [('connection','a256'), ('label','a256'), ('start',float),
                                     ('stop',float), ('wait label','a256'),('scale factor',float), ('units','a256')]
        acquisition_table= np.empty(len(acquisitions), dtype=acquisitions_table_dtypes)
        for i, acq in enumerate(acquisitions):
            acquisition_table[i] = acq
        digital_out_table = []
        if digitals:
            digital_out_table = self.convert_bools_to_bytes(digitals.values())
        grp = self.init_device_group(hdf5_file)
        if all(analog_out_table.shape): # Both dimensions must be nonzero
            grp.create_dataset('ANALOG_OUTS',compression=config.compression,data=analog_out_table)
            self.set_property('analog_out_channels', ', '.join(analog_out_attrs), location='device_properties')
        if len(digital_out_table): # Table must be non empty
            grp.create_dataset('DIGITAL_OUTS',compression=config.compression,data=digital_out_table)
            self.set_property('digital_lines', '/'.join((self.MAX_name,'port0','line0:%d'%(self.n_digitals-1))), location='device_properties')
        if len(acquisition_table): # Table must be non empty
            grp.create_dataset('ACQUISITIONS',compression=config.compression,data=acquisition_table)
            self.set_property('analog_in_channels', ', '.join(input_attrs), location='device_properties')
        # TODO: move this to decorator (requires ability to set positional args with @set_passed_properties)
        self.set_property('clock_terminal', self.clock_terminal, location='connection_table_properties')

    def generate_code(self, hdf5_file):
        #parent.NIBoard.generate_code(self, hdf5_file)
        self._generate_code(hdf5_file)

        # count the number of analog outputs in use
        analog_count = 0
        for child in self.child_devices:
            if isinstance(child,AnalogOut):
                analog_count += 1


        # Check that there is a multiple of two outputs
        if analog_count % 2:
            raise LabscriptError('%s %s must have an even numer of analog outputs '%(self.description, self.name) +
                             'in order to guarantee an even total number of samples, which is a limitation of the DAQmx library. ' +
                             'Please add a dummy analog output device or remove an output you\'re not using, so that there are an even number of analog outputs. Sorry, this is annoying I know :).')


from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED
from blacs.device_base_class import DeviceTab


@BLACS_tab
class NI_PCI_6713Tab(DeviceTab):
    def initialise_GUI(self):
        # Capabilities
        self.num_AO = 8
        self.num_DO = 0
        self.base_units = 'V'
        self.base_min = -10.0
        self.base_max = 10.0
        self.base_step = 0.1
        self.base_decimals = 3

        # Create the AO output objects
        ao_prop = {}
        for i in range(self.num_AO):
            ao_prop['ao%d'%i] = {'base_unit':self.base_units,
                                 'min':self.base_min,
                                 'max':self.base_max,
                                 'step':self.base_step,
                                 'decimals':self.base_decimals
                                }

        do_prop = {}
        for i in range(self.num_DO):
            do_prop['port0/line%d'%i] = {}


        # Create the output objects
        self.create_analog_outputs(ao_prop)
        # Create widgets for analog outputs only
        dds_widgets,ao_widgets,do_widgets = self.auto_create_widgets()

        # now create the digital output objects
        self.create_digital_outputs(do_prop)
        # manually create the digital output widgets so they are grouped separately
        do_widgets = self.create_digital_widgets(do_prop)

        def do_sort(channel):
            flag = channel.replace('port0/line','')
            flag = int(flag)
            return '%02d'%(flag)


        # and auto place the widgets in the UI
        self.auto_place_widgets(("Analog Outputs",ao_widgets),("Digital Outputs",do_widgets,do_sort))

        # Store the Measurement and Automation Explorer (MAX) name
        self.MAX_name = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)

        # Create and set the primary worker
        self.create_worker("main_worker",NiPCI6713Worker,{'MAX_name':self.MAX_name, 'limits': [self.base_min,self.base_max], 'num_AO':self.num_AO, 'num_DO': self.num_DO})
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(False)


@BLACS_worker
class NiPCI6713Worker(Worker):
    def init(self):
        exec 'from PyDAQmx import Task' in globals()
        exec 'from PyDAQmx.DAQmxConstants import *' in globals()
        exec 'from PyDAQmx.DAQmxTypes import *' in globals()
        global pylab; import pylab
        global h5py; import labscript_utils.h5_lock, h5py
        global numpy; import numpy
        global time; import time

        # Create task
        self.ao_task = Task()
        self.ao_read = int32()
        self.ao_data = numpy.zeros((self.num_AO,), dtype=numpy.float64)

        # Create DO task:
        self.do_task = Task()
        self.do_read = int32()
        self.do_data = numpy.zeros(self.num_DO, dtype=numpy.uint8)

        self.setup_static_channels()

        #DAQmx Start Code
        self.ao_task.StartTask()
        self.do_task.StartTask()

    def setup_static_channels(self):
        #setup AO channels
        for i in range(self.num_AO):
            self.ao_task.CreateAOVoltageChan(self.MAX_name+"/ao%d"%i,"",self.limits[0],self.limits[1],DAQmx_Val_Volts,None)
        #setup DO ports
        self.do_task.CreateDOChan(self.MAX_name+"/port0/line0:7","",DAQmx_Val_ChanForAllLines)

    def shutdown(self):
        self.ao_task.StopTask()
        self.ao_task.ClearTask()
        self.do_task.StopTask()
        self.do_task.ClearTask()

    def program_manual(self,front_panel_values):
        for i in range(self.num_AO):
            self.ao_data[i] = front_panel_values['ao%d'%i]
        self.ao_task.WriteAnalogF64(1,True,1,DAQmx_Val_GroupByChannel,self.ao_data,byref(self.ao_read),None)

        for i in range(self.num_DO):
            self.do_data[i] = front_panel_values['port0/line%d'%i]
        self.do_task.WriteDigitalLines(1,True,1,DAQmx_Val_GroupByChannel,self.do_data,byref(self.do_read),None)
        # TODO: Return coerced/quantised values
        return {}

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        # TODO: Coerce/quantise these correctly before returning them
        self.initial_values = initial_values

        with h5py.File(h5file,'r') as hdf5_file:
            group = hdf5_file['devices/'][device_name]
            device_properties = labscript_utils.properties.get(hdf5_file, device_name, 'device_properties')
            connection_table_properties = labscript_utils.properties.get(hdf5_file, device_name, 'connection_table_properties')
            clock_terminal = connection_table_properties['clock_terminal']
            h5_data = group.get('ANALOG_OUTS')
            if h5_data:
                self.buffered_using_analog = True
                ao_channels = device_properties['analog_out_channels']
                # We use all but the last sample (which is identical to the
                # second last sample) in order to ensure there is one more
                # clock tick than there are samples. The 6713 requires this
                # to determine that the task has completed.
                ao_data = pylab.array(h5_data,dtype=float64)[:-1,:]
            else:
                self.buffered_using_analog = False

            h5_data = group.get('DIGITAL_OUTS')
            if h5_data:
                self.buffered_using_digital = True
                do_channels = device_properties['digital_lines']
                do_bitfield = numpy.array(h5_data,dtype=numpy.uint32)
            else:
                self.buffered_using_digital = False

            final_values = {}
            # We must do digital first, so as to make sure the manual mode task is stopped, or reprogrammed, by the time we setup the AO task
            # this is because the clock_terminal PFI must be freed!
            if self.buffered_using_digital:
                # Expand each bitfield int into self.num_DO
                # (8) individual ones and zeros:
                do_write_data = numpy.zeros((do_bitfield.shape[0],self.num_DO),dtype=numpy.uint8)
                for i in range(self.num_DO):
                    do_write_data[:,i] = (do_bitfield & (1 << i)) >> i

                self.do_task.StopTask()
                self.do_task.ClearTask()
                self.do_task = Task()
                self.do_read = int32()

                self.do_task.CreateDOChan(do_channels,"",DAQmx_Val_ChanPerLine)
                self.do_task.CfgSampClkTiming(clock_terminal,1000000,DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,do_bitfield.shape[0])
                self.do_task.WriteDigitalLines(do_bitfield.shape[0],False,10.0,DAQmx_Val_GroupByScanNumber,do_write_data,self.do_read,None)
                self.do_task.StartTask()

                for i in range(self.num_DO):
                    final_values['port0/line%d'%i] = do_write_data[-1,i]
            else:
                # We still have to stop the task to make the
                # clock flag available for buffered analog output, or the wait monitor:
                self.do_task.StopTask()
                self.do_task.ClearTask()

            if self.buffered_using_analog:
                self.ao_task.StopTask()
                self.ao_task.ClearTask()
                self.ao_task = Task()
                ao_read = int32()

                self.ao_task.CreateAOVoltageChan(ao_channels,"",-10.0,10.0,DAQmx_Val_Volts,None)
                self.ao_task.CfgSampClkTiming(clock_terminal,1000000,DAQmx_Val_Rising,DAQmx_Val_FiniteSamps, ao_data.shape[0])
                self.ao_task.WriteAnalogF64(ao_data.shape[0],False,10.0,DAQmx_Val_GroupByScanNumber, ao_data,ao_read,None)
                self.ao_task.StartTask()

                # Final values here are a dictionary of values, keyed by channel:
                channel_list = [channel.split('/')[1] for channel in ao_channels.split(', ')]
                final_values = {channel: value for channel, value in zip(channel_list, ao_data[-1,:])}

            else:
                # we should probabaly still stop the task (this makes it easier to setup the task later)
                self.ao_task.StopTask()
                self.ao_task.ClearTask()

        return final_values

    def transition_to_manual(self,abort=False):
        # if aborting, don't call StopTask since this throws an
        # error if the task hasn't actually finished!

        if self.buffered_using_analog:
            if not abort:
                try:
                    self.ao_task.StopTask()
                except:
                    #sleep for five seconds and try again
                    time.sleep(5)
                    self.ao_task.StopTask()
            self.ao_task.ClearTask()
        if self.buffered_using_digital:
            if not abort:
                self.do_task.StopTask()
            self.do_task.ClearTask()

        self.ao_task = Task()
        self.do_task = Task()
        self.setup_static_channels()
        self.ao_task.StartTask()
        self.do_task.StartTask()
        if abort:
            # Reprogram the initial states:
            self.program_manual(self.initial_values)

        return True

    def abort_transition_to_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)

    def abort_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)


@runviewer_parser
class RunviewerClass(parent.RunviewerClass):
    num_digitals = 0
