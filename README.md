# Mini CRM (Flask)

転職ポートフォリオ向けのシンプルな物件・契約管理アプリです。Flask と SQLAlchemy を使い、物件・入居者・契約の情報を一元管理できる最小限の構成になっています。

## 主な機能
- Flask-Login と Flask-WTF によるユーザー登録・ログイン
- 物件 / 入居者 / 契約の一覧表示と登録
- SQLAlchemy + Flask-Migrate を利用したデータベース管理
- pytest を用いたスモークテスト

## セットアップ
1. 依存関係のインストール  
   `python3 -m pip install -r requirements.txt`
2. 環境変数の設定  
   `.env.example` を `.env` にコピーし、`SECRET_KEY` と `DATABASE_URL` を必要に応じて調整してください。
3. マイグレーションの初期化と適用  
   ```
   export FLASK_APP=wsgi        # Windows: set FLASK_APP=wsgi
   flask db init || true        # 既に初期化済みならスキップされます
   flask db migrate -m "init"
   flask db upgrade
   ```

## アプリの起動
```
flask --app wsgi run --debug
```

## テスト
```
python3 -m pytest -q
```

## ディレクトリ構成
- `app/` Flask アプリケーション本体
- `migrations/` データベースマイグレーション
- `tests/` pytest のテストコード
- `wsgi.py` エントリーポイント
- `config.py` 設定クラス
- `requirements.txt` 依存パッケージの一覧
