from srht.app import app
from srht.config import _cfgi, _cfg
import os
from pathlib import Path

app.static_folder = os.path.join(os.getcwd(), "static")
print(f"Static folder is {app.static_folder}")
thumbnaildir = Path(os.path.join(_cfg("storage"), "thumbnails"))
os.makedirs(thumbnaildir, exist_ok=True)
if __name__ == '__main__':
    app.run(host="localhost", port=_cfgi('port'), debug=True)
