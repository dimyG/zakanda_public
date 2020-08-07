from django.contrib import admin
import models


class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'transaction_id', 'user', 'amount', 'currency', 'test', 'submitted')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name', 'transaction_id')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at')


class StatusReportAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'amount', 'currency', 'mb_transaction_id', 'valid')
    list_filter = ('created_at', 'status', 'valid')
    search_fields = ('payment_request__user__email', 'payment_request__user__username',
                     'payment_request__user__first_name', 'payment_request__user__last_name', 'mb_transaction_id')
    readonly_fields = ('id', 'created_at', 'updated_at')


class TransferRequestAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'transaction_id', 'user', 'amount', 'currency', 'test', 'prepared')
    list_filter = ('created_at', 'user')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name', 'transaction_id')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at')


class TransferStatusReportAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'status_msg', 'mb_amount', 'mb_currency', 'mb_transaction_id', 'claimed')
    list_filter = ('created_at', 'status', 'claimed')
    search_fields = ('transfer_request__user__email', 'transfer_request__user__username',
                     'transfer_request__user__first_name', 'transfer_request__user__last_name', 'mb_transaction_id')
    readonly_fields = ('id', 'created_at', 'updated_at')


admin.site.register(models.PaymentRequest, PaymentRequestAdmin)
admin.site.register(models.StatusReport, StatusReportAdmin)
admin.site.register(models.TransferRequest, TransferRequestAdmin)
admin.site.register(models.TransferStatusReport, TransferStatusReportAdmin)
