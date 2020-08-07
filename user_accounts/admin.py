from django.contrib import admin
import models


@admin.register(models.UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ('^user__username',)
    readonly_fields = ('id',)


@admin.register(models.LegalSellerInfo)
class LegalSellerInfoAdmin(admin.ModelAdmin):
    search_fields = ('^profile__user__username', '=tax_number', '=payments_email')
    readonly_fields = ('id',)


@admin.register(models.PersonSellerInfo)
class PersonSellerInfoAdmin(admin.ModelAdmin):
    search_fields = ('^profile__user__username', '=tax_number', '=payments_email')
    readonly_fields = ('id',)


@admin.register(models.BasicStats)
class BasicStatsAdmin(admin.ModelAdmin):
    search_fields = ('^user__username',)
    readonly_fields = ('id',)
