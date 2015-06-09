# Builds static assets
# Depends on:
# - scss
# - coffeescript
# - inotify-tools
# Run `make` to compile static assets
# Run `make watch` to recompile whenever a change is made

.PHONY: all static watch clean

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
	scss -I styles/ $< $@

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
