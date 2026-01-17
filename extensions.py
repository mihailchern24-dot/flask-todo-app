"""Расширения Flask для Render"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Инициализация расширений
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()