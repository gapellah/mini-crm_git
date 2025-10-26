import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# Alembic の設定オブジェクトで、
# 使用中の .ini ファイル内の値へアクセスするためのものです。
config = context.config

# ログ設定ファイルを読み込んで Python のロギングを設定します。
# 実質的にこの行がロガーを構成します。
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # Flask-SQLAlchemy<3 と Alchemical に対応した呼び出し
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # Flask-SQLAlchemy>=3 に対応した呼び出し
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# モデルの MetaData オブジェクトをここに追加
# autogenerate を利用するための設定
# 例: from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# env.py の要件に応じて定義されたその他の設定値は
# 次のように取得できます:
# my_important_option = config.get_main_option("my_important_option")
# ... など。


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """'offline' モードでマイグレーションを実行します。

    URL だけでコンテキストを設定し、Engine は使いません
    （ここで Engine を用意しても問題ありません）。
    Engine を作成しないため、DBAPI がなくても構いません。

    context.execute() の呼び出しは指定された文字列をスクリプト出力に流します。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """'online' モードでマイグレーションを実行します。

    この場合は Engine を作成し、
    コンテキストに接続を関連付ける必要があります。
    """

    # このコールバックは不要な自動マイグレーションの生成を防ぐためのものです
    # スキーマに変更がない場合に適用されます
    # 参考: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
