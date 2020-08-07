from django import forms
import user_accounts.models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = user_accounts.models.UserProfile
        fields = ["public", "description"]
        labels = {
            'public': _('Allow others to see my Cash values'),
            'description': _('Description')
        }
        help_texts = {
            'description': _('A few words about you...'),
        }
        widgets = {
            # 'public': forms.CheckboxInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 7, 'class': 'form-control',
                                                 'placeholder': help_texts.get('description')})
        }


class LegalSellerForm(forms.ModelForm):

    class Meta:
        model = user_accounts.models.LegalSellerInfo
        fields = ["legal_name", "country", "address", 'tax_number', 'payment_method', "payments_email"]
        labels = {
            "country": _('Incorporation Country'),
            'address': _('Address'),
            'payment_method': _('Payment Method'),
            'payments_email': _('Skrill email'),
            'legal_name': _('Legal Name'),
            'tax_number': _('Tax Identification Number')
        }
        help_texts = {
            # the empty strings override the model fields help text so that they are not shown in the template
            'country': '',
            'address': '',
            'payment_method': _('The payment method you will be paid with.'),
            'payments_email': _('Your email on the payment method (skrill) to which the funds will be paid.'),
            'legal_name': '',
            'tax_number': '',
        }

    # todo validate the payment method is one of the choices
    # https://stackoverflow.com/questions/324477/in-a-django-form-how-do-i-make-a-field-readonly-or-disabled-so-that-it-cannot
    def __init__(self, *args, **kwargs):
        """ makes payment_method field readonly """
        super(LegalSellerForm, self).__init__(*args, **kwargs)
        # instance = getattr(self, 'instance', None)
        # if instance and instance.pk:
        self.fields['payment_method'].widget.attrs['readonly'] = True

    def clean_payment_method(self):
        """ ensures that the readonly field won't be overridden by a POST (additional protection) """
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.payment_method
        else:
            return self.cleaned_data['payment_method']


class PersonSellerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # makes payment_method field readonly
        super(PersonSellerForm, self).__init__(*args, **kwargs)
        self.fields['payment_method'].widget.attrs['readonly'] = True

    def clean_payment_method(self):
        """ ensures that the readonly field won't be overridden by a POST (additional protection) """
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.payment_method
        else:
            return self.cleaned_data['payment_method']

    class Meta:
        model = user_accounts.models.PersonSellerInfo
        fields = ['first_name', 'last_name', "country", 'address', 'tax_number', "phone_number", 'payment_method', "payments_email"]
        labels = {
            'first_name': _("First Name"),
            'last_name': _("Last Name"),
            'country': _('Country of Residence'),
            'address': _('Address'),
            'payments_email': _('Skrill email'),
        }
        help_texts = {
            # the empty strings override the model fields help text so that they are not shown in the template
            'country': '',
            'address': '',
            'payment_method': _('The payment method you will be paid with.'),
            'payments_email': _('Your email on the payment method (skrill) to which the funds will be paid.'),
            'tax_number': '',
        }

    # def __init__(self, *args, **kwargs):
    #     # magic
    #     self.user = kwargs['instance'].profile.user
    #     user_kwargs = kwargs.copy()
    #     user_kwargs['instance'] = self.user
    #     self.user_form = SimpleUserForm(*args, **user_kwargs)
    #     # magic end
    #
    #     super(PersonSellerForm, self).__init__(*args, **kwargs)
    #
    #     self.fields.update(self.user_form.fields)
    #     self.initial.update(self.user_form.initial)

    # def save(self, *args, **kwargs):
    #     # save both forms
    #     self.user_form.save(*args, **kwargs)
    #     return super(PersonSellerForm, self).save(*args, **kwargs)

    # class SimpleUserForm(forms.ModelForm):
    #     class Meta:
    #         model = User
    #         fields = ('first_name', 'last_name')
