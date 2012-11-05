
def deploy(ec_weakref, xml):
    from neco.util.parser import XMLParser    

    # parse xml and build topology graph
    parser = XMLParser()
    box = parser.from_xml(xml)

    # instantiate resource boxes
    

    # allocate physical resources
    # configure physical resources
    # allocate virtual resources
    # configure virtual resources
    # allocate software resources
    # configure software resources
    # schedule application start/stop


