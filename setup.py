# Setup logging
import logging, sys
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S",
    stream=sys.stdout)

import database
from database.setup import Setup

if __name__ == '__main__':
	setup = Setup("hgv_check.db")
	setup.run()