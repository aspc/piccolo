import argparse, logging
from piccolo import config
from piccolo.commands import sites, users, status

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description='Command line interface to the Piccolo provisioning tool',
    epilog='For additional help on targets, try piccolo targetname -h',
)
parser.add_argument('-p', '--pretend', action='store_true', help="Pretend to run the command, but don't make any changes")
parser.add_argument('-f', '--force', action='store_true', help="Ignore failed shell actions and force completion of command")

subparsers = parser.add_subparsers(help="things you can change with Piccolo")

# Site Management

site = subparsers.add_parser("site")
site.add_argument('shortname', help="Shortname of the site (subdomain)")

site_sub = site.add_subparsers(help="site command")

site_create = site_sub.add_parser("create")
site_create.add_argument('full_name', help="Full name of the site, quoted (club or organization)")
site_create.set_defaults(action=sites.create)

site_delete = site_sub.add_parser("delete")
site_delete.set_defaults(action=sites.delete)

site_status = site_sub.add_parser("status")
site_status.set_defaults(action=sites.status)

site_adduser = site_sub.add_parser("adduser")
site_adduser.add_argument('username', help="username")
site_adduser.add_argument('-n', '--no-email', action='store_true', help="Suppress the automatic welcome email")
site_adduser.set_defaults(action=sites.adduser)

site_removeuser = site_sub.add_parser("removeuser")
site_removeuser.add_argument('username', help="username")
site_removeuser.set_defaults(action=sites.removeuser)

# Domain Management

site_domain = site_sub.add_parser("domain")
site_domain.add_argument("domain_name")

domain_sub = site_domain.add_subparsers(help="domain command")
domain_add = domain_sub.add_parser("add")
domain_add.set_defaults(action=sites.domain_add)

domain_remove = domain_sub.add_parser("remove")
domain_remove.set_defaults(action=sites.domain_remove)

# DB Management

site_db = site_sub.add_parser("db")
site_db.add_argument("database_name")

db_sub = site_db.add_subparsers(help="database command")

db_create = db_sub.add_parser("create")
db_create.set_defaults(action=sites.db_create)
db_create.add_argument("-d", "--dbms", help="Database system to use for this db (mysql or postgresql)", required=True)
db_create.add_argument("-k", "--fake-create", action="store_true", help="Ignore existing db with this name (for adding existing dbs to piccolo)")

db_delete = db_sub.add_parser("delete")
db_delete.set_defaults(action=sites.db_delete)

# Backups

# site_backup = site_sub.add_parser("backup")
# site_backup.set_defaults(action=sites.backup)

# User management

user = subparsers.add_parser("user")
user.add_argument('username', help="username")

user_sub = user.add_subparsers(help="user command")

user_create = user_sub.add_parser("create")
user_create.add_argument("full_name", help="full name")
user_create.add_argument("email", help="contact email address")
user_create.add_argument('-n', '--no-email', action='store_true', help="Suppress the automatic welcome email")
user_create.add_argument("-k", "--fake-create", action="store_true", help="Ignore existing user with this name (for adding existing users to piccolo)")
user_create.set_defaults(action=users.create)

user_delete = user_sub.add_parser("delete")
user_delete.set_defaults(action=users.delete)

status_parser = subparsers.add_parser("status")
status_parser.set_defaults(action=status.status)

list_users_parser = subparsers.add_parser("list_users")
list_users_parser.set_defaults(action=status.list_users)

list_sites_parser = subparsers.add_parser("list_sites")
list_sites_parser.set_defaults(action=status.list_sites)

# status_sub = status.add_subparsers(help="status command")
# 
# status_users = status_sub.add_parser("users")
# status_users.set_defaults(action=users.list)
# 
# status_users = status_sub.add_parser("sites")
# status_users.set_defaults(action=users.list)


def execute_command():
    args = parser.parse_args()
    if args.pretend:
        logger.info("Doing a pretend run... no changes will be made")
        config.PRETEND = True
    else:
        config.PRETEND = False
    if args.force:
        logger.info("Forcing completion... will ignore failed shell actions.")
        config.FORCE = True
    else:
        config.FORCE = False
    
    args.action(args) # perform selected action
