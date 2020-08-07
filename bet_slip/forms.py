from django import forms


class BetAmountForm(forms.Form):
    bet_amount = forms.FloatField(label='', min_value=0.1, max_value=50000.0, widget=forms.NumberInput(
        attrs={'class': "form-control", 'placeholder': "Amount"})
    )
    # make the bookmaker_name a hidden field. It will be populated by the value of the bookmakers pull down when the
    # place bet button is pressed.
    bookmaker_name = forms.CharField(max_length=25, widget=forms.HiddenInput())

