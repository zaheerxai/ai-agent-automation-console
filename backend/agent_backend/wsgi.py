import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application

# 1. Add the 'backend' directory to the Python path
# This allows 'import agent_backend' to work even if we are at the repository root
path_to_backend = Path(__file__).resolve().parent.parent
sys.path.append(str(path_to_backend))

# 2. Update the settings module path to be absolute from the backend folder
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agent_backend.settings')

application = get_wsgi_application()
app = application # Vercel entry point