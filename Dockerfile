FROM python:3.10

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt search portaudio
RUN apt install portaudio19-dev
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./resources /code/resources
COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]