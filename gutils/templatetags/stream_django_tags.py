# Import all code from the stream_django activity_tags.py to overcome the fact that it's templatetags file
# has the same name with the actstream app. Now you can use it with the name of this file

from stream_django.templatetags.activity_tags import *