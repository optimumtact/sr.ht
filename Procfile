# Modify this Procfile to fit your needs
app: /venv/bin/python -m gunicorn -w 4 -b 0.0.0.0:8080 --timeout 300 --graceful-timeout 300 --keep-alive 300 srht.app:app
web: nginx -g 'daemon off;'
