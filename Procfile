postdeploy: python manage.py migrate && python manage.py build_svg_sprite && python manage.py collectstatic --noinput && python manage.py import_schools --if-empty && python manage.py import_higher_ed_schools --if-empty
web: gunicorn conf.wsgi --config gunicorn.conf.py --log-file - --capture-output
worker: celery -A conf worker --loglevel=info --concurrency=2
