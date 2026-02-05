from django import forms
from .models import Topic, Comment

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["board_category", "title", "text", "status"]
        widgets = {
            "text": forms.Textarea(attrs={"maxlength": "1000"}),  # UI補助
        }
        error_messages = {
            "text": {
                "max_length": "本文は1000文字以内で入力してください",
            }
        }

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        if len(text) > 1000:
            raise forms.ValidationError("本文は1000文字以内で入力してください")
        return text


class CommentForm(forms.ModelForm):
    # 返信番号（DBには保存しない入力欄）
    reply_to = forms.IntegerField(
        required=False,
        min_value=1,
        label="返信したいコメントの番号（任意）",
    )

    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"maxlength": "1000"}),
        }

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        if len(text) > 1000:
            raise forms.ValidationError("コメントは1000文字以内で入力してください")
        return text