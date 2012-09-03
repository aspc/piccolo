from piccolo.sites import Site, Domain #, SiteExists, BadSiteName
from piccolo.databases import Database
from piccolo.users import User
from piccolo import db
import logging
logger = logging.getLogger(__name__)

def status(args):
    session = db.Session()
    sites = session.query(Site).all()
    users = session.query(User).all()
    logger.info("Sites:")
    for s in sites:
        logger.info("\t[{0}] {1} ({2})".format(s.shortname, s.full_name, s._get_home()))
        logger.info("\t\tusers: {0}".format(', '.join([u.username for u in s.users])))
        logger.info("\t\tdatabases: {0}".format(', '.join([d.dbname for d in s.databases])))
        logger.info("\t\tdomains: {0}".format(', '.join([d.domain_name for d in s.domains])))
    logger.info("Users:")
    for u in users:
        logger.info("\t[{0}] {1} <{2}>".format(u.username, u.full_name, u.email))
        logger.info("\t\tsites: {0}".format(', '.join([s.shortname for s in u.sites])))

def list_users(args):
    session = db.Session()
    all_users = session.query(User).all()
    logger.info("Total users: {0}".format(len(all_users)))
    user_emails = ["{0} <{1}>".format(u.full_name, u.email) for u in all_users]
    print ', '.join(user_emails)

def list_sites(args):
    session = db.Session()
    sites = session.query(Site).all()
    logger.info("Sites:")
    print '\n'.join([s.shortname for s in sites])
