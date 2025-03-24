from django import forms
from .models import ProblemCard
from .gpt_engine import ask_gpt_with_validation
import logging

logger = logging.getLogger(__name__)

class ProblemCardForm(forms.ModelForm):
    gpt_key_question = forms.CharField(
        required=False,
        label="💡 GPT предлагает формулировку ключевого вопроса",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'readonly': True,
            'rows': 2,
        })
    )

    class Meta:
        model = ProblemCard
        fields = ['who', 'what', 'where', 'when', 'why_now', 'r1_as_is', 'r2_to_be', 'gap', 'problem_type']
        labels = {
            'who': 'Кто формулирует проблему?',
            'what': 'Что происходит (суть ситуации)?',
            'where': 'Где разворачиваются события?',
            'when': 'Когда и при каких обстоятельствах появилась проблема?',
            'why_now': 'Почему проблема стала актуальной именно сейчас?',
            'r1_as_is': 'R1: Как есть (текущее состояние)',
            'r2_to_be': 'R2: Как должно быть (желаемое состояние)',
            'gap': 'Разрыв (gap) между R1 и R2',
            'problem_type': 'Тип проблемы',
        }
        widgets = {
            'who': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'style': 'overflow:hidden; resize:none;'}),
            'what': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'style': 'overflow:hidden; resize:none;'}),
            'where': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'style': 'overflow:hidden; resize:none;'}),
            'when': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'style': 'overflow:hidden; resize:none;'}),
            'why_now': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'overflow:hidden; resize:none;'}),
            'r1_as_is': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'overflow:hidden; resize:none;'}),
            'r2_to_be': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'overflow:hidden; resize:none;'}),
            'gap': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'style': 'overflow:hidden; resize:none;'}),
            'problem_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_comments = {}

    def clean(self):
        logger.debug("🧼 Старт валидации формы ProblemCardForm")
        cleaned_data = super().clean()

        required_fields = ['who', 'what', 'where', 'when', 'why_now']
        forbidden_phrases = ['не знаю', 'непонятно', 'все плохо', 'ничего', 'ничего не происходит', 'никак', 'нет данных']

        for field in required_fields:
            value = cleaned_data.get(field, '').strip()
            if not value:
                self.add_error(field, "Это поле обязательно для заполнения.")
            elif len(value) < 10:
                self.add_error(field, "Пожалуйста, дайте более развернутый ответ (не менее 10 символов).")
            elif value.lower() in forbidden_phrases:
                self.add_error(field, "Формулировка слишком общая или неопределённая — уточните.")

        if self.errors:
            return cleaned_data

        try:
            gpt_response = ask_gpt_with_validation(cleaned_data)
        except Exception:
            logger.exception("❌ Ошибка при вызове GPT")
            self.add_error(None, "Ошибка при обращении к GPT. Попробуйте позже.")
            return cleaned_data

        cleaned_data['analysis'] = gpt_response.get("analysis", "")
        cleaned_data['gpt_key_question'] = gpt_response.get("key_question", "")
        self.field_comments = gpt_response.get("field_comments", {}) or {}

        for field, comment in self.field_comments.items():
            if comment.strip() and field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': self.fields[field].widget.attrs.get('class', '') + ' is-gpt-flagged',
                    'data-gpt-comment': comment
                })
                self.add_error(field, comment)

        if any(word in cleaned_data['analysis'].lower() for word in ["неясно", "размыто", "недостаточно", "неструктурировано"]):
            self.add_error(None, f"GPT считает, что описание проблемы недостаточно чёткое:\n\n{cleaned_data['analysis']}")

        return cleaned_data
