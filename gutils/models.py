import logging
from rq import Worker


logger = logging.getLogger(__name__)


class MyWorker(Worker):
    """ Overrides the default rq Worker class in order to close the connection before job execution
     (before forking) so to avoid postgre connection related errors.
    """
    # todo use HerokuWorkerClass (available in rq 0.7)

    def perform_job(self, *args, **kwargs):
        from django.db import connections
        connections.close_all()
        # logger.debug('performing job by MyWorker class')
        super(MyWorker, self).perform_job(*args, **kwargs)
