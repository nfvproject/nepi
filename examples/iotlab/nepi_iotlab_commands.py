#!/usr/bin/env python
from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceAction, ResourceState

# Create the EC
#ec = ExperimentController(exp_id = "")
ec = ExperimentController()

# Create and Configure the Nodes

m3_102 = ec.register_resource("IOTLABNode")
ec.set(m3_102, 'hostname', 'm3-102.grenoble.iot-lab.info')
ec.set(m3_102, 'username', "saintmar")
ec.set(m3_102, 'password', "xxxx")

# Create and Configure the Application
#stop_app = ec.register_resource("IOTLABApplication")
#ec.set(stop_app, 'command', "stop")

update_app = ec.register_resource("IOTLABApplication")
ec.set(update_app, 'command', 'update')
ec.set(update_app, 'firmware_path', "~/Firmware/serial_echo.elf")

#start_app = ec.register_resource("IOTLABApplication")
#ec.set(start_app, 'command', "start")

#eset_app = ec.register_resource("IOTLABApplication")
#ec.set(reset_app, 'command', "reset")

# Connection
ec.register_connection(update_app, m3_102)
#ec.register_connection(stop_app, m3_2)

# Deploy
ec.deploy()

#ec.register_condition(app1_guid, ResourceAction.START, app2_guid, ResourceState.STARTED, time = "5s")
ec.register_condition(update_app, ResourceAction.STOP, update_app, ResourceState.STARTED, "2s")

ec.wait_finished([update_app])

#print ec.trace(update_app, "stdout")

# Stop Experiment
ec.shutdown()
