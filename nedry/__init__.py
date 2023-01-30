import logging
logging.basicConfig(format="[%(asctime)s][%(levelname)s][%(module)s:%(lineno)s]: %(message)s")

__author__ = "Erik Nyquist"
__license__ = "Apache 2.0"
__version__ = "2.3.2"
__maintainer__ = "Erik Nyquist"
__email__ = "eknyquist@gmail.com"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info(f"nedry {__version__}")
