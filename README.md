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

## Deployment
This has a working docker-compose file, just install docker and docker-compose

Then copy the example env file and adjust for your needs

    cp env.dev.example .env
    nano .env
    
Soft link the production docker-compose to docker-compose.yml
    ln -s docker-compose-prod.yml docker-compose.yml

Then start the project with compose
    docker-compose up -d

then you can browse to localhost:5000 (by default) to access it

a production deployment shoudl configure various options, but i dont have time to document them

## Dev deployment
This is setup to run out of the box on localhost:5000 using the sample env file and the docker dev template.

You can run 
```bash
make build
make dev
```
to spin the project up mounted into a dev container for easy editing.



** About the production deployment **
The compose file for prod uses hivemind for process management, so it obeys the procfile standard, both gunicorn and nginx run in a single container as the application was originally intended for a nginx + wsgi hosting and needs to share a storage folder

https://github.com/DarthSim/hivemind

## Bootstrapping initial user
If you visit the site and there are no users in the user table it will send you on a setup flow for an admin user, the app secret key is required to complete this flow, to prevent driveby users creating the first user

## Task management
The application uses a task management system for background job processing. Tasks are managed through the `manage.py` script.

To run tasks:

    python manage.py task run

This will start the task worker that processes queued background jobs. Tasks are typically used for operations that don't need to complete immediately, such as file processing, cleanup operations, and other asynchronous work.

## Customization

You can customize the appearance of the site with template overrides. Create a
directory called `overrides` and copy templates from the `templates` directory
into `overrides`. Modify them as you see fit, they will be used instead of the
version from `templates`.

Although I don't know why you would do this when you can just modify source
