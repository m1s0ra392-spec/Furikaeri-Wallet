"""
WSGI furikaeri-wallet_project for furikaeri-wallet_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'furikaeri-wallet_project.settings')

application = get_wsgi_application()
