from django.core.management.base import BaseCommand, CommandError
from app.models import PopupMessage
from app.views import make_email
import datetime

class Command(BaseCommand):
    help = 'Send out popup messages by email'

    def handle(self, *args, **kwargs):
        qr = PopupMessage.objects.filter(
            dismissed=False, emailed=False).order_by('sent')[:25]
        for pm in qr:
            ea = pm.person.emails.all().filter(active=True).first()
            if ea:
                e = ea.email
            else:
                e = pm.person.user.email
                if not e:
                    continue
            msg = make_email('Gateway ADVANCE New Message', e,
                             'app/popup_email.html', {'pm': pm})
            msg.send(fail_silently=False)
            pm.emailed = True
            pm.save()
