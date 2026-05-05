# Builds static assets
# Depends on:
# - tailwindcss CLI
# - coffeescript
# - inotify-tools
# Run `make` to compile static assets
# Run `make watch` to recompile whenever a change is made

.PHONY: all static watch clean manage install-tailwind
.DEFAULT_GOAL := all

ifeq (manage,$(firstword $(MAKECMDGOALS)))
  MANAGE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(MANAGE_ARGS):;@:)
endif

TAILWIND_VERSION:=v3.4.17
TAILWIND_BIN:=bin/tailwindcss
UNAME_S:=$(shell uname -s)
UNAME_M:=$(shell uname -m)

ifeq ($(UNAME_S),Linux)
	ifeq ($(UNAME_M),x86_64)
		TAILWIND_RELEASE:=tailwindcss-linux-x64
	else ifeq ($(UNAME_M),aarch64)
		TAILWIND_RELEASE:=tailwindcss-linux-arm64
	else
		$(error Unsupported Linux architecture for tailwindcss: $(UNAME_M))
	endif
else ifeq ($(UNAME_S),Darwin)
	ifeq ($(UNAME_M),x86_64)
		TAILWIND_RELEASE:=tailwindcss-macos-x64
	else ifeq ($(UNAME_M),arm64)
		TAILWIND_RELEASE:=tailwindcss-macos-arm64
	else
		$(error Unsupported macOS architecture for tailwindcss: $(UNAME_M))
	endif
else
	$(error Unsupported OS for tailwindcss: $(UNAME_S))
endif

STYLES:=$(filter-out static/main.css,$(patsubst styles/%.css,static/%.css,$(wildcard styles/*.css)))
STYLES+=static/main.css
SCRIPTS:=$(patsubst scripts/%.coffee,static/%.js,$(wildcard scripts/*.coffee))
SCRIPTS+=$(patsubst scripts/%.js,static/%.js,$(wildcard scripts/*.js))
_STATIC:=$(patsubst _static/%,static/%,$(wildcard _static/*))

TAILWIND_CONTENT:=$(shell find templates -type f -name '*.html')

static/%: _static/%
	@mkdir -p static/
	cp $< $@

static/%.css: styles/%.css
	@mkdir -p static/
	cp $< $@

$(TAILWIND_BIN):
	@mkdir -p bin
	curl -fsSL https://github.com/tailwindlabs/tailwindcss/releases/download/$(TAILWIND_VERSION)/$(TAILWIND_RELEASE) -o $(TAILWIND_BIN)
	chmod +x $(TAILWIND_BIN)

static/main.css: styles/main.css tailwind.config.js $(TAILWIND_CONTENT) $(TAILWIND_BIN)
	@mkdir -p static/
	$(TAILWIND_BIN) -i styles/main.css -o static/main.css --minify

static/%.js: scripts/%.js
	@mkdir -p static/
	cp $< $@

static/%.js: scripts/%.coffee
	@mkdir -p static/
	coffee -m -o static/ -c $<

static: $(STYLES) $(SCRIPTS) $(_STATIC)

install-tailwind: $(TAILWIND_BIN)

all: static
	echo $(STYLES)
	echo $(SCRIPTS)

clean:
	rm -rf static

watch:
	while inotifywait \
		-e close_write scripts/ \
		-e close_write styles/ \
		-e close_write _static/; \
		do make; done

build:
	docker compose -f docker-compose-dev.yml build

dev:
	UID=$$(id -u) GID=$$(id -g) docker compose -f docker-compose-dev.yml up

task:
	docker compose -f docker-compose-dev.yml exec web /venv/bin/python /app/manage.py task run -c 300
manage:
	docker compose -f docker-compose-dev.yml exec -it web /venv/bin/python /app/manage.py $(MANAGE_ARGS)

destroy:
	docker compose -f docker-compose-dev.yml down --volumes

psql:
	docker compose -f docker-compose-dev.yml exec db psql -U hello_flask hello_flask_dev
schema:
	docker compose -f docker-compose-dev.yml exec db pg_dump -U hello_flask -n public -O -x --schema-only hello_flask_dev
test:
	uv run pytest tests/
