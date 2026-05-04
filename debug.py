import os
from srht.app import app
from srht.common import validate_storage_directory
from srht.config import _cfgi

app.static_folder = os.path.join(os.getcwd(), "static")

print(f"Static folder is {app.static_folder}")
validate_storage_directory()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=_cfgi("port"), debug=True)
