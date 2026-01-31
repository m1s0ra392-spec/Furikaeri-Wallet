from django import forms
from .models import Topic, Comment


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["title", "text"]


        
class CommentForm(forms.ModelForm):
    # DBには保存しない「入力専用」フィールド
    reply_to = forms.IntegerField(
        required=False,
        min_value=1,
        label="返信先コメント番号（任意）",
        widget=forms.NumberInput(attrs={"class": "reply-input", "placeholder": "例: 3"}),
    )
    

    class Meta:
        model = Comment
        fields = ["text"]  
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "textarea",
                "maxlength": "1000",
                "placeholder": "1000文字以内でコメントを書いてください",
            }),
        }
        labels = {"text": "コメント"}