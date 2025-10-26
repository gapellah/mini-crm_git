from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional

from ...models import LeaseStatus


class PropertyForm(FlaskForm):
    name = StringField("物件名", validators=[DataRequired()])
    address = StringField("住所", validators=[DataRequired()])
    note = TextAreaField("備考", validators=[Optional()])
    submit = SubmitField("物件を保存")


class DeletePropertyForm(FlaskForm):
    property_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("削除")


class TenantForm(FlaskForm):
    property_id = SelectField("物件", coerce=int, validators=[DataRequired()])
    unit_number = StringField("号室", validators=[DataRequired()])
    name = StringField("氏名", validators=[DataRequired()])
    email = StringField("メールアドレス", validators=[DataRequired(), Email()])
    phone = StringField("電話番号", validators=[Optional()])
    submit = SubmitField("入居者を保存")


LEASE_STATUS_CHOICES = [
    (LeaseStatus.ACTIVE, "契約中"),
    (LeaseStatus.PENDING, "準備中"),
    (LeaseStatus.TERMINATED, "解約済み"),
]


class LeaseForm(FlaskForm):
    property_id = SelectField("物件", coerce=int, validators=[DataRequired()])
    unit_number = SelectField("号室", validators=[DataRequired()])
    lease_id = HiddenField()
    tenant_id = HiddenField(validators=[DataRequired()])
    tenant_display = StringField("入居者", render_kw={"readonly": True})
    rent = DecimalField("賃料（万円）", places=1, rounding=None, validators=[DataRequired()])
    start_date = DateField("契約開始日", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("契約終了日", validators=[Optional()], format="%Y-%m-%d")
    status = SelectField(
        "状態",
        choices=LEASE_STATUS_CHOICES,
        validators=[DataRequired()],
    )
    submit = SubmitField("契約を保存")


class DeleteTenantForm(FlaskForm):
    tenant_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("削除")
