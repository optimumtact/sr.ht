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

You'll need these things (Arch packages in parenthesis, some from AUR):

* Python 3 (python)
* PostgreSQL (postgresql)
* scss (ruby-sass)

The following ubuntu/debian packages would also be useful, equivalents should exist on your system

    apt-get install build-essential libssl-dev libffi-dev python3-dev

And for the rest

    pip install -r requirements.txt

Use the packages your OS provides, or build them from source.

**Set up services**

I'll leave you to set up PostgreSQL however you please. Prepare a connection
string that looks like this when you're done:

    postgresql://username:password@hostname:port/database

We need to be able to create/alter/insert/update/delete in the database you
give it.

**Clone the repository**

Find a place you want the code to live.

    $ git clone git://github.com/optimumtact/sr.ht.git
    $ cd sr.ht

**Configure the site**

    $ cp alembic.ini.example alembic.ini
    $ cp config.ini.example config.ini

Edit config.ini and alembic.ini to your liking.

**Compile static assets**

    $ make

Run this again whenever you pull the code.

**Deployment**

What you do from here depends on your site-specific configuration. If you just
want to run the site for development, run

    python app.py

To run it in production, you probably want to use gunicorn behind an nginx proxy.
There's a sample nginx config in the configs/ directory here, but you'll probably
want to tweak it to suit your needs. Here's how you can run gunicorn, put this in
your init scripts:

    gunicorn app:app -b 127.0.0.1:8000

Note: you may have to install gunicorn first with

    pip install gunicorn

The `-b` parameter specifies an endpoint to use. You probably want to bind this to
localhost and proxy through from nginx. I'd also suggest blocking the port you
choose from external access. It's not that gunicorn is *bad*, it's just that nginx
is better.

When running in a production enviornment, run `python app.py` at least once and
then read the SQL stuff below before you let it go for good.

nginx configuration is available in `nginx/`, modify it to suit your environment.
**nginx is required to run this website properly**.

## Becoming an admin

You can become an admin with the management cli script

    $ cd /path/to/sr.ht/
    $ python manage.py user approve {youruser}
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
