postdeploy: python manage.py migrate && python manage.py build_svg_sprite && python manage.py collectstatic --noinput
web: gunicorn conf.wsgi --config gunicorn.conf.py --log-file - --capture-output
worker: celery -A conf worker --loglevel=info --concurrency=2
