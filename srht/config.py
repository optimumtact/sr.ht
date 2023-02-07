import logging
import os
from dotenv import load_dotenv
load_dotenv()

# we also try the os environ
_cfg = lambda k: os.getenv(k)
_cfgi = lambda k: int(_cfg(k))

logger = logging.getLogger(_cfg("domain"))
logger.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sh.setFormatter(formatter)

logger.addHandler(sh)

# scss logger
logging.getLogger("scss").addHandler(sh)

