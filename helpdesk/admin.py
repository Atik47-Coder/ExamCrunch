from django.contrib import admin
from .models import HelpRequest,HelpInvitation,Response,Feedback

admin.site.register(HelpRequest)
admin.site.register(HelpInvitation)
admin.site.register(Response)
admin.site.register(Feedback)
