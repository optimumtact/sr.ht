FROM python:3.13 AS base

FROM base AS builder

# Builder image
RUN mkdir /install
RUN mkdir /app
ENV PATH="/root/.local/bin:${PATH}"
RUN export DEBIAN_FRONTEND=noninteractive && apt update 
RUN export DEBIAN_FRONTEND=noninteractive && apt-get -yq install gcc python3-dev make curl g++ ffmpeg
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN curl https://github.com/DarthSim/hivemind/releases/download/v1.1.0/hivemind-v1.1.0-linux-amd64.gz -fsL -o hivemind-v1.1.0-linux-amd64.gz && gunzip hivemind-v1.1.0-linux-amd64.gz && chmod u+x hivemind-v1.1.0-linux-amd64

# Set the working directory
WORKDIR /src
# Copy the dependency files
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/venv
RUN uv sync --frozen --no-dev --no-install-project

# Now do the static images
COPY _static /src/_static
COPY scripts /src/scripts
COPY styles /src/styles
COPY Makefile /src/Makefile
COPY tailwind.config.js /src/tailwind.config.js
RUN mkdir /src/static
RUN make install-tailwind && make

# Now the final image
FROM base

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN export DEBIAN_FRONTEND=noninteractive && apt update 
RUN export DEBIAN_FRONTEND=noninteractive && apt-get -yq install nginx postgresql-client ffmpeg
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
COPY --from=builder /src/static /app/static
COPY --from=builder /hivemind-v1.1.0-linux-amd64 .
CMD ["/app/hivemind-v1.1.0-linux-amd64"]

