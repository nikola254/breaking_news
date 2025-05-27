from app.blueprints.main import main_bp
from app.blueprints.news_api import news_api_bp
from app.blueprints.parser_api import parser_api_bp
from app.blueprints.forecast_api import forecast_api_bp
from app.blueprints.external_api import external_api_bp

__all__ = ['main_bp', 'news_api_bp', 'parser_api_bp', 'forecast_api_bp', 'external_api_bp']