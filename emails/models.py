from django.db import models
import games.models


# class TotalBetEmail(models.Model):
#     total_bet = models.OneToOneField(games.models.TotalBet)
#     has_been_sent = models.BooleanField(default=False)
#     has_been_seen = models.BooleanField(default=False)
#
#     def __unicode__(self):
#         return "email for tb.id {}".format(self.total_bet.id)