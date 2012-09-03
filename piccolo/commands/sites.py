from piccolo.sites import Site, Domain #, SiteExists, BadSiteName
from piccolo.databases import Database
from piccolo.users import User
from piccolo.shell import ShellActionFailed
from piccolo import db
import logging, sys
logger = logging.getLogger(__name__)

def create(args):
    logger.debug("create " + args.full_name + " as " + args.shortname + " from console")
    try:
        Site.create(args.shortname, args.full_name)
    except ShellActionFailed as e:
        logger.error("Could not create {0} because shell actions failed. See log for details.".format(args.shortname))
        logger.error(e)
    except:
        logger.exception("Could not properly create {0}".format(args.shortname))

def delete(args):
    logger.debug("delete " + args.shortname + " from console")
    try:
        Site.delete(args.shortname)
    except Site.DoesNotExist:
        logger.exception("There is no site named {0} in the DB".format(args.shortname))
    except ShellActionFailed as e:
        logger.exception("Could not delete {0} because shell actions failed. The site record remains in the DB.".format(args.shortname))

def adduser(args):
    logger.debug("add user " + args.username + " to " + args.shortname + " from console")
    thesite = Site.get(args.shortname)
    theuser = User.get(args.username)
    if not thesite:
        logger.error("No site named {0} exists".format(args.shortname))
    if not theuser:
        logger.error("No user named {0} exists".format(args.username))
    if thesite and theuser:
        try:
            thesite.addUser(theuser, suppress_welcome=args.no_email)
        except Site.AlreadyHasUser:
            logger.info("{0} is already an administrator of {1}".format(args.username, args.shortname))
        except ShellActionFailed:
            logger.exception("Could not create {0} because shell actions failed. See log for details.".format(args.username))

def removeuser(args):
    logger.debug("remove user" + args.username + " from " + args.shortname + " from console")
    thesite = Site.get(args.shortname)
    theuser = User.get(args.username)
    if not thesite:
        logger.error("No site named {0} exists".format(args.shortname))
    if not theuser:
        logger.error("No user named {0} exists".format(args.username))
    if thesite and theuser:
        try:
            thesite.removeUser(theuser)
        except Site.NoSuchUser:
            logger.info("User {0} is not an administrator of {1}".format(
                theuser.username,
                thesite.shortname
            ))
        except ShellActionFailed as e:
            logger.exception("Could not remove {0} from {1} because shell actions failed. User remains in Site in DB.".format(
                theuser.username,
                thesite.shortname,
            ))


def domain_add(args):
    thesite = Site.get(args.shortname)
    if not thesite:
        logger.error("No site named {0} exists".format(thesite.shortname))
    else:
        try:
            Domain.create(args.domain_name, thesite)
        except Domain.Exists:
            logger.error("Domain {0} already exists in the DB".format(args.domain_name))
        except ShellActionFailed as e:
            logger.exception("Could not add {0} to {1} because shell actions failed.".format(args.domain_name, args.shortname))
        

def domain_remove(args):
    thesite = Site.get(args.shortname)
    if not thesite:
        logger.error("No site named {0} exists".format(thesite.shortname))
    else:
        try:
            Domain.delete(args.domain_name, thesite)
        except Domain.DoesNotExist as e:
            logger.exception("No such domain")
        except ShellActionFailed as e:
            logger.exception("Could not remove {0} from {1} because shell actions failed.".format(args.domain_name, args.shortname))


def db_create(args):
    thesite = Site.get(args.shortname)
    if not thesite:
        logger.error("No site named {0} exists".format(thesite.shortname))
        sys.exit(1)
    if args.dbms.lower() == "mysql":
        dbms = Database.MYSQL
    elif args.dbms.lower() == "postgresql":
        dbms = Database.POSTGRESQL
    else:
        logger.error("Invalid DBMS!")
        sys.exit(1)
    try:
        Database.create(args.database_name, thesite, dbms, fake_create=args.fake_create)
    except Database.Exists as e:
        logger.exception("A database with the name {0} already exists".format(args.database_name))
    except Exception as e:
        logger.exception("Database creation failed")

def db_delete(args):
    thesite = Site.get(args.shortname)
    if not thesite:
        logger.error("No site named {0} exists".format(thesite.shortname))
        sys.exit(1)
    try:
        Database.delete(args.database_name, thesite)
    except Exception as e:
        logger.exception("Database deletion failed")

def status(args):
    s = Site.get(args.shortname)
    logger.info("\t[{0}] {1} ({2})".format(s.shortname, s.full_name, s._get_home()))
    logger.info("\t\tusers: {0}".format(', '.join([u.username for u in s.users])))
    logger.info("\t\tdatabases: {0}".format(', '.join([d.dbname for d in s.databases])))
    logger.info("\t\tdomains: {0}".format(', '.join([d.domain_name for d in s.domains])))

def backup(args):
    logger.debug("back up " + args.shortname + " from console")
