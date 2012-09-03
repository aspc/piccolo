import ConfigParser, sys, os.path, stat, re

PICCOLO_SRC_DIR = os.path.dirname(__file__)
PICCOLO_ROOT = os.path.abspath(os.path.join(PICCOLO_SRC_DIR, '..'))
CONFIG_PATH = "/etc/piccolo/piccolo.cfg"
TEMPLATE_ROOT = os.path.join(PICCOLO_ROOT, "templates")
NAME_LIMIT = 32
NAME_REGEX = re.compile(r'^([A-Za-z0-9\-]{2,})$')

if not os.path.exists(CONFIG_PATH):
    sys.stderr.write("Config file missing!\n")
    sys.stderr.write("(Have you made a config file yet? Use {0} to generate one, then save it in {1} with the permissions u=rw.)\n".format(
        os.path.join(PICCOLO_ROOT, "configure.py"),
        CONFIG_PATH,
    ))
    sys.exit(1)

try:
    config = ConfigParser.SafeConfigParser()
    config.read(CONFIG_PATH)
except IOError as e:
    sys.stderr.write("Couldn't open {0}!")
    if os.geteuid() != 0:
        sys.stderr.write("(This is probably because you're not running as root.)")
    sys.stderr.write(str(e))
    sys.exit(1)

DATA_DIR = config.get("piccolo", "data")
USERS_ROOT = config.get("piccolo", "users_root")
SITES_ROOT = config.get("piccolo", "sites_root")
DEFAULT_DOMAIN = config.get("piccolo", "default_domain")
NGINX_CONF_ROOT = config.get("piccolo", "nginx_conf_root")
LOGGING = {
    'directory': config.get("piccolo", "logs"),
    'max_size': 1, # in MB
    'retain_count': 1, # Keep this many copies of the old logs after rotating
}

DATABASE = os.path.join(DATA_DIR, "piccolo.sqlite")
MYSQL = {
    'username': config.get("mysql", "username"),
    'password': config.get("mysql", "password"),
}
POSTGRESQL = {
    'username': config.get("postgresql", "username"),
    'password': config.get("postgresql", "password"),
}
EMAIL = {
    'username': config.get("email", "username"),
    'password': config.get("email", "password"),
    'smtp_server': config.get("email", "smtp_server"),
    'smtp_port': config.get("email", "smtp_port"),
    'friendly_name': config.get("email", "friendly_name"),
}
