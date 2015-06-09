# sr.ht

Private file hosting.

![](https://sr.ht/fda.png)

I run a private instance of sr.ht *at* [sr.ht](https://sr.ht). If you aren't
already friends with me and you want to use it, you have to deploy your own
sr.ht instance. Instructions follow:

## Running the site

Quick overview:

1. Install Python 3, virtualenv, PostgreSQL
2. Set up aforementioned things
3. Clone the repository
4. Activate the virtualenv
5. Install pip requirements
7. Configure the site
8. Compile static assets
9. SQL
10. Site configuration

**Install the dependencies**

You'll need these things:

* Python 3
* virtualenv
* PostgreSQL
* scss

Use the packages your OS provides, or build them from source.

**Set up services**

Do a quick sanity check on all of those things.

    $ python3 --version
      Python 3.4.1
    $ pip --version
      pip 1.5.6 from /usr/lib/python3.4/site-packages (python 3.4)
    $ virtualenv --version
      1.11.6
    $ psql --version
      psql (PostgreSQL) 9.3.4

YMMV if you use versions that differ from these.

I'll leave you to set up PostgreSQL however you please. Prepare a connection
string that looks like this when you're done:

    postgresql://username:password@hostname:port/database

The connection string I use on localhost is this:

    postgresql://postgres@localhost/sr.ht

We need to be able to create/alter/insert/update/delete in the database you
give it.

**Clone the repository**

Find a place you want the code to live.

    $ git clone git://github.com/SirCmpwn/sr.ht.git
    $ cd sr.ht

**Activate virtualenv**

    $ virtualenv --no-site-packages .
    $ source bin/activate

If you're like me and are on a system where `python3` is not the name of your
Python executable, use `--python=somethingelse` to fix that.

**pip requirements**

    $ pip install -r requirements.txt

**Configure the site**

    $ cp alembic.ini.example alembic.ini
    $ cp config.ini.example config.ini

Edit config.ini and alembic.ini to your liking.

**Compile static assets**

    $ make

Run this again whenever you pull the code.

**Site Configuration**

What you do from here depends on your site-specific configuration. If you just
want to run the site for development, you can source the virtualenv and run

    python app.py

To run it in production, you probably want to use gunicorn behind an nginx proxy.
There's a sample nginx config in the configs/ directory here, but you'll probably
want to tweak it to suit your needs. Here's how you can run gunicorn, put this in
your init scripts:

    /path/to/sr.ht/bin/gunicorn app:app -b 127.0.0.1:8000

The `-b` parameter specifies an endpoint to use. You probably want to bind this to
localhost and proxy through from nginx. I'd also suggest blocking the port you
choose from external access. It's not that gunicorn is *bad*, it's just that nginx
is better.

When running in a production enviornment, run `python app.py` at least once and
then read the SQL stuff below before you let it go for good.

nginx configuration is available in `nginx/`, modify it to suit your environment.
**nginx is required to run sr.ht properly**.

## SQL Stuff

We use alembic for schema migrations between versions. The first time you run the
application, the schema will be created. However, you need to tell alembic about
it. Run the application at least once, then:

    $ cd /path/to/truecraft.io/
    $ source bin/activate
    $ python
    >>> from alembic.config import Config
    >>> from alembic import command
    >>> alembic_cfg = Config("alembic.ini")
    >>> command.stamp(alembic_cfg, "head")
    >>> exit()

Congrats, you've got a schema in place. Run `alembic upgrade head` after pulling
the code to update your schema to the latest version. Do this before you restart
the site.
