FROM python:2.7.17-buster

WORKDIR /usr/src/zakanda_src

# The project needs to use numpy==1.16.0 (instead of 1.10.1) for pandas==0.17.1 to work properly in this container
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update -y
RUN apt-get install -y binutils libproj-dev gdal-bin

# There is a bug in django 1.8 that has to do with decoding the geos version. A solution is to modify slightly the
# site-packages/django/contrib/gis/geos/libgeos.py file
RUN sed -i "s/ver = geos_version().decode().*/ver = geos_version().decode().split(' ')[0]/" /usr/local/lib/python2.7/site-packages/django/contrib/gis/geos/libgeos.py

# These are non essential libraries
# RUN apt-get install -y net-tools

COPY ./ ./

RUN chmod +x docker_aws_ECS/entrypoint.sh
ENTRYPOINT ["docker_aws_ECS/entrypoint.sh"]

#CMD [ "gunicorn", "zakanda.wsgi", "--bind", "0.0.0.0:8000"]