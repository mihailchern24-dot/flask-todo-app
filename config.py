"""Конфигурация приложения для Render"""
import os
from datetime import timedelta

class Config:
    """Основная конфигурация"""
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    
    # База данных - Render использует PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Исправление формата URL для PostgreSQL (важно для Render)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    # Для локальной разработки (если нет DATABASE_URL)
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///smart_unload.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_PROTECTION = 'strong'
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Пагинация
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))
    
    # Для Production
    PREFERRED_URL_SCHEME = 'https'
    
    # Логирование
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Отладка
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Производительность
    JSONIFY_PRETTYPRINT_REGULAR = False
    JSON_SORT_KEYS = False
