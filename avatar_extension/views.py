
import logging
from django.contrib.auth.decorators import login_required
import avatar.views
import avatar.forms
from zakanda import utils

logger = logging.getLogger(__name__)


@login_required
def delete(request, extra_context=None, next_override=None, *args, **kwargs):
    if isinstance(extra_context, dict):
        extra_context.update(utils.get_pjax_context(request))
    else:
        extra_context = utils.get_pjax_context(request)
    response = avatar.views.delete(request, extra_context=extra_context, next_override=next_override, *args, **kwargs)
    return response


@login_required
def change(request, extra_context=None, next_override=None, upload_form=avatar.forms.UploadAvatarForm,
           primary_form=avatar.forms.PrimaryAvatarForm, *args, **kwargs):
    if isinstance(extra_context, dict):
        extra_context.update(utils.get_pjax_context(request))
    else:
        extra_context = utils.get_pjax_context(request)
    response = avatar.views.change(request, extra_context=extra_context, next_override=next_override,
                                   upload_form=upload_form, primary_form=primary_form, *args, **kwargs)
    return response


@login_required
def add(request, extra_context=None, next_override=None, upload_form=avatar.forms.UploadAvatarForm, *args, **kwargs):
    if isinstance(extra_context, dict):
        extra_context.update(utils.get_pjax_context(request))
    else:
        extra_context = utils.get_pjax_context(request)
    response = avatar.views.add(request, extra_context=extra_context, next_override=next_override,
                                upload_form=upload_form, *args, **kwargs)
    return response