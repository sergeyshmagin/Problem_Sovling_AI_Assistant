from django.views.generic import FormView
from .forms import ProblemCardForm

class ProblemCardCreateView(FormView):
    template_name = 'assistant/problem_card_form.html'
    form_class = ProblemCardForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['excluded_context_fields'] = ['gpt_key_question', 'r1_as_is', 'r2_to_be', 'gap', 'problem_type']
        context['target_fields'] = ['r1_as_is', 'r2_to_be', 'gap']
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        context.update({
            'gpt_key_question': form.cleaned_data.get('gpt_key_question'),
            'analysis': form.cleaned_data.get('analysis'),
            'field_comments': form.cleaned_data.get('field_comments', {})
        })
        return self.render_to_response(context)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))