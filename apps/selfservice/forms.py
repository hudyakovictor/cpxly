from django import forms
from .claim_engine import InvalidClaim, normalize


class CompanyForm(forms.Form):
    name = forms.CharField(label="Название компании", max_length=200)


class ClaimForm(forms.Form):
    creditor = forms.CharField(label="Ваша компания", max_length=200)
    debtor = forms.CharField(label="Заказчик / адресат", max_length=200)
    contract_number = forms.CharField(label="Номер договора", max_length=200)
    contract_date = forms.DateField(label="Дата договора", widget=forms.DateInput(attrs={"type": "date"}))
    due_date = forms.DateField(label="Дата оплаты по вашим сведениям", widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.CharField(label="Неоплаченная сумма, ₽", max_length=200)
    description = forms.CharField(label="Что выполнено и на чём основано требование", max_length=4000, widget=forms.Textarea)
    facts_confirmed = forms.BooleanField(label="Я проверил введённые реквизиты и сведения")
    synthetic_data = forms.BooleanField(label="Ввожу только вымышленные сведения, без клиентских документов")
    use_ai = forms.BooleanField(label="Запросить отдельную ИИ-подсказку для синтетического описания", required=False)
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        raw = dict(data)
        for key in ("contract_date", "due_date"):
            raw[key] = raw[key].isoformat()
        try:
            self.normalized = normalize(raw)
        except InvalidClaim as exc:
            raise forms.ValidationError(str(exc)) from exc
        return data
