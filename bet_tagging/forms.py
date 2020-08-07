import logging
from django.forms import ModelForm, Textarea, FloatField, TextInput, Select, NumberInput, ValidationError, ChoiceField, CheckboxInput
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
import models

logger = logging.getLogger(__name__)


class BetTagForm(ModelForm):

    # def __init__(self, *args, **kwargs):
    #     super(BetTagForm, self).__init__(*args, **kwargs)
    #     self.fields['type'] = ChoiceField(choices=[
    #         (models.BetTag.free, models.BetTag.free),
    #         (models.BetTag.private, models.BetTag.private)
    #     ])

    class Meta:
        model = models.BetTag
        fields = ["name", "description", "type"]
        labels = {
            'description': _('Description'),
            'name': _('Name'),
            'type': _('Type'),
        }
        help_texts = {
            'description': _('Write a description for your Bet Group (up to 400 characters)'),
        }
        widgets = {
            'description': Textarea(attrs={'cols': 50, 'rows': 5, 'class': 'form-control', 'placeholder': help_texts.get('description')}),
            'name': TextInput(attrs={'class': 'form-control'}),
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                # unique_together check doesn't work since owner field is not included in the form
                'unique_together': "You already have a Bet Group '%(model_name)s's'. Please define a different name",
            }
        }

    def clean_type(self):
        bet_group_type = self.cleaned_data['type']
        if bet_group_type == models.BetTag.premium:
            if not self.instance.owner.profile.is_seller():
                raise ValidationError(_("You have to become a seller in order to create a Premium Bet Group!"))
        # Always return a value to use as the new cleaned data, even if
        # this method didn't change it.
        return bet_group_type

    def clean(self):
        cleaned_data = super(BetTagForm, self).clean()
        name = cleaned_data.get('name')
        owner = self.owner  # we need to pass the owner attribute to the form when it is instantiated
        # print(dir(self))
        if name and owner:
            try:
                if hasattr(self, 'obj_pk') and self.obj_pk:
                    # if the form is used to edit an object we add the object's pk as a form attribute. In this case
                    # we must exclude the object (BetTag) from the unique_together validation check since the user
                    # might just want to update the description. In this case obj already exist and the validation
                    # check would fail.
                    models.BetTag.objects.exclude(pk=self.obj_pk).get(name=name, owner=owner)
                else:
                    models.BetTag.objects.get(name=name, owner=owner)
                raise ValidationError('{} you already have a Bet Group with name {}. You can define a different '
                                      'name or you can go back, change the name of the existing Bet Group and retry'.format(owner, name))
            except models.BetTag.MultipleObjectsReturned:
                logger.error("User %s has many BetTags with name %s", owner, name)
                raise ValidationError('{} you already have a Bet Group with name {}. You can define a different '
                                      'name or you can go back, change the name of the existing Bet Group and retry'.format(owner, name))
            except models.BetTag.DoesNotExist:
                pass
        return cleaned_data

    # def __init__(self, user, *args, **kwargs):
    #     super(BetTagForm, self).__init__(*args, **kwargs)


class DepositWithdrawalForm(ModelForm):
    def __init__(self, *args, **kwargs):
        """
        we will add the user as a required kwarg (in the get_form_kwargs) when the form is initialized.
        This means that we have to set the self.user in form's __init__ method.
        We want the user, in order to extract his bet_tags during form initialization.
        Even on get requests, an unbound form is instantiated and send.
        So, since bet_tags are defined during initialization (in __init__) they are available.
        """
        # pop instead of get, since super (the original init method) doesn't expect a user kwarg
        self.user = kwargs.pop('user', None)
        super(DepositWithdrawalForm, self).__init__(*args, **kwargs)
        bet_tags = models.BetTag.objects.filter(owner=self.user)
        self.fields['bet_tag'].queryset = bet_tags
        self.fields['bet_tag'].empty_label = None


class DepositForm(DepositWithdrawalForm):
    # if the amount is defined here then the Meta definitions for this field have no effect ! No need to do so.
    # I can define the min value as an attribute
    # amount = FloatField(min_value=1)  # declarative definition in order to define min_value
    class Meta:
        model = models.Deposit
        fields = ["bet_tag", "amount"]
        labels = {"amount": _("Amount"), "bet_tag": _("Bet Group")}
        widgets = {
            'bet_tag': Select(attrs={'class': 'form-control'}),
            'amount': NumberInput(attrs={'class': 'form-control', 'min': models.Deposit.min_amount,
                                         'max': models.Deposit.max_amount}),
        }


class WithdrawalForm(DepositWithdrawalForm):
    class Meta:
        model = models.Withdrawal
        fields = ["bet_tag", "amount"]
        labels = {"amount": _("Amount"), "bet_tag": _("Bet Group")}
        widgets = {
            'bet_tag': Select(attrs={'class': 'form-control'}),
            'amount': NumberInput(attrs={'class': 'form-control', 'min': models.Withdrawal.min_amount}),
        }

    def clean(self):
        cleaned_data = super(WithdrawalForm, self).clean()
        amount = cleaned_data.get("amount")
        bet_group = cleaned_data.get("bet_tag")
        # logger.debug('bet group id: %s, amount: %s', bet_group, amount)
        if amount and bet_group:
            # if all have survived the field cleaning
            try:
                balance = bet_group.balance
                # logger.debug('balance: %s', balance)
                if amount > balance:
                    error = ValidationError(_("You don't have enough balance"), code='invalid_withdrawal_amount')
                    # it adds the error to the amount field and removes it from cleaned_data
                    self.add_error('amount', error)
            except Exception as e:
                logger.error('%s', e)
                # raise ValidationError(_("Invalid withdrawal data"), code='invalid_withdrawal_data')


class NotificationSubscriptionForm(ModelForm):
    class Meta:
        model = models.NotificationSubscription
        fields = ["email", "in_app"]
        help_texts = {
            "email": _("Send me emails for new bets"),
            "in_app": _("Send me website notifications for new bets")
        }


class ServiceForm(ModelForm):
    def __init__(self, *args, **kwargs):
        # makes duration field readonly (select element doesn't support 'readonly" attribute. Use 'disabled' instead)
        # notice that disabled inputs are not submitted with the form
        super(ServiceForm, self).__init__(*args, **kwargs)
        self.fields['duration'].widget.attrs['disabled'] = True

    def clean_duration(self):
        """ ensures that the readonly field won't be overridden by a POST (additional protection) """
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            return instance.duration
        else:
            return self.cleaned_data['duration']

    class Meta:
        model = models.Service
        fields = ["duration", "price"]
        labels = {
            'price': _("Price (euros)"),
            'duration': _("Duration in days"),
            # 'subscribers_limit': _("Maximum number of subscribers")
        }
        help_texts = {
            "price": _("The price which your subscribers need to pay, to access "
                       "your Bet Group tips for the selected duration."),
            "duration": _("The duration of this subscription service in days."),
            # "subscribers_limit": _("The maximum allowed number of subscribers for this subscription service."),
        }
