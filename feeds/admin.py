from django.contrib import admin
import feeds.models

admin.site.register(feeds.models.RawBetEvent)
admin.site.register(feeds.models.BetEventActivity)
admin.site.register(feeds.models.FollowActivity)
admin.site.register(feeds.models.BetGroupFollowActivity)
admin.site.register(feeds.models.CommentActivity)
# admin.site.register(feeds.models.TotalBetActivity)