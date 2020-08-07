web: gunicorn zakanda.wsgi --log-file -
worker_01: python manage.py rqworker emails default --worker-class gutils.models.MyWorker
worker_02: python manage.py rqworker emails default --worker-class gutils.models.MyWorker
scheduler: python manage.py rqscheduler