import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "timetracker.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_FROM = os.getenv("MAIL_FROM")
    SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
    INIT_ENABLED = os.getenv("INIT_ENABLED", "false").lower() == "true"
    INIT_TOKEN = os.getenv("INIT_TOKEN")
    AUTO_SEED_ON_EMPTY = os.getenv("AUTO_SEED_ON_EMPTY", "true").lower() == "true"
    SHOW_RESET_LINK = os.getenv("SHOW_RESET_LINK", "false").lower() == "true"
    
