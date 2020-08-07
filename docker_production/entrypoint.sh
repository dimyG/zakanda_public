#!/bin/sh
# * Notice that the EOL character of this file must be UNIX style (LF) otherwise you will get an error when the
#   script runs in the container
# * Notice that despite the fact that this file is not in the zakanda_src directory it is executed from the
#   zakanda_src directory so the path to files are relative to zakanda_src and not to the file's position
set -e
# Never push static files from your local environment to your production static files store
# (as defined in production settings), only from deployed commited code
# # python manage.py collectstatic --noinput --clear
gunicorn zakanda.wsgi --bind 0.0.0.0:8000 --timeout 30 --log-level debug
exec "$@"