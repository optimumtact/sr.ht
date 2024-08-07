import os
from pathlib import Path

from srht.app import app
from srht.common import validate_storage_directory
from srht.config import _cfgi

app.static_folder = os.path.join(os.getcwd(), "static")
print(f"Static folder is {app.static_folder}")
validate_storage_directory()
if __name__ == "__main__":
    app.run(host="localhost", port=_cfgi("port"), debug=True)
