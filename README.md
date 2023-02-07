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
**Clone the repository**

Find a place you want the code to live.

    $ git clone git://github.com/optimumtact/sr.ht.git
    $ cd sr.ht

**Deployment**


This has a working docker-compose file, just install docker, docker-compose

Then copy the example env file and adjust for your needs

    cp env.dev.example .env.dev
    nano .env.dev
    
Then start the project with compose
    
    docker-compose up -d

then you can browse to localhost:5000 (by default) to access it

dev builds with docker mount the source directory, if you're using the docker-compose in production, swap to the standard Dockerfile for the image

If it fails to start the first time, just run it again, the db might not have stood all the way up before the web container started

The Docker uses python:3-slim and hivemind for process management, so it obeys the procfile standard, both gunicorn and nginx run in a single container,
as the application was originally intended for a nginx + wsgi hosting and needs to share a storage folder

https://github.com/DarthSim/hivemind

This project is deployed on fly.io for production usage, and should be trivial to get started with flyctl launch (choose the option to create a pg db otherwise the app wont boot because it wont have a DATABASE_URL secret)


## Becoming an admin and bootstrapping initial user

You can become an admin with the management cli script

    docker-compose exec -it web bin/bash
    cd /app
    python manage.py user create {yourusername} {password} {emailaddress}
    python manage.py admin promote {youruser}

## Customization

You can customize the appearance of the site with template overrides. Create a
directory called `overrides` and copy templates from the `templates` directory
into `overrides`. Modify them as you see fit, they will be used instead of the
version from `templates`.

Although I don't know why you would do this when you can just modify source
