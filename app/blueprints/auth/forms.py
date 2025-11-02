"""ログインとユーザー登録用フォームの定義をまとめたモジュール。"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    email = EmailField("メールアドレス", validators=[DataRequired(), Email()])
    password = PasswordField("パスワード", validators=[DataRequired()])
    submit = SubmitField("ログイン")


class RegisterForm(FlaskForm):
    email = EmailField(
        "メールアドレス",
        validators=[
            DataRequired(),
            Email(),
        ],
    )
    password = PasswordField(
        "パスワード",
        validators=[DataRequired(), Length(min=6)],
    )
    confirm_password = PasswordField(
        "パスワード（確認）",
        validators=[
            DataRequired(),
            EqualTo("password", message="パスワードが一致しません。"),
        ],
    )
    role = StringField("権限（任意）")
    submit = SubmitField("登録")
