from django.core.management.base import BaseCommand, CommandError
from app.models import MOU, StaffRecord
from app.views import make_email, add_pdf
import datetime

class Command(BaseCommand):
    help = 'Sends out MOUs once all signatures are collected'

    def handle(self, *args, **kwargs):
        qr = MOU.objects.filter(director_sig__isnull=False,
                                sponsor_sig__isnull=False,
                                advance_sig__isnull=False,
                                gs_dean_sig__isnull=False,
                                start_date__isnull=True)
        for mou in qr:
            MOU.objects.filter(center=mou.center,
                               status__in=['A', 'E']).update(status='R')
            mou.start_date = max(
                mou.director_sig,
                mou.sponsor_sig,
                mou.advance_sig,
                mou.gs_dean_sig)
            y = mou.start_date.year
            m = mou.start_date.month
            d = mou.start_date.day
            if m == 2 and d == 29:
                m = 3
                d = 1
            mou.expiration = datetime.date(y+5, m, d)
            mou.status = 'A'
            mou.save()
            director = StaffRecord.objects.filter(
                center=mou.center, status='C', role='D').first()
            if director is None:
                continue
            if MOU.objects.filter(center=mou.center).count() == 1:
                msg = make_email('Gateway ADVANCE Acceptance Letter',
                                 director.person.email,
                                 'app/center_welcome_email.html',
                                 {'sr': director})
                add_pdf(msg, 'mou.pdf', mou.template_name,
                        {'center': mou.center, 'mou': mou,
                         'director': director.person})
                msg.send(fail_silently=False)
            else:
                # TODO: MOU renewal notice
                pass
