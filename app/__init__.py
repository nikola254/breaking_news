from flask import Flask
from config import Config

app = Flask(__name__, static_folder='static', static_url_path='')
app.config.from_object(Config)

# Импортируем и регистрируем Blueprint-модули
from app.blueprints import main_bp, news_api_bp, parser_api_bp, forecast_api_bp, external_api_bp

app.register_blueprint(main_bp)
app.register_blueprint(news_api_bp)
app.register_blueprint(parser_api_bp)
app.register_blueprint(forecast_api_bp)
app.register_blueprint(external_api_bp)

# Импортируем модели после инициализации приложения
from app import models