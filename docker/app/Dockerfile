FROM ubuntu:22.04

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ARG MEDIA_ROOT
ENV MEDIA_ROOT $MEDIA_ROOT
ARG STATIC_ROOT
ENV STATIC_ROOT $STATIC_ROOT
ENV DEBIAN_FRONTEND noninteractive

RUN mkdir /code
RUN mkdir -p "$MEDIA_ROOT"

RUN apt-get update

# Install PostgreSQL 13
RUN apt-get install -y gnupg wget lsb-release software-properties-common
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add -
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" > /etc/apt/sources.list.d/postgres.list
RUN apt-get update
RUN apt-get install -y python3.10 python3-pip libpython3.10-dev \
	postgresql-client-common postgresql-client libpq-dev \
	gettext git-core


# Geodjango dependencies
RUN apt-get install -y libproj-dev gdal-bin
RUN apt-get install -y nodejs yarnpkg

RUN ln -fs /usr/bin/python3 /usr/bin/python

RUN python3 -m pip install --upgrade pip
RUN pip install wheel
RUN pip install django-queryset-csv
RUN pip install freezegun
COPY requirements.txt requirements-prod.txt /code/
RUN pip install -r /code/requirements-prod.txt -r /code/requirements.txt

# Install ipython for convenience
RUN pip install ipython

RUN mkdir -p /code/analytics/client
COPY package.json yarn.lock /code/
COPY analytics/client/package.json analytics/client/yarn.lock /code/analytics/client/

WORKDIR /code
RUN yarnpkg install
WORKDIR /code/analytics/client
RUN yarnpkg install

COPY . /code/
# Build the analytics frontend bundle
RUN yarnpkg build

WORKDIR /code
RUN ./manage.py collectstatic --no-input
RUN ./manage.py compilemessages
COPY ./docker/app/docker-entrypoint.sh /
COPY ./docker/app/wait-for-it.sh /
RUN mkdir /docker-entrypoint.d
COPY ./docker/app/scripts/*.sh /docker-entrypoint.d
ENTRYPOINT ["/bin/bash", "/docker-entrypoint.sh"]
