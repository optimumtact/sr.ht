from flask_sqlalchemy import SQLAlchemy

from srht.config import _cfg

db = SQLAlchemy(engine_options={"pool_pre_ping": True})
