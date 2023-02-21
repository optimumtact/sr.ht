from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(engine_options={"pool_pre_ping":True})