#!/usr/bin/env python
from ConfigParser import SafeConfigParser
from datetime import date
import sys, subprocess, shlex, random, string, os, os.path, shutil

INSTALL_ROOT = os.path.dirname(__file__)

def generate_password(length=12):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(length))

def format(instring, vars):
    for k in vars.keys():
        instring = instring.replace(k, vars[k])
    return instring

def template_copy(src, dest, vars):
    source = open(src, 'r')
    destination = open(dest, 'w')
    do("chmod u=rw,g=,o= {0}".format(dest))
    for line in source:
        for k in vars.keys():
            line = format(line, vars)
        destination.write(line)
    destination.close()
    source.close()

def do(command):
    args = shlex.split(command)
    print "Executing shell command: {0}".format(command)
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print "Error executing {0}, process exited with code {1}".format(command, e.returncode)
        print e.output
        sys.exit(1)
    else:
        if output:
            print output

def get_input(prompt, default=None, optional=False):
    prompt = "{0}".format(prompt)
    if optional:
        prompt += " (optional): "
    elif default:
         prompt += " [{0}]: ".format(default)
    else:
        prompt += ": "
    val = None
    while not val:
        val = raw_input(prompt)
        if default and not val:
            return default
        elif optional:
            break
    return val

print "Install Piccolo"
print
print "=-======o=oooo\oo=o=o=o=="
print

if os.geteuid() != 0:
    sys.stderr.write("This install tool must be run as root")
    sys.exit(1)

config = SafeConfigParser()
config.add_section("piccolo")
config.set("piccolo", "sites_root", get_input("Root directory for sites", default="/srv/www"))
config.set("piccolo", "default_domain", get_input("Default domain", default="aspc.pomona.edu"))
config.set("piccolo", "users_root", "/home")
config.set("piccolo", "nginx_conf_root", get_input("Root directory for site nginx configs", default="/etc/piccolo/nginx"))
config.set("piccolo", "data", get_input("Directory for Piccolo data", default="/var/local/piccolo"))
config.set("piccolo", "logs", get_input("Log directory", default="/var/log/piccolo"))

folders = [
    ("/usr/local/piccolo", "root", "admin", "u=rwx,g=,o="),
    ("/etc/piccolo", "root", "admin", "u=rwx,g=rx,o=rx"),
    (config.get("piccolo", "nginx_conf_root"), "root", "admin", "u=rwx,g=rx,o=rx"),
    (config.get("piccolo", "sites_root"), "root", "admin", "u=rwx,g=rx,o=rx"),
    (os.path.join(config.get("piccolo", "sites_root"), "default"), "root", "admin", "u=rwx,g=rwxs,o=rx"),
    (os.path.join(config.get("piccolo", "sites_root"), "default", "public"), "root", "admin", "u=rwx,g=rwxs,o=rx"),
    (config.get("piccolo", "data"), "root", "admin", "u=rwx,g=rx,o="),
    (config.get("piccolo", "logs"), "root", "admin", "u=rwx,g=rx,o="),
]

for path, user, group, mode in folders:
    if os.path.exists(path):
        print "{0} already exists! Rather than risk messing things up, this tool is just going to quit.".format(path)
        sys.exit(1)
    else:
        do("mkdir {0}".format(path))
        do("chown {0}:{1} {2}".format(user, group, path))
        do("chmod {0} {1}".format(mode, path))

# Create default site

# Move dist default out of the way
default_en = "/etc/nginx/sites-enabled/default"
default_av = "/etc/nginx/sites-available/default"
if os.path.exists(default_en):
    do("rm {0}".format(default_en))
if os.path.exists(default_av):
    do("mv {0} {0}.dist".format(default_av))

# Copy in template

template_copy(
    os.path.join(INSTALL_ROOT, "default_nginx.conf"),
    "/etc/nginx/sites-available/default",
    {
        "$SITES_ROOT": config.get("piccolo", "sites_root"),
        "$NGINX_CONF_ROOT": config.get("piccolo", "nginx_conf_root"),
    }
)

do("ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/000-default")

# Add upload limit increase to global config

template_copy(
    os.path.join(INSTALL_ROOT, "upload_limit_increase.conf"),
    "/etc/nginx/conf.d/upload_limit_increase.conf",
    {}
)

# Copy ssl settings to install dir

template_copy(
    os.path.join(INSTALL_ROOT, "ssl_settings.conf"),
    "/etc/piccolo/ssl_settings.conf",
    {}
)

# Copy index.html to new default dir

shutil.copyfile(
    os.path.join(INSTALL_ROOT, "default_index.html"),
    os.path.join(config.get("piccolo", "sites_root"), "default", "public", "index.html")
)

do("service nginx stop")
do("service nginx start")

# Set up database access

# MySQL

config.add_section("mysql")
config.set("mysql", "username", "piccolo")
config.set("mysql", "password", generate_password(length=20))

print "This install tool will create a MySQL account to manage users and databases. The "\
    "account will be named 'piccolo'."
print "\nEnter your MySQL root password when prompted.\n"

mysql_temp = os.path.expanduser(os.path.join("~", "install_mysql_tmp.sql"))
template_copy(
    os.path.join(INSTALL_ROOT, "install_mysql.sql"),
    mysql_temp,
    {"$MYSQL_PASSWORD": config.get("mysql", "password"),}
)
do("mysql -u root -p -e 'source {0}'".format(mysql_temp))
os.remove(mysql_temp)
print
print "Okay, done!"
print

# PostgreSQL

config.add_section("postgresql")
config.set("postgresql", "username", "piccolo")
config.set("postgresql", "password", generate_password(length=20))

print "This install tool will create a PostgreSQL user account to manage users and databases. The "\
    "account will be named 'piccolo'."

postgres_temp = os.path.expanduser(os.path.join("~", "install_postgres_tmp.sql"))
template_copy(
    os.path.join(INSTALL_ROOT, "install_postgres.sql"),
    postgres_temp,
    {"$POSTGRES_PASSWORD": config.get("postgresql", "password"),}
)
do("chown postgres {0}".format(postgres_temp))
do("sudo -u postgres psql -f {0}".format(postgres_temp))
do("sudo -u postgres psql -c 'select pg_reload_conf()'")
do("rm {0}".format(postgres_temp))
print
print "Okay, done!"
print

# Set up email access

print "Piccolo needs to be able to send emails to new webmasters. This is usually done through the system@aspc.pomona.edu account."
print
config.add_section("email")
config.set("email", "username", get_input("Email Account", default="system@aspc.pomona.edu"))
config.set("email", "password", get_input("Password"))
config.set("email", "smtp_server", get_input("SMTP Server", default="smtp.gmail.com"))
config.set("email", "smtp_port", get_input("SMTP Port", default="587"))
config.set("email", "friendly_name", get_input("Friendly Name", default="The ASPC System"))
print
print "Okay, that's all!"
print
# Install piccolo

REPO_DIR = os.path.abspath(os.path.join(INSTALL_ROOT, '..'))

# clone to final location
do("hg clone {0} /usr/local/piccolo".format(REPO_DIR))

# chmod
do("chown -R root:admin {0}".format("/usr/local/piccolo"))
do("chmod -R g=,o= {0}".format("/usr/local/piccolo"))

# install config & chmod it

destination = open("/etc/piccolo/piccolo.cfg", 'w')
do("chmod u=rw,g=,o= /etc/piccolo/piccolo.cfg")

header = "; Piccolo Configuration [{0}] ;".format(date.today().isoformat())

destination.write(';'*len(header) + "\n")
destination.write(header + "\n")
destination.write(';'*len(header) + "\n")

config.write(destination)

# symlink

do("ln -s /usr/local/piccolo/bin/piccolo-admin.py /usr/local/sbin/piccolo")