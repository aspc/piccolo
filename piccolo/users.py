import re, os, logging, pwd, time, stat, smtplib
from email.mime.text import MIMEText
import piccolo.log
from piccolo import db, config, shell
from piccolo.shell import do, wait

logger = logging.getLogger(__name__)

class User(db.Base):
    __tablename__ = 'users'
    username = db.Column(db.String(config.NAME_LIMIT), primary_key=True)
    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    
    class Exists(Exception):
        pass
    
    class DoesNotExist(Exception):
        pass
    
    class BadName(Exception):
        pass
    
    class ShellActionFailed(Exception):
        pass
    
    def __init__(self, username, full_name, email):
        self.username = username
        self.full_name = full_name
        self.email = email
    
    def __str__(self):
        return u"<User: {0}>".format(self.username)

    __unicode__ = __str__
    
    def _get_home(self):
        return shell.join(config.USERS_ROOT, self.username)
    
    def _vars(self):
        return {
            '$USERNAME': self.username,
            '$FULL_NAME': self.full_name
        }
    
    def send_email(self, subject, message):
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = "{0} <{1}>".format(config.EMAIL['friendly_name'], config.EMAIL['username'])
        msg['To'] = "{0} <{1}>".format(self.full_name, self.email)
        
        s = smtplib.SMTP(config.EMAIL['smtp_server'], config.EMAIL['smtp_port'])
        s.starttls()
        s.login(config.EMAIL['username'], config.EMAIL['password'])
        s.sendmail(config.EMAIL['username'], [self.email], msg.as_string())
        s.quit()
    
    def _shell_create(self):
        do("useradd -U -b {0} -m -s /bin/bash {1}".format(
            config.USERS_ROOT,
            self.username
        ))
        self._format_append("user_bash_profile.sh", shell.join(self._get_home(), ".profile"))
        tmppass = shell.join(self._get_home(), '.tmppass')
        with open(tmppass, 'w') as t:
            os.chmod(tmppass, stat.S_IRWXU)
            t.write("{0}\n{0}\n".format(self._temp_password))
            t.close()
        do("passwd {0} < {1}".format(self.username, tmppass), shell=True)
        do("passwd -e {0}".format(self.username))
        do("rm {0}".format(tmppass))
    
    def _shell_delete(self):
        do("pkill -u {0}".format(self.username), ignore_errors=True)
        wait("Waiting for user's processes to exit")
        do("userdel -r {0}".format(self.username))
    
    def _format_copy(self, src, dest):
        src = shell.join(config.TEMPLATE_ROOT, src)
        shell.template_copy(src, dest, self._vars())
    
    def _format_append(self, src, dest):
        src = shell.join(config.TEMPLATE_ROOT, src)
        shell.template_append(src, dest, self._vars())
    
    @staticmethod
    def get(username):
        session = db.Session()
        userq = session.query(User).filter(User.username == username)
        if (userq.count() == 1):
            return userq.first()
        else:
            return None
    
    @staticmethod
    def create(username, full_name, email, suppress_welcome=False, fake_create=False):
        if fake_create:
            suppress_welcome = True
        session = db.Session()
        if not config.NAME_REGEX.match(username) or len(username) > config.NAME_LIMIT:
            raise User.BadName("{0} is not a valid username (containing only letters, numbers, and dashes and being between 2 and {1} characters)".format(username, config.NAME_LIMIT))
        
        if User.get(username):
            raise User.Exists("There is already a user named {0} in piccolo".format(username))
        
        try:
            pwd.getpwnam(username)
        except KeyError:
            pass
        else:
            if not fake_create:
                raise User.Exists("There is already a user named {0} in /etc/passwd".format(username))
        
        if shell.exists(shell.join(config.USERS_ROOT, username)) and not fake_create:
            raise User.BadName("Cannot create user {1} because folder {0} already exists.".format(shell.join(config.USERS_ROOT, username), username))
        logger.debug("user doesn't exist yet")
        new_user = User(username, full_name, email)
        session.add(new_user)
        session.commit()
        new_user._temp_password = shell.generate_password(length=12)
        try:
            if not fake_create:
                new_user._shell_create()
        except User.ShellActionFailed:
            session.delete(new_user)
            session.commit()
            raise
        else:
            logger.info('Created user "{0}" [{1}] with contact email <{2}>'.format(full_name, username, email))
            if not suppress_welcome:
                user_vars = new_user._vars()
                user_vars.update({"$INITIAL_PASSWORD": new_user._temp_password,})
                email_message = shell.format(open(shell.join(config.TEMPLATE_ROOT, 'user_email.txt')).read(), user_vars)
                email_subject = "New Peninsula Account {0}".format(new_user.username)
                new_user.send_email(email_subject, email_message)
                logger.info("Sent welcome email to {0}".format(new_user.email))
            elif not fake_create:
                logger.info("User's initial password: {0}".format(new_user._temp_password))
    
    @staticmethod
    def delete(username):
        session = db.Session()
        the_user = User.get(username)
        if not the_user:
            raise User.DoesNotExist("Cannot delete {0} because it does not exist in the DB".format(username))
        try:
            the_user._shell_delete()
        except shell.ShellActionFailed as e:
            logger.exception("Shell action failed")
            raise
        else:
            session.delete(the_user)
            session.commit()
            logger.info("Deleted {0} from the DB".format(username))
    
    def archive(destination=None):
        archive_name = '{0}.tar.gz'.format(theuser.username)
        if not destination:
            destination = shell.join(DATA_DIR, 'deleted_users', archive_name)
        else:
            destination = shell.join(destination, archive_name)
        try:
            subprocess.check_output(
                ["/bin/tar", "cvzf",],
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError, err:
            raise User.ShellActionFailed(err)