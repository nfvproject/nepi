#!/usr/bin/env python
# -*- coding: utf-8 -*-

# PROTOCOL MESSAGES
CREATE      = 0
CONNECT     = 1
SET         = 2
GET         = 3
START       = 4
STOP        = 5
STATUS      = 6
ENABLE_TRACE    = 7
DISABLE_TRACE   = 8
GET_TRACE   = 9
ADD_ADDRES  = 10
ADD_ROUTE   = 11
SHUTDOWN    = 12

tesbed_messages = {
        CREATE: "CREATE,%d,%d,%s,[%s]", # CREATE,time,guid,factory_id,parameters
        CONNECT: "CONNECT,%d,%d,%d,%d,%s,%s", # CONNECT,time,object1_guid,object2_guid,connector1_id,connector2_id
        SET: "%d,%d,%s,%s", # SET,time,guid,name,value
        GET: "%d,%d,%s", # GET,time,guid,name
        START: "%d,%d", # START,time,guid
        STOP: "%d,%d", # STOP,time,guid
        STATUS: "%d,%d", # STATUS,time,guid
        ENABLE_TRACE: "%d,%d,%s", # ENABLE_TRACE,time,guid,trace_id
        DISABLE_TRACE: "%d,%d,%s", # DISABLE_TRACE,time,guid,trace_id
        GET_TRACE: "%d,%d,%s", # GET_TRACE,time,guid,trace_id
        ADD_ADDRESSES: "%d,%d", # ADD_ADDRESSES,time,guid
        ADD_ROUTE: "%d,%d", # ADD_ROUTE,time,guid
        SHUTDOWN: "%d,%d" , # SHUTDOWN,time.guid
    }

