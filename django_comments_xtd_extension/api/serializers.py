import logging
import pytz
from rest_framework import serializers
from django.utils.timezone import get_default_timezone
from django.contrib.auth.models import User
from django_comments_xtd.api.serializers import ReadCommentSerializer, WriteCommentSerializer
from avatar.templatetags import avatar_tags
from avatar.utils import get_default_avatar_url
from django_comments_xtd.models import XtdComment
from django.core.urlresolvers import reverse


logger = logging.getLogger(__name__)


class WriteCommentSerializerCustom(WriteCommentSerializer):
    # todo high define the user url attribute so that the username in comments becomes a link
    # each comment object has a user_url attribute which is empty by default and can be defined
    # in the comment's form. I have hidden this form field and I want to externally make it
    # be the user's profile page. So I have to manually modify the form field.

    def get_user_url(self):
        try:
            user_id = self.request.user.id
        except Exception as e:
            # user url will be empty for anonymous users
            return
        return reverse('bet_statistics:profile_stats_template', args=[user_id])

    def save(self):
        # self.form.get_comment_object(site_id=site.id)
        super(WriteCommentSerializerCustom, self).save()


class ReadCommentSerializerCustom(ReadCommentSerializer):
    user_id = serializers.IntegerField(default=0, read_only=True)  # it doesn't exist in the parent class

    class Meta:
        model = XtdComment
        fields = ('id', 'user_name', 'user_url', 'user_moderator',
                  'user_avatar', 'permalink', 'comment', 'submit_date',
                  'parent_id', 'level', 'is_removed', 'allow_reply', 'flags', 'user_id')

    def get_user_avatar(self, obj):
        user = obj.user
        if isinstance(user, User):
            return avatar_tags.avatar_url(user=obj.user, size=80)
        return get_default_avatar_url()

    # def get_user_id(self, obj):
    #     user = obj.user
    #     if isinstance(user, User):
    #         if user.is_authenticated():
    #             return user.id
    #     return 0

    def get_submit_date(self, obj):
        # the date is read as utc despite the fact that it has tzinfo in the db. So we localize it to
        # user's timezone taking the timezone from the session. It has been set by the django_easy_timezones
        # app using the IP and a GEOIP database
        # todo is this necessary for production too?
        zone = self.request.session.get('django_timezone')
        if not zone:
            zone = get_default_timezone()
        obj.submit_date = obj.submit_date.astimezone(pytz.timezone(zone))
        return super(ReadCommentSerializerCustom, self).get_submit_date(obj)



