import pytest
from django.db import connections
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from zakanda.settings import pg_zakanda_db_password, host

print ("executing conftest...")


def run_sql(sql):
    for connection in connections.all():
        connection.close()
    conn = psycopg2.connect(dbname="postgres", user="postgres", password=pg_zakanda_db_password, host=host)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()


@pytest.fixture(scope='session')
def django_db_setup():
    """
    we copy the projects database (schema and data) so that all tests run on it
    """
    from django.conf import settings

    settings.DATABASES['default']['NAME'] = 'zakanda_copy_for_test'
    run_sql('DROP DATABASE IF EXISTS zakanda_copy_for_test')
    run_sql('CREATE DATABASE zakanda_copy_for_test TEMPLATE zakanda_db')
    print ("executing django_db_setup...")
    # run_sql('CREATE DATABASE zakanda_copy_for_test')

    # db_name = connection.settings_dict['NAME']
    # print("current db name: ", db_name)
    # os.system("pg_dump -U postgres --schema-only zakanda_db > C:\dump_file")
    # os.system('psql -U postgres zakanda_copy_for_test < C:\dump_file')
    yield

    for connection in connections.all():
        connection.close()
    run_sql('DROP DATABASE zakanda_copy_for_test')


# @pytest.yield_fixture(autouse=True, scope='session')
# def test_suite_cleanup_thing():
#     # setup
#     yield
#     # teardown - put your command here