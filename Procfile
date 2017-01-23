web: gunicorn oh_data_source.wsgi --log-file=-
worker: celery -A oh_data_source worker --without-gossip --without-mingle --without-heartbeat
