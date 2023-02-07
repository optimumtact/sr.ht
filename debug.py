from srht.app import app
from srht.config import _cfg, _cfgi

import os

app.static_folder = os.path.join(os.getcwd(), "/app/static")
print(app.static_folder)
import os
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
