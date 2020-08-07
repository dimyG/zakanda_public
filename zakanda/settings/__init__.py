from .base import *

try:
    print "searching local settings..."
    from .local import *
except ImportError:
    print "local settings not found!"
    try:
        print 'searching production settings...'
        from .production import *
    except ImportError:
        print "production settings not found!"
        pass
