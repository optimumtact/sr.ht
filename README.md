# sr.ht

Private file hosting for you and your friends.

![](https://sr.ht/9087.png)

I run a private instance of sr.ht *at* [sr.ht](https://sr.ht). You can request
an invite if you know me personally. Otherwise, here are the setup instructions
to run it on your own infrastructure:

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
* Flask (python-flask)
* SQLAlchemy (python-sqlalchemy)
* Flask-Login (python-flask-login)
* psycopg2 (python-psycopg2)
* bcrypt (python-bcrypt)

Use the packages your OS provides, or build them from source.

**Set up services**

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

**Configure the site**

    $ cp alembic.ini.example alembic.ini
    $ cp config.ini.example config.ini

Edit config.ini and alembic.ini to your liking.

**Compile static assets**

    $ make

Run this again whenever you pull the code.

**Deployment**

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

## Becoming an admin

You can become an admin like so:

    $ cd /path/to/sr.ht/
    $ source bin/activate
    $ python
    >>> from srht.database import db
    >>> from srht.objects import User
    >>> from datetime import datetime
    >>> u = User.query.filter(User.username == "your username").first()
    >>> u.approved = True # approve yourself
    >>> u.approvalDate = datetime.now()
    >>> u.admin = True # make yourself an admin
    >>> db.commit()

## SQL Stuff

We use alembic for schema migrations between versions. The first time you run the
application, the schema will be created. However, you need to tell alembic about
it. Run the application at least once, then:

    $ cd /path/to/sr.ht/
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

## Customization

You can customize the appearance of the site with template overrides. Create a
directory called `overrides` and copy templates from the `templates` directory
into `overrides`. Modify them as you see fit, they will be used instead of the
version from `templates`.
