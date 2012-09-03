from piccolo.users import User
from piccolo.config import DATA_DIR
import logging, subprocess
logger = logging.getLogger(__name__)

def create(args):
    logger.debug("create " + args.full_name + " as " + args.username + " from console")
    try:
        User.create(args.username, args.full_name, args.email, suppress_welcome=args.no_email, fake_create=args.fake_create)
    except User.BadName, why:
        logger.error(why)
    except User.Exists:
        logger.exception("{0} could not be created".format(args.username))

def delete(args):
    logger.debug("Delete {0}".format(args.username))
    try:
        User.delete(args.username)
    except User.DoesNotExist:
        logger.exception("There is no user named {0}".format(args.username))
