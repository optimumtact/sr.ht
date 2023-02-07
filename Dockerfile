FROM python:3-slim as base

FROM base as builder

# Builder image
RUN mkdir /install
RUN apt-get update && apt-get install -y libpq-dev gcc python3-dev ruby-sass coffeescript make curl
RUN curl https://github.com/DarthSim/hivemind/releases/download/v1.1.0/hivemind-v1.1.0-linux-amd64.gz -fsL -o hivemind-v1.1.0-linux-amd64.gz && gunzip hivemind-v1.1.0-linux-amd64.gz && chmod u+x hivemind-v1.1.0-linux-amd64
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install --prefix="/install" -r /requirements.txt

# Now do the static images
COPY _static /_static
COPY scripts /scripts
COPY styles /styles
COPY Makefile /Makefile
RUN mkdir /static
WORKDIR /
RUN make

# Now the final image
FROM base

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# Copy requirements from builder
COPY --from=builder /install /usr/local
RUN apt-get update && apt-get install -y nginx curl libpq5 && rm -rf /var/lib/apt/lists/*
RUN service nginx stop
WORKDIR /app
# Bundle app sources
COPY Procfile Procfile
COPY srht srht
COPY templates templates
COPY emails emails
COPY manage.py manage.py
COPY nginx/basic.conf /etc/nginx/sites-enabled/default
COPY --from=builder /static /app/static
COPY --from=builder /hivemind-v1.1.0-linux-amd64 .
CMD ["/app/hivemind-v1.1.0-linux-amd64"]

