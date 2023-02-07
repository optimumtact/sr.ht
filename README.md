(fork of [sr.ht](https://github.com/SirCmpwn/sr.ht))

Private file hosting with python/nginx

## Differences from upstream

* Fixed a few instances where page redirects would take you to the local IP of the sr.ht instance, which obviously isn't connectable from outside.
* Removed most hardcoded branding and moved it to config strings.
* Switched to simplex bootstrap theme
* Some minor style fixes
* Improvements to administration with some cli scripting
* Removed the anime branding and replaced with a more sfw icon
* Being able to delete files from the web interface

## Running the site

Quick overview:

1. Install dependencies
2. Set up dependencies
3. Clone the repository
7. Configure the site
8. Compile static assets
9. Set up SQL
10. Deployment

**Install the dependencies**

You'll need these things

* Python 3 (python)
* PostgreSQL (postgresql)
* scss (ruby-sass)

The following ubuntu/debian packages would also be useful/required for some pip dependencies, equivalents should exist on your system

    apt-get install build-essential libssl-dev libffi-dev python3-dev

**Clone the repository**

Find a place you want the code to live.

    $ git clone git://github.com/optimumtact/sr.ht.git
    $ cd sr.ht

**Deployment**

This has a working docker-compose file, just install docker, docker-compose and run

    docker-compose up -d

then you can browse to localhost:8080 (by default) to access it

dev builds currently require a full container rebuild, so I might eventually add a version that mounts the source directories instead for ease of use

If it fails to start the first time, just run it again, the db might not have stood all the way up before the web container started

The Docker uses python:3-slim and hivemind for process management, so it obeys the procfile standard, both gunicorn and nginx run in a single container,
as the application was originally intended for a nginx + wsgi hosting and needs to share a storage folder

https://github.com/DarthSim/hivemind

This project is deployed on fly.io for production usage


## Becoming an admin and bootstrapping initial user

You can become an admin with the management cli script

    $ cd /path/to/sr.ht/
    $ python manage.py user create {yourusername} {password} {emailaddress}
    $ python manage.py admin promote {youruser}

## SQL Stuff

We use alembic for schema migrations between versions. The first time you run the
application, the schema will be created. However, you need to tell alembic that 
you're already on the latest version

    $ cd /path/to/sr.ht
    $ bin/activate
    $ bin/alembic -c alembic.ini stamp head

Congrats, you've got a schema in place. Run `alembic upgrade head` after pulling
the code to update your schema to the latest version. Do this before you restart
the site.

## Customization

You can customize the appearance of the site with template overrides. Create a
directory called `overrides` and copy templates from the `templates` directory
into `overrides`. Modify them as you see fit, they will be used instead of the
version from `templates`.
