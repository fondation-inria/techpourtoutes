postdeploy: python manage.py migrate && python manage.py build_svg_sprite && python manage.py tailwind build && python manage.py collectstatic --noinput
web: gunicorn conf.wsgi --log-file -
