from django.contrib import admin
from .models import TgUser, VpnClient, Plan, Purchase

admin.site.register(TgUser)
admin.site.register(VpnClient)
admin.site.register(Plan)
admin.site.register(Purchase)
