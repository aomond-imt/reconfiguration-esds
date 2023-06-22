#!/usr/bin/env python

import random, os
from esds import RCode
from esds.plugins.power_states import *

def execute(api):
    ##### Setup node power consumption ####
    node_cons=PowerStates(api, 0) # Node consumes 0 watts when off
    comms_cons=PowerStatesComms(api)
    comms_cons.set_power("lora", 0, 0.16, 0.16)
    comms_cons.set_power("nbiot", 0, 0.65, 0.65)
    ##### Start node implementation #####
    seed=0
    if(os.path.isfile("seed.txt")):
        with open('seed.txt') as f:
            seed = int(f.readline())
    rand=random.Random(api.node_id+seed) # Fixed seed for reproducibility
    api.turn_off() # Node off on start    
    for hour in range(0,24): # Simulate for 24 hours
        api.wait(rand.randint(0,3600-api.args["uptime"])) # Stay off for a random duration during current hour
        api.turn_on()
        node_cons.set_power(0.4) # Node consumes 0.4W on idle
        wakeat=api.read("clock") # Read current simulated time
        wakeuntil=wakeat+api.args["uptime"]
        # Send/Receive during uptime:
        while api.read("clock") < wakeuntil:
            if api.args["type"] == "sender":
                api.sendt(api.args["wireless"],"my data",api.args["datasize"],None, wakeuntil-api.read("clock"))
            else:
                code, data=api.receivet(api.args["wireless"],wakeuntil-api.read("clock"))
                if code == RCode.SUCCESS:
                    api.log("Receive "+data)
        api.log("Was up for {}s".format(api.read("clock")-wakeat)) # Just report effective uptime duration (must always be 180s)
        # Turn off the node and wait for the next hour:
        node_cons.set_power(0) # Node consumes 0 watts when off
        api.turn_off()
        api.wait(3600*(hour+1)-api.read("clock")) # Wait for the next hour
    ##### Report energy consumed by the nodes at the end of the simulation #####
    node_cons.report_energy()
    comms_cons.report_energy()



