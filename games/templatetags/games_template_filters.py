__author__ = 'xene'

from django.template.defaulttags import register


# In the template: {{ mydict|get_item:item.NAME }}
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

