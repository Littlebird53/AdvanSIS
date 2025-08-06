from django import template
from django.utils.html import format_html
from django.shortcuts import reverse
from django.template import Context, Template
from app import models

register = template.Library()

@register.filter
def as_form(obj, name='default'):
    return obj.build_form(name, instance=obj)

@register.filter
def as_form_table(obj, name='default'):
    return obj.build_form(name, instance=obj).as_table()

@register.filter
def as_row(obj, name='default'):
    return obj.as_row(name)

@register.filter
def form_field(obj, name='default'):
    form = obj.build_form(name, instance=obj)
    tmpl = Template('<form hx-trigger="change" hx-post="{% url obj.edit_url_name obj.id %}" data-form-id="skip">{{field}}<input type="hidden" name="form" value="{{name}}"/></form>')
    return tmpl.render(Context({
        'obj': obj,
        'name': name,
        'field': form[obj.forms[name]['fields'][0]],
    }))

@register.filter
def delete_button(obj):
    return Template(
        '''<form hx-delete="{% url instance.edit_url_name instance.id %}" class="delete-form"><button>Delete</button></form>''').render(
        Context({'instance': obj}))

@register.simple_tag
def create_form(model_name):
    cls = models.AutosaveFormMixin.create_views[model_name]
    return cls.build_form('new').as_table()

@register.simple_tag
def create_form_horizontal(model_name):
    cls = models.AutosaveFormMixin.create_views[model_name]
    form = cls.build_form('new')
    return Template('<table><tr>{% for field in form %}<th>{{field.label}}</th>{% endfor %}</tr><tr>{% for field in form %}<td>{{field}}</td>{% endfor %}</tr></table>').render(Context({'form': form}))

@register.simple_tag
def create_url(model_name):
    cls = models.AutosaveFormMixin.create_views[model_name]
    return reverse(cls.create_url_name)
