import logging, shutil, glob, os, string, time, re
import piccolo.log
from piccolo import db, config, shell
from piccolo.users import User
from piccolo.databases import Database
from piccolo.shell import do, wait

logger = logging.getLogger(__name__)

site_users = db.Table('site_users', db.Base.metadata,
    db.Column('site_shortname', db.String(config.NAME_LIMIT), db.ForeignKey('sites.shortname')),
    db.Column('user_username', db.String(config.NAME_LIMIT), db.ForeignKey('users.username'))
)

class Site(db.Base):
    __tablename__ = 'sites'
    shortname = db.Column(db.String(config.NAME_LIMIT), primary_key=True)
    full_name = db.Column(db.String(255))
    db_username = db.Column(db.String(config.NAME_LIMIT), unique=True)
    db_username_mysql = db.Column(db.String(16), unique=True) # because MySQL has to be special >:|
    db_password = db.Column(db.String(20))
    users = db.relationship('User',
                    secondary=site_users,
                    backref="sites",
                    lazy='joined',
                    join_depth=1)
    
    _permissions = (
        ('bin', 'u=rx,g=rx,o='),
        ('config', 'u=rwx,g=rwx,o='),
        ('logs', 'u=rwx,g=rx,o='),
        ('public', 'u=rwx,g=rwxs,o='),
        ('run', 'u=rwx,g=rxs,o=x'),
        ('temp', 'u=rwx,g=rxs,o=')
    )
    
    _additional_dirs = (
        'logs',
        'run',
        'temp',
        'temp/nginx'
    )
    
    class Exists(Exception):
        pass
    
    class DoesNotExist(Exception):
        pass
    
    class BadName(Exception):
        pass
    
    class AlreadyHasUser(Exception):
        pass
    
    class NoSuchUser(Exception):
        pass
    
    def __init__(self, shortname, full_name):
        self.shortname = shortname
        self.full_name = full_name
    
    def __str__(self):
        return u"<Site: {0}>".format(self.shortname)
    
    __unicode__ = __str__
    
    def _get_home(self):
        return shell.join(config.SITES_ROOT, self.shortname)
    
    
    def _create_db_accounts(self):
        logger.info("Creating PostgreSQL user account {0}".format(self.db_username))
        if not shell.is_pretend():
            conn, cur = Database._postgres()
            cur.execute("CREATE ROLE {0} PASSWORD '{1}' LOGIN;".format(self.db_username, self.db_password))
            cur.execute('SELECT pg_reload_conf();')
            cur.close()
            conn.close()
        
        logger.info("Creating MySQL user account {0}".format(self.db_username_mysql))
        if not shell.is_pretend():
            conn, cur = Database._mysql()
            cur.execute("CREATE USER '{0}'@'localhost' IDENTIFIED BY '{1}';".format(self.db_username_mysql, self.db_password))
            cur.close()
            conn.close()
    
    def _drop_db_accounts(self):
        logger.info("Dropping databases associated with {0}".format(self.shortname))
        
        for provisioned_db in self.databases:
            try:
                provisioned_db._drop()
            except:
                if not shell.is_forced(): raise
        try:
            logger.info("Dropping PostgreSQL user account {0}".format(self.db_username))
            if not shell.is_pretend():
                conn, cur = Database._postgres()
                cur.execute("DROP OWNED BY {0};".format(self.db_username))
                cur.execute("DROP ROLE {0};".format(self.db_username))
                cur.execute('SELECT pg_reload_conf();')
                cur.close()
                conn.close()
        except:
            if not shell.is_forced():
                raise
        
        try:
            logger.info("Dropping MySQL user account {0}".format(self.db_username_mysql))
            if not shell.is_pretend():
                conn, cur = Database._mysql()
                cur.execute("DROP USER '{0}'@'localhost';".format(self.db_username_mysql))
                cur.close()
                conn.close()
        except:
            if not shell.is_forced():
                raise
    
    def _shell_delete(self):
        for service in ("httpd.sh", "php.sh"):
            do("sudo -u {0} {1} stop".format(self.shortname, shell.join(self._get_home(), "bin", service)))
        do("pkill -u {0}".format(self.shortname), ignore_errors=True)
        
        wait("Waiting for services to be removed from process list")
        
        try:
            self._drop_db_accounts()
        except:
            if not shell.is_forced():
                raise
        
        do("rm /etc/sudoers.d/{0}".format(self.shortname))
        do("rm /etc/piccolo/nginx/{0}.conf".format(self.shortname))
        do("rm -rf /etc/piccolo/nginx/{0}_domains".format(self.shortname))
        do("userdel -r {0}".format(self.shortname))
        do("groupdel {0}".format(self.shortname), ignore_errors=True)
    
    def _shell_create(self, pretend=False):
        # Actual shell-level business of provisioning the site goes here
        
        # Set up siteuser and sitegroup
        do("useradd -U -b {0} -m -s /bin/bash {1}".format(
            config.SITES_ROOT,
            self.shortname
        ))
        
        # Set up template and permissions
        do("chmod u=rwX,g=rwXs,o=X {0}".format(self._get_home()))
        
        for path in glob.glob(shell.join(config.TEMPLATE_ROOT, 'site', '*')):
            do("cp -R {0} {1}".format(path, self._get_home()))
        
        for d in Site._additional_dirs:
            do("mkdir {0}".format(shell.join(self._get_home(), d)))
        
        do("chown -R {0}:{0} {1}".format(self.shortname, self._get_home()))
        
        for p in Site._permissions:
            do("chmod {0} {1}".format(p[1], shell.join(self._get_home(), p[0])))
        
        # Do variable substitution in template files
        
        for root, dirs, files in os.walk(self._get_home()):
            for name in files:
                shell.format_file(shell.join(root, name), self._vars())
        
        for root, dirs, files in os.walk(shell.join(self._get_home(), "bin")):
            for name in files:
                do("chmod u=rwx,g=rx,o= {0}".format(shell.join(root, name)))
        
        for root, dirs, files in os.walk(shell.join(self._get_home(), "config")):
            for name in files:
                do("chmod u=rw,g=rw,o= {0}".format(shell.join(root, name)))
        
        # Install crontab from temp file
        
        crontab_path = shell.join(self._get_home(), 'crontab')
        self._format_copy('site.crontab', crontab_path)
        
        do("crontab -u {0} {1}".format(self.shortname, crontab_path))
        do("rm {0}".format(crontab_path))
        
        # Install sudoers
        sudoers_dest = '/etc/sudoers.d/{0}'.format(self.shortname)
        if shell.exists(sudoers_dest):
            raise shell.ShellActionFailed("{0} exists. Abort!".format(sudoers_dest))
        self._format_copy('site.sudoers', sudoers_dest)
        do("chmod u=r,g=r,o= {0}".format(sudoers_dest))
        do("chown root:root {0}".format(sudoers_dest))
        
        # Install nginx config
        nginx_dest = shell.join(config.NGINX_CONF_ROOT, "{0}.conf".format(self.shortname))
        if shell.exists(nginx_dest):
            raise shell.ShellActionFailed("{0} exists. Abort!".format(nginx_dest))
        self._format_copy('site.nginx.conf', nginx_dest)
        do("chmod u=rw,g=rw,o=r {0}".format(nginx_dest))
        do("chown root:admin {0}".format(nginx_dest))
        
        do("mkdir {0}".format(shell.join(config.NGINX_CONF_ROOT, "{0}_domains".format(self.shortname))))
        
        # Set up db users
        self._create_db_accounts()
        
        # Start site
        for service in ("httpd.sh", "php.sh"):
            do("sudo -u {0} {1} start".format(self.shortname, shell.join(self._get_home(), "bin", service)))
    
    def _vars(self):
        return {
            '$SHORTNAME': self.shortname,
            '$FULL_NAME': self.full_name,
            '$SITE_ROOT': self._get_home(),
            '$DB_USERNAME': self.db_username,
            '$DB_USERNAME_MYSQL': self.db_username_mysql,
            '$DB_PASSWORD': self.db_password,
            '$NGINX_CONF_ROOT': config.NGINX_CONF_ROOT,
        }
    
    def _format_template(self, src):
        src = shell.join(config.TEMPLATE_ROOT, src)
        return shell.format(open(src, 'r').read(), self._vars())
    
    def _format_copy(self, src, dest):
        src = shell.join(config.TEMPLATE_ROOT, src)
        shell.template_copy(src, dest, self._vars())
    
    @staticmethod
    def get(shortname):
        session = db.Session()
        siteq = session.query(Site).filter(Site.shortname == shortname)
        if (siteq.count() == 1):
            return siteq.first()
        else:
            return None
    
    @staticmethod
    def delete(shortname):
        session = db.Session()
        the_site = Site.get(shortname)
        if not the_site:
            raise Site.DoesNotExist("Cannot delete {0} because it does not exist in the DB".format(shortname))
        try:
            the_site._shell_delete()
        except shell.ShellActionFailed as e:
            logger.exception("Shell action failed")
            raise
        else:
            if not shell.is_pretend():
                session.delete(the_site)
                session.commit()
                do("service nginx reload")
            logger.info("Deleted {0} from the DB".format(shortname))
    
    @staticmethod
    def create(shortname, full_name):
        session = db.Session()
        if Site.get(shortname):
            raise Site.Exists
        elif shell.exists(shell.join(config.SITES_ROOT, shortname)):
            raise Site.Exists
        elif not config.NAME_REGEX.match(shortname) or len(shortname) > config.NAME_LIMIT:
            raise Site.BadName("Site names must be between 2 and {0} characters and be valid hostnames (only letters, numbers, and dashes)".format(config.NAME_LIMIT))
        elif Domain.get('.'.join([shortname, config.DEFAULT_DOMAIN])):
            existing = Domain.get('.'.join([shortname, config.DEFAULT_DOMAIN]))
            raise Site.BadName("There is already a domain {0} in piccolo, so adding this site would "\
                "create a name conflict. Remove {0} from {1} before "\
                "adding this site.".format(existing.domain_name, existing.site.shortname))
        else:
            logger.debug("site doesn't exist yet in db")
            new_site = Site(shortname, full_name)
        
        new_site.db_password = shell.generate_password(length=20)
        new_site.db_username = re.sub(r'[^\w\d]', '_', new_site.shortname)
        new_site.db_username_mysql = new_site.db_username[:16] # grrr
        
        if not shell.is_pretend():
            session.add(new_site)
            session.commit()
        try:
            new_site._shell_create()
            if not shell.is_pretend():
                Domain.create('.'.join([new_site.shortname, config.DEFAULT_DOMAIN]), new_site)
        except shell.ShellActionFailed as e:
            logger.exception("Shell action failed")
            raise
        else:
            do("service nginx reload")
            logger.info('Created site "{0}" [{1}]'.format(full_name, shortname))
    
    def addUser(self, user, suppress_welcome=False):
        if shell.is_pretend():
            suppress_welcome = True
            logger.info("Pretending to add {0} to site {1}".format(user, self))
        
        session = db.Session()
        logger.debug('Users in {0}: {1}'.format(self.shortname, self.users))
        if user in self.users:
            raise Site.AlreadyHasUser
        if not shell.is_pretend():
            self.users.append(user)
            session.commit()
        try:
            do("gpasswd -a {0} {1}".format(user.username, self.shortname))
            do("ln -s {0} {1}".format(self._get_home(), shell.join(user._get_home(), self.shortname)))
        except shell.ShellActionFailed:
            if not shell.is_pretend():
                self.users.remove(user)
                session.commit()
            raise
        else:
            if not suppress_welcome:
                email_vars = {
                    "$FULL_NAME": user.full_name,
                    "$SITE_SHORTNAME": self.shortname,
                }
                
                email_message = shell.format(open(shell.join(config.TEMPLATE_ROOT, 'site_adduser_email.txt')).read(), email_vars)
                email_subject = "Peninsula Account Update: {0} added to site {1}".format(user.username, self.shortname)
                user.send_email(email_subject, email_message)
                logger.info("Sent adduser email to {0}".format(user.email))
            logger.info('Added {0} to {1}'.format(user.username, self.shortname))
    
    def removeUser(self, user):
        if shell.is_pretend():
            logger.info("Pretending to remove {0} from site {1}".format(user, self))

        session = db.Session()
        logger.debug('Users in {0}: {1}'.format(self.shortname, self.users))
        if not user in self.users:
            raise Site.NoSuchUser
        try:
            do("gpasswd -d {0} {1}".format(user.username, self.shortname))
            do("rm {0}".format(shell.join(user._get_home(), self.shortname)))
        except shell.ShellActionFailed:
            logger.exception("Removal failed; user is still member of site in DB.")
            raise
        else:
            if not shell.is_pretend():
                self.users.remove(user)
                session.commit()
            logger.info('Removed {0} from {1}'.format(user.username, self.shortname))

class Domain(db.Base):
    __tablename__ = 'domain'
    domain_name = db.Column(db.String(50), primary_key=True)
    site_shortname = db.Column(db.String(20), db.ForeignKey('sites.shortname'))
    site = db.relationship("Site", backref=db.backref('domains', order_by=domain_name, cascade="all"))
    
    class Exists(Exception):
        pass
    
    class DoesNotExist(Exception):
        pass
    class Mismatch(Exception):
        pass
    
    class MinimumDomains(Exception):
        pass
    
    def __init__(self, domain_name, site):
        self.domain_name = domain_name
        self.site = site
    
    def _vars(self):
        return {
            "$DOMAIN_NAME": self.domain_name,
        }
    
    def _get_folder(self):
        return shell.join(config.NGINX_CONF_ROOT, "{0}_domains".format(self.site.shortname))
    
    def _get_path(self):
        return shell.join(self._get_folder(), "{0}.conf".format(self.domain_name))
    
    def _shell_create(self):
        self._format_copy("site.nginx.domain.conf", self._get_path())
        do("service nginx reload")
    
    def _shell_delete(self):
        do("rm {0}".format(self._get_path()))
        do("service nginx reload")
    
    def _format_copy(self, src, dest):
        src = shell.join(config.TEMPLATE_ROOT, src)
        shell.template_copy(src, dest, self._vars())
    
    @staticmethod
    def get(domain_name):
        session = db.Session()
        q = session.query(Domain).filter(Domain.domain_name == domain_name)
        if (q.count() == 1):
            return q.first()
        else:
            return None
    
    @staticmethod
    def create(domain_name, site_instance):
        session = db.Session()
        if Domain.get(domain_name):
            raise Domain.Exists
        new_domain = Domain(domain_name, site_instance)
        
        if not shell.is_pretend():
            session.add(new_domain)
            session.commit()
        try:
            new_domain._shell_create()
        except shell.ShellActionFailed as e:
            logger.exception("Shell action failed")
            raise
        else:
            logger.info('Added domain "{0}" for site {1}'.format(domain_name, site_instance.shortname))
    
    @staticmethod
    def delete(domain_name, site_instance):
        session = db.Session()
        the_domain = Domain.get(domain_name)
        if the_domain.site is not site_instance:
            raise Domain.Mismatch("Domain {0} exists, but is not associated with site {1}".format(domain_name, site_instance.shortname))
        if not the_domain:
            raise Domain.DoesNotExist("No domain {0} in the DB".format(domain_name))
        if len(site_instance.domains) < 2:
            raise Domain.MinimumDomains("Sites need at least one domain, but {0} will have zero "\
                "if you remove this one. Add an alternate domain first!".format(site_instance.shortname))
        try:
            the_domain._shell_delete()
        except shell.ShellActionFailed as e:
            logger.exception("Shell action failed")
            raise
        else:
            if not shell.is_pretend():
                session.delete(the_domain)
                session.commit()
            logger.info('Deleted domain "{0}"'.format(domain_name))
