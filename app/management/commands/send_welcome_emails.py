from django.core.management.base import BaseCommand, CommandError
from app.models import StudentRecord, StaffRecord
from app.views import make_email, add_pdf
import datetime

class Command(BaseCommand):
    help = 'Sends welcome emails for approved applications'

    def send_email(self, sr, mode):
        msg = make_email('Gateway ADVANCE Acceptance Letter',
                         sr.person.user.email,
                         f'app/{mode}_welcome_email.html', {'sr': sr})
        add_pdf(msg, 'acceptance_letter.pdf', f'latex/{mode}_welcome.tex',
                {'sr': sr})
        msg.send(fail_silently=False)

    def handle(self, *args, **kwargs):
        for sr in StudentRecord.objects.filter(status='C', acceptance_date__isnull=True):
            try:
                self.send_email(sr, 'student')
                sr.acceptance_date = datetime.date.today()
                sr.save()
            except:
                pass
        for sr in StaffRecord.objects.filter(status='C', center_approved=True, advance_approved=True, acceptance_date__isnull=True):
            try:
                if sr.center is None:
                    self.send_email(sr, 'instructor_at_large')
                else:
                    self.send_email(sr, 'instructor')
                sr.acceptance_date = datetime.date.today()
                sr.save()
            except:
                pass
