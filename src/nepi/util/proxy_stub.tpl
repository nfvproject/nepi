def %(methname)s(%(self)s, %(argdefs)s):
    msg = BaseProxy._make_message(
        argtypes,
        argencoders,
        %(command)d,
        %(methname)r,
        %(classname)r,
        %(args)s)
    %(self)s._client.send_msg(msg)
    reply = %(self)s._client.read_reply()
    rv = BaseProxy._parse_reply(
        rvtype,
        %(methname)r,
        %(classname)r,
        reply)
    return rv

