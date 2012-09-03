import stat, os, errno, shlex, subprocess, logging, random, string, time
from os.path import exists, join, basename
from piccolo import config
logger = logging.getLogger(__name__)

class ShellActionFailed(Exception):
    pass

def is_pretend():
    return config.PRETEND

def is_forced():
    return config.FORCE

FLAGS = {
    'u': {'r': stat.S_IRUSR, 'w': stat.S_IWUSR, 'x': stat.S_IXUSR,},
    'g': {'r': stat.S_IRGRP, 'w': stat.S_IWGRP, 'x': stat.S_IXGRP,},
    'o': {'r': stat.S_IROTH, 'w': stat.S_IWOTH, 'x': stat.S_IXOTH,},
}

def format(instring, vars):
    for k in vars.keys():
        instring = instring.replace(k, vars[k])
    return instring

def format_file(infile, vars):
    logger.info("Formatting {0} with vars {1}".format(infile, vars))
    instring = open(infile, 'r').read()
    instring = format(instring, vars)
    if not is_pretend():
        with open(infile, 'w') as out:
            out.write(instring)
        logger.info("Wrote {0}".format(infile))
    

def _template_copy(src, dest, vars, mode):
    try:
        source = open(src, 'r')
        if not is_pretend():
            destination = open(dest, mode)
        for line in source:
            for k in vars.keys():
                line = format(line, vars)
            logger.debug("Writing {0}: {1}".format(dest, line))
            if not is_pretend():
                destination.write(line)
        if not is_pretend():
            destination.close()
        source.close()
    except:
        if is_forced():
            pass
        else:
            raise

def template_copy(src, dest, vars):
    logger.info("Copying template from {0} to {1}".format(src, dest))
    _template_copy(src, dest, vars, 'w')
    
def template_append(src, dest, vars):
    logger.info("Appending template from {0} to {1}".format(src, dest))
    _template_copy(src, dest, vars, 'a')

def do(command, shell=False, ignore_errors=False):
    if not shell:
        args = shlex.split(command)
    else:
        args = command
    logger.info("Executing shell command: {0}".format(command))
    if not is_pretend():
        try:
            output = subprocess.check_output(args, shell=shell, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if not ignore_errors:
                logger.error("Error executing {0}, process exited with code {1}".format(command, e.returncode))
                logger.error(e.output)
            if not (is_forced() or ignore_errors):
                raise ShellActionFailed(command)
        else:
            if output:
                logger.debug(output)

def wait(message, delay=2):
    logger.info("{0} [{1}s]".format(message, delay))
    if not is_pretend():
        time.sleep(delay)

def flags_to_mode(permstring):
    mask = 0
    for perm in permstring.split(','):
        type, attrs = perm.split('=')
        for a in attrs:
            mask |= FLAGS[type][a]
    return mask

def mode(path):
    '''Returns the file mode, including the SETUID/SETGID/ISVTX bits'''
    return stat.S_IMODE(os.stat(path).st_mode)

def ugo_mode(path):
    '''Returns the file mode, masked to include only user, group, and other permission bits'''
    return mode(path) & (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

def generate_password(length=12):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(length))