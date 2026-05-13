postdeploy: python manage.py migrate && python manage.py build_svg_sprite && manage.py tailwind build && python manage.py collectstatic --noinput
web: gunicorn config.wsgi --log-file -
