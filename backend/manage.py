"""Django's command-line tool for the Meta-Fut A.I API. Start the server with:
    python backend/manage.py runserver
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "metafut_api.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
