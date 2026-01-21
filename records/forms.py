from django import forms
from .models import Record

class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ["category", "amount", "date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
    
    def clean_memo(self):
        memo = self.cleaned_data.get("memo", "")

        if memo.strip() == "":
            raise forms.ValidationError("内容を入力してください")

        if len(memo) > 100:
            raise forms.ValidationError("メモは100文字以内で入力してください")

        return memo
    
    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        # 未入力 or 0未満をNG
        if amount is None:
            raise forms.ValidationError("金額を入力してください")

        if amount < 0:
            raise forms.ValidationError("金額は0以上で入力してください")

        return amount