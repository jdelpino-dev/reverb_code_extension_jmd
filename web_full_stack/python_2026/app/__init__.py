from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app():
    app = Flask(__name__)

    from app.routes.categories import categories_bp
    from app.routes.listings import listings_bp

    app.register_blueprint(categories_bp)
    app.register_blueprint(listings_bp)

    return app
