# Builds static assets
# Depends on:
# - scss
# - coffeescript
# - inotify-tools
# Run `make` to compile static assets
# Run `make watch` to recompile whenever a change is made

.PHONY: all static watch clean manage

ifeq (manage,$(firstword $(MAKECMDGOALS)))
  MANAGE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(MANAGE_ARGS):;@:)
endif

STYLES:=$(patsubst styles/%.scss,static/%.css,$(wildcard styles/*.scss))
STYLES+=$(patsubst styles/%.css,static/%.css,$(wildcard styles/*.css))
SCRIPTS:=$(patsubst scripts/%.coffee,static/%.js,$(wildcard scripts/*.coffee))
SCRIPTS+=$(patsubst scripts/%.js,static/%.js,$(wildcard scripts/*.js))
_STATIC:=$(patsubst _static/%,static/%,$(wildcard _static/*))

static/%: _static/%
	@mkdir -p static/
	cp $< $@

static/%.css: styles/%.css
	@mkdir -p static/
	cp $< $@

static/%.css: styles/%.scss
	@mkdir -p static/
	sassc -I styles/ $< $@

static/%.js: scripts/%.js
	@mkdir -p static/
	cp $< $@

static/%.js: scripts/%.coffee
	@mkdir -p static/
	coffee -m -o static/ -c $<

static: $(STYLES) $(SCRIPTS) $(_STATIC)

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

manage:
	docker compose -f docker-compose-dev.yml exec -it web /venv/bin/python /app/manage.py $(MANAGE_ARGS)

destroy:
	docker compose -f docker-compose-dev.yml down --volumes

psql:
	docker compose -f docker-compose-dev.yml exec db psql -U hello_flask hello_flask_dev
test:
	uv run pytest tests/
