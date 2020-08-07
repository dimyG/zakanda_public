from django.contrib import admin
import models


@admin.register(models.BetTag)
class DepositAdmin(admin.ModelAdmin):
    search_fields = ('=balance', '^owner__username', '^name')
    readonly_fields = ('id', 'balance', 'created_at', 'updated_at')


@admin.register(models.Deposit)
class DepositAdmin(admin.ModelAdmin):
    search_fields = ('=amount', '^bet_tag__owner__username', '^bet_tag__name')
    readonly_fields = ('id', 'amount')


@admin.register(models.Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    search_fields = ('=amount', '^bet_tag__owner__username', '^bet_tag__name')
    readonly_fields = ('id', 'amount')


@admin.register(models.NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('^bet_group__name', '=bet_group__id', '^user__username', '^user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    search_fields = ('^bet_group__name', '=bet_group__id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('^service__bet_group__name', '=service__bet_group__id', '^user__username', '^user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.PaymentReport)
class PaymentReportAdmin(admin.ModelAdmin):
    search_fields = ('^subscription__service__bet_group__name', '=subscription__service__bet_group__id',
                     '^subscription__user__username', '^subscription__user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.GenericTransferReport)
class TransferReportAdmin(admin.ModelAdmin):
    search_fields = ('^subscriptions__service__bet_group__name', '=subscriptions__service__bet_group__id',
                     '^subscriptions__user__username', '^subscriptions__user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
