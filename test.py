# We setup logging first to ensure it applies to every module
import logging, sys
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S",
    stream=sys.stdout)

import database
from database.setup import Setup
setup = Setup("hgv_check.db")
setup.run()