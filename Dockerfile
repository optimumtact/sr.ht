FROM python:3.10 AS base

FROM base AS builder

# Builder image
RUN mkdir /install
RUN mkdir /app
ENV PATH="/root/.local/bin:${PATH}"
RUN export DEBIAN_FRONTEND=noninteractive && apt update 
RUN export DEBIAN_FRONTEND=noninteractive && apt-get -yq install postgresql gcc python3-dev sassc make curl g++ ffmpeg pipx
RUN curl https://github.com/DarthSim/hivemind/releases/download/v1.1.0/hivemind-v1.1.0-linux-amd64.gz -fsL -o hivemind-v1.1.0-linux-amd64.gz && gunzip hivemind-v1.1.0-linux-amd64.gz && chmod u+x hivemind-v1.1.0-linux-amd64
RUN pipx install poetry
RUN pipx inject poetry poetry-plugin-bundle

# Set the working directory
WORKDIR /src
# Copy the Poetry configuration files
COPY pyproject.toml poetry.lock* ./
RUN poetry bundle venv --python=/usr/bin/python3 --only=main /venv

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

RUN export DEBIAN_FRONTEND=noninteractive && apt update 
RUN export DEBIAN_FRONTEND=noninteractive && apt-get -yq install nginx postgresql ffmpeg
# Copy requirements from builder
COPY --from=builder /venv /venv
WORKDIR /app
# Bundle app sources
COPY Procfile Procfile
COPY srht srht
COPY templates templates
COPY emails emails
COPY manage.py manage.py
COPY db_schema/updates /migrations
COPY nginx/basic.conf /etc/nginx/sites-available/default
COPY --from=builder /static /app/static
COPY --from=builder /hivemind-v1.1.0-linux-amd64 .
CMD ["/app/hivemind-v1.1.0-linux-amd64"]

