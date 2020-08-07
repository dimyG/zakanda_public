from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def domain_mistyping(email):
    """ Checks common mistyping of the most common email providers """
    try:
        full_domain = email.split('@')[1]
        domain = full_domain.split('.')[0]
    except Exception as e:
        raise ValidationError("Enter a valid email address")

    valid_domains = ['gmail', 'hotmail', 'yahoo']
    gmail_mistypes = ['gmai', 'ymai', 'vmai', 'fmai', 'hmai', 'bmai', 'tmai', 'gamail', 'gnai']
    yahoo_mistypes = ['yaho', 'uaho', 'taho', 'yahho']
    hotmail_mistypes = ['hotmai', 'hotnai']
    mistypes = gmail_mistypes + yahoo_mistypes + hotmail_mistypes

    for mistype in mistypes:
        if domain.find(mistype) != -1:
            if domain not in valid_domains:
                raise ValidationError(
                    _("'%(domain)s' is probably not a valid email domain"),
                    params={'domain': domain},
                )


class SignupFormCustom(SignupForm):
    email = forms.EmailField(widget=forms.TextInput(attrs={'type': 'email', 'placeholder': _('E-mail address')}),
                             validators=[domain_mistyping])
