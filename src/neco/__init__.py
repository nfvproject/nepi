import logging
import os

LOGLEVEL = os.environ.get("NEPI_LOGLEVEL", "DEBUG").upper()
LOGLEVEL = getattr(logging, LOGLEVEL)
FORMAT = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
logging.basicConfig(format = FORMAT, level = LOGLEVEL)

