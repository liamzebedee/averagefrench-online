import os

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'tweets.db')
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # Database settings
    DATABASE_TIMEOUT = 20.0
    
    # Session settings
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_RELOADER = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_RELOADER = False
    SESSION_COOKIE_SECURE = True
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    USE_RELOADER = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
