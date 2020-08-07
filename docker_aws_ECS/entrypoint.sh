#!/bin/sh
# * Notice that the EOL character of this file must be UNIX style (LF) otherwise you will get an error when the
#   script runs in the container
# * Notice that despite the fact that this file is not in the zakanda_src directory it is executed from the
#   zakanda_src directory so the path to files are relative to zakanda_src and not to the file's position
set -e
# # python manage.py collectstatic --noinput --clear  # NEVER push static files from your local environment, only from commited code
gunicorn zakanda.wsgi --bind 0.0.0.0:8000
exec "$@"