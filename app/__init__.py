from flask import Flask
from config import Config

app = Flask(__name__, static_folder='static', static_url_path='')
app.config.from_object(Config)

from app import routes, models