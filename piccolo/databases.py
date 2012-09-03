import logging, psycopg2, MySQLdb
from piccolo import db, config, shell

logger = logging.getLogger(__name__)

class Database(db.Base):
    MYSQL = 1
    POSTGRESQL = 2
    
    __tablename__ = 'databases'
    dbname = db.Column(db.String(64), primary_key=True)
    dbms = db.Column(db.Integer())
    site_shortname = db.Column(db.String(config.NAME_LIMIT), db.ForeignKey('sites.shortname'))
    site = db.relationship("Site", backref=db.backref('databases', order_by=dbname, cascade="all"))
    
    class Exists(Exception):
        pass
    
    class DoesNotExist(Exception):
        pass
    
    class BadName(Exception):
        pass
    
    class Mismatch(Exception):
        pass
    
    def __init__(self, dbname, site, dbms):
        self.dbname = dbname
        self.dbms = dbms
        self.site = site
    
    @staticmethod
    def _postgres():
        conn = psycopg2.connect(
            user=config.POSTGRESQL['username'],
            password=config.POSTGRESQL['password'],
            database="postgres")
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn, conn.cursor()
    
    @staticmethod
    def _mysql():
        conn = MySQLdb.connect(
            user=config.MYSQL['username'],
            passwd=config.MYSQL['password'],
            db="mysql",
        )
        return conn, conn.cursor()
    
    @staticmethod
    def _mysql_exists(dbname):
        conn, cur = Database._mysql()
        cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s;", (dbname,))
        if cur.fetchone():
            return True
        else:
            return False
        
    @staticmethod
    def _postgres_exists(dbname):
        conn, cur = Database._postgres()
        cur.execute("SELECT datname FROM pg_database WHERE datname = %s;", (dbname,))
        if cur.fetchone():
            return True
        else:
            return False
        conn.close()
    
    def _create(self, ignore_exists):
        if self.dbms == Database.MYSQL:
            logger.info("Creating MySQL database {0}".format(self.dbname))
            if not shell.is_pretend():
                self._mysql_create(ignore_exists)
        elif self.dbms == Database.POSTGRESQL:
            logger.info("Creating PostgreSQL database {0}".format(self.dbname))
            if not shell.is_pretend():
                self._postgres_create(ignore_exists)
        else:
            raise Exception("Invalid DBMS")
    
    def _mysql_create(self, ignore_exists):
        if Database._mysql_exists(self.dbname):
            if not ignore_exists:
                raise Database.Exists
        else:
            conn, cur = Database._mysql()
            if not ignore_exists:
                cur.execute("CREATE DATABASE `{0}`;".format(self.dbname)) # not using builtin escapes because they quote wrong, and the risk of injection is tiny here
            cur.execute("GRANT ALL PRIVILEGES ON `{0}`.* TO %s@localhost;".format(self.dbname), (self.site.db_username,))
    
    def _postgres_create(self, ignore_exists):
        if Database._postgres_exists(self.dbname):
            if not ignore_exists:
                raise Database.Exists
        else:
            conn, cur = Database._postgres()
            if ignore_exists:
                cur.execute("ALTER DATABASE {0} OWNER TO {1};".format(self.dbname, self.site.db_username))
            else:
                cur.execute("CREATE DATABASE {0} WITH OWNER = {1};".format(self.dbname, self.site.db_username))
    
    def _drop(self):
        if self.dbms == Database.MYSQL:
            logger.info("Dropping MySQL database {0}".format(self.dbname))
            if not shell.is_pretend():
                self._mysql_drop()
        elif self.dbms == Database.POSTGRESQL:
            logger.info("Dropping PostgreSQL database {0}".format(self.dbname))
            if not shell.is_pretend():
                self._postgres_drop()
        else:
            raise Exception("Invalid DBMS")
    
    def _mysql_drop(self):
        if not Database._mysql_exists(self.dbname):
            raise Database.DoesNotExist
        conn, cur = Database._mysql()
        cur.execute("DROP DATABASE {0};".format(self.dbname))
        # cur.execute("REVOKE ALL PRIVILEGES ON {0}.* FROM %s@localhost;".format(self.dbname), (self.site.shortname,))
    
    def _postgres_drop(self):
        if not Database._postgres_exists(self.dbname):
            raise Database.DoesNotExist
        conn, cur = Database._postgres()
        cur.execute("DROP DATABASE {0};".format(self.dbname))
    
    def _dbms_string(self):
        if self.dbms == Database.MYSQL:
            return 'MySQL'
        elif self.dbms == Database.POSTGRESQL:
            return 'PostgreSQL'
        else:
            raise Exception("Invalid dbms")
    
    @staticmethod
    def get(dbname):
        session = db.Session()
        q = session.query(Database).filter(Database.dbname == dbname)
        if (q.count() == 1):
            return q.first()
        else:
            return None
    
    @staticmethod
    def create(dbname, site, dbms, fake_create):
        session = db.Session()
        if Database.get(dbname):
            raise Database.Exists # do not ignore db already existing in piccolo...
        if len(dbname) > 63:
            raise Database.BadName("Database names must be < 63 characters long")
        new_db = Database(dbname, site, dbms)
        new_db._create(fake_create)
        if not shell.is_pretend():
            session.add(new_db)
            session.commit()
            with open(shell.join(site._get_home(), 'config', 'databases.txt'), 'a') as db_list:
                db_list.write("[{0}] {1}\n".format(new_db._dbms_string(), new_db.dbname))
    
    @staticmethod
    def delete(dbname, site):
        session = db.Session()
        the_db = Database.get(dbname)
        if not the_db:
            raise Database.DoesNotExist
        if the_db.site is not site:
            raise Database.Mismatch("Database {0} exists, but is owned by {1}, not {2}".format(
                dbname,
                the_db.site.shortname,
                site.shortname,
            ))
        the_db._drop()
        if not shell.is_pretend():
            dbms_string = the_db._dbms_string()
            session.delete(the_db)
            session.commit()
            old_db_list = open(shell.join(site._get_home(), 'config', 'databases.txt'), 'r').read()
            new_db_list = old_db_list.replace("[{0}] {1}\n".format(dbms_string, dbname), '')
            with open(shell.join(site._get_home(), 'config', 'databases.txt'), 'w') as db_list:
                db_list.write(new_db_list)
    
    def dump(dbname, destination):
        if Database.get(dbname):
            raise Database.DoesNotExist
        # test exists
        # dump (_my,_post)
        pass
    
    def restore(dbname, source):
        if Database.get(dbname):
            raise Database.DoesNotExist
        # hmm don't run this without knowing what the source file does...
        # limit it to one db?
        pass