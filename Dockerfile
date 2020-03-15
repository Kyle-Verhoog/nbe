FROM ubuntu:latest

RUN apt-get update && apt-get -y install cron python3-pip
RUN pip3 install pipenv

COPY . /code
WORKDIR /code
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
RUN pipenv install --system

COPY nbe-cron /etc/cron.d/nbe-cron
RUN chmod 0644 /etc/cron.d/nbe-cron
CMD ["cron", "-f"]
