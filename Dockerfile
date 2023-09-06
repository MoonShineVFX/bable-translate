FROM python:3.10

WORKDIR /bot

ADD requirements.txt /tmp
RUN apt-get update -y && \
    apt-get install -y python3-pip
RUN pip3 install -r /tmp/requirements.txt

ADD . /bot

ENV FLASK_APP=bot.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=0
CMD ["flask","run","--host=0.0.0.0"]
