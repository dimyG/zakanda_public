import logging
from zakanda.utils import cbv_pjaxtend
from allauth.account.views import LoginView, SignupView
from forms import SignupFormCustom

logger = logging.getLogger(__name__)


class LoginViewCustom(LoginView):
    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        logger.debug("get to LoginViewCustom")
        resp = super(LoginViewCustom, self).get(request, *args, **kwargs)
        return resp

    @cbv_pjaxtend()
    def post(self, request, *args, **kwargs):
        logger.debug("post to LoginViewCustom")
        resp = super(LoginViewCustom, self).post(request, *args, **kwargs)
        return resp

    # def get_context_data(self, **kwargs):
    #     res = super(LoginViewCustom, self).get_context_data(self, **kwargs)


class SignUpViewCustom(SignupView):
    form_class = SignupFormCustom


login_custom = LoginViewCustom.as_view()
signup_custom = SignUpViewCustom.as_view()

# to go back to full page load
# login html remove extends parent
# navbar login form remove data-pjax
# zakanda.urls remove login url
