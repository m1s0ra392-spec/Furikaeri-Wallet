from django import forms
from django.utils import timezone
from .models import Record

class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ["category", "amount", "date", "memo"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "memo": forms.Textarea(attrs={
                "placeholder": "※メモは200文字以内で入力してください",
                "rows": 3,
            }),
        }
        error_messages = {
            "memo": {
                "required": "内容を入力してください",
                "max_length": "メモは200文字以内で入力してください",
            },
            "date": {
                "required": "日付を入力してください",
            },
        }
        
    #日付のバリデーション
    def clean_date(self):
        date = self.cleaned_data.get("date")

        if not date:
            raise forms.ValidationError("日付を入力してください")

        today = timezone.localdate()

        if date > today:
            raise forms.ValidationError("未来の日付は入力できません")

        return date
    
    
    #メモのバリデーション
    def clean_memo(self):
        memo = self.cleaned_data.get("memo", "")

        if memo.strip() == "":
            raise forms.ValidationError("内容を入力してください")

        return memo
    
    #金額のバリデーション
    def clean_amount(self):  
        amount = self.cleaned_data.get("amount")

        # 未入力 or 0未満をNG
        if amount is None:
            raise forms.ValidationError("金額を入力してください")

        if amount < 0:
            raise forms.ValidationError("金額は0以上で入力してください")

        return amount