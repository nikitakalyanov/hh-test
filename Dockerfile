FROM python:3.9-buster

COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

COPY test_hh_api.py /test_hh_api.py

ENTRYPOINT /test_hh_api.py
