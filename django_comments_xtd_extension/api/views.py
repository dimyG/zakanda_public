from django_comments_xtd import api
import serializers as custom_serializers


class CommentListCustom(api.views.CommentList):
    serializer_class = custom_serializers.ReadCommentSerializerCustom
