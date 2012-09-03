# Code lifted from Colorama (http://pypi.python.org/pypi/colorama), BSD Licensed
# Included here so Piccolo can be mostly self-contained

CSI = '\033['

def code_to_chars(code):
    return CSI + str(code) + 'm'

class AnsiCodes(object):
    def __init__(self, codes):
        for name in dir(codes):
            if not name.startswith('_'):
                value = getattr(codes, name)
                setattr(self, name, code_to_chars(value))

class AnsiFore:
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37
    RESET   = 39

class AnsiBack:
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47
    RESET   = 49

class AnsiStyle:
    BRIGHT    = 1
    DIM       = 2
    NORMAL    = 22
    RESET_ALL = 0

Fore = AnsiCodes( AnsiFore )
Back = AnsiCodes( AnsiBack )
Style = AnsiCodes( AnsiStyle )
__all__ = [
    'black',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'white',
    'blackbg',
    'redbg',
    'greenbg',
    'yellowbg',
    'bluebg',
    'magentabg',
    'cyanbg',
    'whitebg',
    'dim',
    'bright',
]

def add_attribute(attribute, reset):
    def styled(inp):
        if isinstance(inp, str) or isinstance(inp, unicode):
            s = inp
        else:
            s = inp()
        return attribute + s + reset
    return styled

black = add_attribute(Fore.BLACK, Fore.RESET)
red = add_attribute(Fore.RED, Fore.RESET)
green = add_attribute(Fore.GREEN, Fore.RESET)
yellow = add_attribute(Fore.YELLOW, Fore.RESET)
blue = add_attribute(Fore.BLUE, Fore.RESET)
magenta = add_attribute(Fore.MAGENTA, Fore.RESET)
cyan = add_attribute(Fore.CYAN, Fore.RESET)
white = add_attribute(Fore.WHITE, Fore.RESET)

blackbg = add_attribute(Back.BLACK, Back.RESET)
redbg = add_attribute(Back.RED, Back.RESET)
greenbg = add_attribute(Back.GREEN, Back.RESET)
yellowbg = add_attribute(Back.YELLOW, Back.RESET)
bluebg = add_attribute(Back.BLUE, Back.RESET)
magentabg = add_attribute(Back.MAGENTA, Back.RESET)
cyanbg = add_attribute(Back.CYAN, Back.RESET)
whitebg = add_attribute(Back.WHITE, Back.RESET)

dim = add_attribute(Style.DIM, Style.NORMAL)
bright = add_attribute(Style.BRIGHT, Style.NORMAL)

