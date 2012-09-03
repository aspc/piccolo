import piccolo.log
import piccolo.config
from piccolo.shell import flags_to_mode, ugo_mode, exists
from piccolo import db
import os, stat, logging, sys
from piccolo import sites, users, databases

"""
Really just serves to set things up (initialize database, etc.)
"""

VERSION = (0, 1)
logger = logging.getLogger(__name__)

if not exists(piccolo.config.DATABASE):
    db.Base.metadata.create_all(db.sqlite_db)
    os.chmod(piccolo.config.DATABASE, flags_to_mode("u=rw"))

# Test security settings
mode_checks = [
    (piccolo.config.DATA_DIR, "u=rwx,g=rx"),
    (piccolo.config.LOGGING['directory'], "u=rwx,g=rx"),
    (piccolo.config.CONFIG_PATH, "u=rw"),
    (piccolo.config.PICCOLO_SRC_DIR, "u=rwx"),
    (piccolo.config.NGINX_CONF_ROOT, "u=rwx,g=rx,o=rx"),
    (piccolo.config.DATABASE, "u=rw")
]

for path, required_flags in mode_checks:
    if not exists(path):
        logger.error("{0} is missing. Cannot start.".format(path))
        sys.exit(1)
    if ugo_mode(path) != flags_to_mode(required_flags):
        logger.warning("{0} has incorrect permissions:"
            " mode is {1:04o}, but should be {2:04o}. Running piccolo"
            " with the current permissions is a security risk!".format(path, ugo_mode(path), flags_to_mode(required_flags)))
    else:
        logger.debug("Correct permissions on {0} :]".format(path))

