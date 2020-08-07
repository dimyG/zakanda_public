from django import template
# from gutils.utils import get_user

register = template.Library()


@register.filter(name='addclass')
def addclass(field, given_class):
    existing_classes = field.field.widget.attrs.get('class', None)
    if existing_classes:
        if existing_classes.find(given_class) == -1:
            # if the given class doesn't exist in the existing classes
            classes = existing_classes + ' ' + given_class
        else:
            classes = existing_classes
    else:
        classes = given_class
    return field.as_widget(attrs={"class": classes})


@register.filter('fieldtype')
def fieldtype(field):
    return field.field.widget.__class__.__name__


@register.filter(is_safe=True)
def define_label_class(field, added_class):
    return field.label_tag(attrs={'class': added_class})


# @register.filter
# def get_user_by(gid):
#     obj = get_user(gid)
#     if not obj:
#         return gid
#     return obj
