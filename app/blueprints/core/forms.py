from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional


class PropertyForm(FlaskForm):
    name = StringField("物件名", validators=[DataRequired()])
    address = StringField("住所", validators=[DataRequired()])
    note = TextAreaField("備考", validators=[Optional()])
    submit = SubmitField("登録")


class TenantForm(FlaskForm):
    name = StringField("氏名", validators=[DataRequired()])
    email = StringField("メールアドレス", validators=[DataRequired(), Email()])
    phone = StringField("電話番号", validators=[Optional()])
    submit = SubmitField("登録")


class LeaseForm(FlaskForm):
    property_id = SelectField("物件", coerce=int, validators=[DataRequired()])
    tenant_id = SelectField("入居者", coerce=int, validators=[DataRequired()])
    rent = DecimalField("賃料", places=2, rounding=None, validators=[DataRequired()])
    start_date = DateField("契約開始日", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("契約終了日", validators=[Optional()], format="%Y-%m-%d")
    status = SelectField(
        "状態",
        choices=[("active", "契約中"), ("ended", "終了")],
        validators=[DataRequired()],
        default="active",
    )
    submit = SubmitField("登録")


class DeleteForm(FlaskForm):
    id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("削除")
