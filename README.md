# Single-database configuration for Flask.
# 
# # Mini CRM (Flask)
# Flask 製の物件・契約管理ミニ CRM です。小規模チームが物件・入居者・契約の CRUD をひとつの UI で扱えるようにする最小構成のサンプルアプリケーションを想定しています。
# 
# セットアップ手順
# python -m pip install -U pip
# pip install -r requirements.txt
# export FLASK_APP=wsgi            # Windows: set FLASK_APP=wsgi
# flask db init || true            # 既に初期化済みなら無視されます
# flask db migrate -m "init"
# flask db upgrade
# pytest -q
# 
# アプリの起動
# flask --app wsgi run --debug
# 
# (コードテスト
# python3 -m pytest -q )  
# 
#
# テストアドレス これでログインしてみてください
#  test1@test.com
#  1234ab
# 
# 
# 
# 
# 
# ディレクトリ構成
#  mini-crm/
#   app/                   Flask アプリケーション本体
#     __init__.py          アプリケーションファクトリの定義
#     extensions.py        拡張（SQLAlchemy など）の初期化
#     models.py            DB モデル定義
#     blueprints/          認証・メイン機能の Blueprint 群
#       auth/
#         __init__.py
#         routes.py        認証系ルート
#         forms.py         ログイン / 登録フォーム
#       core/
#         __init__.py
#         routes.py        物件・入居者・契約のルート
#         forms.py         各種 CRUD フォーム
#     templates/           Jinja2 テンプレート
#       base.html          共通レイアウト
#       index.html         ダッシュボード
#       auth/
#         login.html        ログインフォーム
#         register.html     新規ユーザー登録フォーム
#       core/
#         properties_list.html  物件一覧テーブル
#         property_form.html    物件の新規作成・編集フォーム
#         tenants_list.html     入居者一覧
#         tenant_form.html      入居者の新規作成・編集フォーム
#         leases_list.html      契約一覧
#         lease_form.html       契約の新規作成フォーム
#     static/              静的ファイル置き場
#   migrations/            Flask-Migrate のメタデータとリビジョン
#   tests/                 pytest のテストコード
#     test_smoke.py
#   config.py              環境別設定クラス
#   wsgi.py                デプロイ用エントリーポイント
#   requirements.txt       依存パッケージ
#   .env.example           環境変数テンプレート
