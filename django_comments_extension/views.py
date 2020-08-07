# from __future__ import absolute_import
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required, permission_required
import django_comments
from django_comments.views.utils import next_redirect, confirmation_view
from django_comments.views import moderation
from django.http import HttpResponse, Http404
# from zakanda.utils import custom_pjaxtend


@csrf_protect
# @permission_required("django_comments.can_moderate")
def delete(request, comment_id, next=None):
    # I removed the can_moderate permission so that any user can delete his own comments
    """
    Deletes a comment. Confirmation on GET, action on POST. Requires the "can
    moderate comments" permission.

    Templates: :template:`comments/delete.html`,
    Context:
        comment
            the flagged `comments.comment` object
    """
    comment = get_object_or_404(django_comments.get_model(),
                                pk=comment_id,
                                site__pk=get_current_site(request).pk)

    user = request.user
    if not user.is_authenticated():
        return HttpResponse("You have no power here")

    # if user is not moderator or is not the author of the comment forbid any action
    if not user.has_perms("django_comments.can_moderate"):
        user_id = user.id
        author_id = comment.user.id
        if not author_id == user_id:
            return HttpResponse("You have no power here")

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as deleted instead of actually deleting it.
        moderation.perform_delete(request, comment)
        return next_redirect(request, fallback=next or 'comments-delete-done',
                             c=comment.pk)

    # Render a form on GET
    else:
        return render(request, 'comments/delete.html', {'comment': comment, "next": next})