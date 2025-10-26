from typing import Optional, Union

from flask import Flask

from dotenv import load_dotenv

from .extensions import db, login_manager, migrate


def create_app(config_object: Optional[Union[str, type]] = None) -> Flask:
    """mini CRM プロジェクトのアプリケーションファクトリ。"""
    load_dotenv()

    app = Flask(__name__)
    config_path = config_object or "config.Config"
    app.config.from_object(config_path)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from .models import User  # noqa: WPS433

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        if not user_id.isdigit():
            return None
        return db.session.get(User, int(user_id))

    from .blueprints.auth.routes import auth_bp
    from .blueprints.core.routes import core_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)

    return app
