from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    existing_classes = field.field.widget.attrs.get('class', '')
    combined_classes = f"{existing_classes} {css_class}".strip()
    return field.as_widget(attrs={**field.field.widget.attrs, 'class': combined_classes})

@register.filter(name='get_item')
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter(name='hide_field')
def hide_field(field_name):
    return field_name in ["gpt_key_question"]  # Можно расширить список

@register.filter
def not_in(value, args):
    return value not in args.split(',')