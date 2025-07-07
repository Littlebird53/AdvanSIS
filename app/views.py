from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic.edit import FormView, UpdateView
from app import models
from app import forms
import collections
import datetime
from email.mime.image import MIMEImage
import json
import itertools

def make_email(subject, to, template_name, context):
    message = EmailMultiAlternatives(subject=subject, to=[to])
    message.mixed_subtype = 'related'
    tmpl = get_template(template_name)
    message.attach_alternatives(tmpl.render(context), 'text/html')
    for name in ['logo', 'facebook', 'twitter', 'instagram', 'youtube']:
        with open(finders.find(f'email/{name}.png'), 'rb') as fin:
            data = fin.read()
            blob = MIMEImage(data)
            blob.add_header('Content-ID', f'<{name}>')
            message.attach(blob)
    return message

def add_pdf(message, filename, template_name, context):
    from django_tex.core import compile_template_to_pdf
    pdf = compile_template_to_pdf(template_name, context)
    message.attach(filename, pdf)

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('app:dashboard')
    return render(request, 'app/index.html')

def permission_denied_page(request, exception):
    return render(request, 'errors/403.html')

class CreateAccountView(FormView):
    template_name = 'app/create_account.html'
    success_url = '/'
    form_class = forms.NewUserForm

    def form_valid(self, form):
        import uuid
        user = models.User.objects.create_user(
            str(uuid.uuid1()),
            form.cleaned_data['email'],
            form.cleaned_data['password'])
        person = form.save(commit=False)
        person.user = user
        email = models.EmailAddress()
        email.email = form.cleaned_data['email']
        email.category = 'P'
        email.save()
        person.save()
        user.username = str(person.id)
        user.save()
        person.emails.add(email)
        from django.contrib.auth import login
        login(self.request, user)
        return super().form_valid(form)

def get_current_term():
    seq = ['Sp', 'Su', 'Fa', 'Wi']
    term_map = [0, # skip
                0, 0, 0, 0, 0, # Jan-May
                1, 1, # Jun-Jul
                2, 2, 2, 2, # Aug-Nov
                3, # Dec
                ]
    month = datetime.date.today().month
    return seq[term_map[month]]

def sort_courses(courses):
    seq = ['Sp', 'Su', 'Fa', 'Wi']
    term_map = [0, # skip
                0, 0, 0, 0, 0, # Jan-May
                1, 1, # Jun-Jul
                2, 2, 2, 2, # Aug-Nov
                3, # Dec
                ]
    year = datetime.date.today().year
    month = datetime.date.today().month
    term = term_map[month]
    dct = {'present': [], 'past': [], 'future': []}
    for course in courses:
        key = course.sort_key()
        print(course, key, year, term)
        if key[0] < year:
            dct['past'].append(course)
        elif key[0] > year:
            dct['future'].append(course)
        elif key[1] < term:
            dct['past'].append(course)
        elif key[1] > term:
            dct['future'].append(course)
        else:
            dct['present'].append(course)
    for k in dct:
        dct[k].sort(key=lambda c: c.sort_key())
    return dct

def get_staff_stats():
    ret = {}
    ret['staff_applications'] = models.StaffRecord.objects.filter(
        status='C', center_approved=True, advance_approved=False).count()
    return ret

@login_required
def dashboard(request):
    message = None
    if request.method == 'POST':
        form = forms.ContactUpdateForm(request.POST,
                                       instance=request.user.person)
        if form.is_valid():
            message = 'Personal information updated successfully'
            form.save()
        else:
            message = 'There were errors. Please correct them below.'
    else:
        form = forms.ContactUpdateForm(instance=request.user.person)
    current = []
    other = []
    for record in request.user.person.studentrecord_set.all():
        courses = sort_courses(
            [g.course for g in models.Grade.objects.filter(
                person=request.user.person,
                course__center=record.center)])
        if record.status == 'C':
            current.append((record, courses, True))
        else:
            other.append((record, courses, True))
    for record in request.user.person.staffrecord_set.all():
        courses = sort_courses(models.Course.objects.filter(
            (Q(instructor=request.user.person) |
             Q(associate_instructors=request.user.person)),
            center=record.center))
        if record.status == 'C':
            current.append((record, courses, False))
        else:
            other.append((record, courses, False))
    current.sort(key=lambda x: x[0].sort_key())
    other.sort(key=lambda x: x[0].sort_key())
    info_open = bool(form.errors)
    if not message and not info_open:
        if not request.user.person.has_profile:
            info_open = True
            message = 'Please complete your profile'
        elif not request.user.person.has_address:
            info_open = True
            message = 'Please add your address'
    stats = None
    if request.user.is_staff:
        stats = get_staff_stats()
    return render(request, 'app/dashboard.html',
                  {
                      'form': form,
                      'message': message,
                      'records': current + other,
                      'info_open': info_open,
                      'stats': stats,
                  })

def can_edit_info(user, person):
    if user.person == person or user.is_staff:
        return True
    s_centers = person.studentrecord_set.values_list('center', flat=True)
    i_centers = person.staffrecord_set.values_list('center', flat=True)
    return models.StaffRecord.objects.filter(
        person=user.person, role__in=['D', 'R'], status='C',
        center__in=s_centers.union(i_centers)).exists()
def get_person(request, personid):
    person = get_object_or_404(models.Person, pk=personid)
    if not can_edit_info(request.user, person):
        raise PermissionDenied()
    return person

@login_required
def edit_email_address(request, personid):
    print('edit_email_address', personid)
    person = get_person(request, personid)
    print(person)
    addr = person.emails.all()
    if request.method == 'GET':
        add = forms.NewEmailForm(person)
    else:
        dl = request.POST.get('delete')
        add = forms.NewEmailForm(person, request.POST)
        if dl and dl.isdigit():
            obj = get_object_or_404(models.EmailAddress, pk=int(dl))
            if obj in addr:
                obj.active = False
                obj.save()
            keys = list(add.errors.keys())
            for k in keys:
                del add.errors[k]
        elif add.is_valid():
            obj = add.save()
            person.emails.add(obj)
            add = forms.NewEmailForm(person)
    return render(request, 'app/edit_email_address.html',
                  {'form': add, 'existing': addr.filter(active=True),
                   'person': person})

@login_required
def edit_phone_address(request, personid):
    person = get_person(request, personid)
    addr = person.phones.all()
    if request.method == 'GET':
        add = forms.NewPhoneForm(person)
    else:
        dl = request.POST.get('delete')
        add = forms.NewPhoneForm(person, request.POST)
        if dl and dl.isdigit():
            obj = get_object_or_404(models.PhoneAddress, pk=int(dl))
            if obj in addr:
                obj.active = False
                obj.save()
            keys = list(add.errors.keys())
            for k in keys:
                del add.errors[k]
        elif add.is_valid():
            obj = add.save()
            person.phones.add(obj)
            add = forms.NewPhoneForm(person)
    return render(request, 'app/edit_phone_address.html',
                  {'form': add, 'existing': addr.filter(active=True),
                   'person': person})

@login_required
def edit_mailing_address(request, personid):
    person = get_person(request, personid)
    addr = person.mailings.all()
    if request.method == 'GET':
        add = forms.NewMailingForm(person)
    else:
        dl = request.POST.get('delete')
        add = forms.NewMailingForm(person, request.POST)
        if dl and dl.isdigit():
            obj = get_object_or_404(models.MailingAddress, pk=int(dl))
            if obj in addr:
                obj.active = False
                obj.save()
            keys = list(add.errors.keys())
            for k in keys:
                del add.errors[k]
        elif add.is_valid():
            obj = add.save()
            person.mailings.add(obj)
            add = forms.NewMailingForm(person)
    return render(request, 'app/edit_mailing_address.html',
                  {'form': add, 'existing': addr.filter(active=True),
                   'person': person})

@login_required
def course_details(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    grade = models.Grade.objects.filter(
        course=course, person=request.user.person).first()
    files = []
    if grade is not None:
        files = models.CourseFile.objects.filter(
            course=course).order_by('order')
    return render(request, 'app/course_details.html',
                  {'course': course, 'grade': grade, 'files': files})

@login_required
def manage_course(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    if not course.can_edit(request.user.person):
        return redirect('app:course', courseid)

    mode = None
    if request.method == 'POST':
        mode = request.POST.get('mode')

    message = ''
    qr = models.Grade.objects.filter(course=course).order_by(
        'person__family_name', 'person__given_name')
    if mode == 'grades':
        students = forms.GradeFormset(request.POST, queryset=qr)
        if students.is_valid():
            students.save()
            if students.changed_objects:
                message = 'grades updated'
        else:
            print(students.errors, students.non_form_errors)
    else:
        students = forms.GradeFormset(queryset=qr)

    file_query = models.SharedFile.objects.filter(
        course=course.template).filter(
            Q(owner__isnull=True) | Q(owner=request.user.person))
    file_kwargs = {
        'prefix': 'files',
        'queryset': models.CourseFile.objects.filter(
            course=course).order_by('order'),
        'form_kwargs': {'files': file_query, 'course': course},
    }
    if mode == 'files':
        files = forms.CourseFileFormset(request.POST, **file_kwargs)
        if files.is_valid():
            files.save()
            # deleting doesn't work if we don't refresh the queryset
            return redirect('app:manage_course', course.id)
    else:
        files = forms.CourseFileFormset(**file_kwargs)

    if mode == 'add':
        add = forms.AddFileForm(request.POST, request.FILES)
        if add.is_valid():
            obj = add.save(commit=False)
            obj.course = course.template
            obj.owner = request.user.person
            obj.save()
    else:
        add = forms.AddFileForm()

    return render(request, 'app/manage_course.html',
                  {
                      'course': course,
                      'grades': students,
                      'message': message,
                      'files': files,
                      'all_files': file_query,
                      'add_file': add,
                  })
@login_required
def add_student(request, courseid, studentid):
    course = get_object_or_404(models.Course, pk=courseid)
    student = get_object_or_404(models.Person, pk=studentid)
    if not course.can_edit(request.user.person):
        return redirect('app:course', courseid)

    models.Grade.objects.get_or_create(course=course, person=student)
    return redirect('app:add_student_list', courseid)
@login_required
def add_student_query(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    if not course.can_edit(request.user.person):
        return redirect('app:course', courseid)

    qr = models.Person.objects.exclude(grade__course=course).filter(
        studentrecord__status='C').order_by('family_name', 'given_name')
    form = forms.StudentSearchForm(request.GET,
                                   initial={'include': course.multi_center})
    form.is_valid()
    if not form.cleaned_data.get('include'):
        qr = qr.filter(studentrecord__center=course.center,
                       studentrecord__status='C')
    if form.cleaned_data.get('query'):
        q1 = Q()
        for sec in form.cleaned_data['query'].split(';'):
            q2 = Q()
            for w in sec.strip().split():
                q2 = q2 & (Q(given_name__icontains=w) | \
                           Q(family_name__icontains=w) | \
                           Q(user__username__icontains=w))
            q1 = q1 | q2
        qr = qr.filter(q1)
    if form.cleaned_data.get('courses'):
        qr = qr.filter(grade__course__template__in=form.cleaned_data['courses'])
    return render(request, 'app/add_student_query.html',
                  {'form': form, 'students': qr, 'course': course})
@login_required
def add_student_list(request, courseid):
    return render(request, 'app/add_student_list.html',
                  {'grades': models.Grade.objects.filter(
                      course=courseid).order_by('person__family_name',
                                                'person__given_name')})
@login_required
def add_student_search(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    if not course.can_edit(request.user.person):
        return redirect('app:course', courseid)

    return render(request, 'app/add_student_search.html',
                  {'course': course})
@login_required
def edit_schedule(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    if not course.can_edit(request.user.person):
        return redirect('app:course', courseid)

    if request.method == 'POST':
        form = forms.CalendarForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            data['mode'] = 'weekly'
            course.schedule = data
            course.save()
            return render(request, 'app/view_schedule.html',
                          {'course': course})
    else:
        form = forms.CalendarForm(initial=course.schedule or {})
    return render(request, 'app/edit_schedule.html',
                  {'course': course, 'form': form})

@login_required
def list_centers(request):
    return render(request, 'app/center_catalog.html',
                  {'centers': models.Center.objects.filter(
                      active=True).order_by('name')})

@login_required
def course_catalog(request):
    return render(request, 'app/course_catalog.html',
                  {'courses': models.CourseTemplate.objects.filter(
                      active=True).order_by('title'),
                   'staff_view': request.user.person.staffrecord_set.all().filter(status='C').exists()})

@login_required
def course_resources(request, courseid):
    if not request.user.is_staff and not request.user.person.staffrecord_set.all().filter(status='C').exists():
        raise PermissionDenied()
    course = get_object_or_404(models.CourseTemplate, pk=courseid)
    if request.method == 'POST':
        form = forms.AddFileForm(request.POST, request.FILES)
        if form.is_valid():
            sf = form.save(commit=False)
            sf.course = course
            if not request.user.is_staff:
                sf.owner = request.user.person
            sf.save()
            form = forms.AddFileForm()
    else:
        form = forms.AddFileForm()
    qs = models.SharedFile.objects.filter(course=course).order_by('title')
    if not request.user.is_staff:
        qs = qs.filter(Q(owner__isnull=True) | Q(owner=request.user.person))
    return render(request, 'app/course_resources.html', {
        'course': course,
        'form': form,
        'files': qs,
    })

@login_required
def degree_catalog(request):
    return render(request, 'app/degree_catalog.html',
                  {'degrees': models.Degree.objects.filter(
                      active=True).order_by('name')})

@login_required
def student_info(request, studentid):
    student = get_object_or_404(models.Person, pk=studentid)
    s_centers = student.studentrecord_set.values_list('center', flat=True)
    i_centers = student.staffrecord_set.values_list('center', flat=True)
    director_centers = models.StaffRecord.objects.filter(
        person=request.user.person, role__in=['D', 'R'], status='C',
        center__in=s_centers.union(i_centers)).values_list(
            'center', flat=True)
    if request.user.is_staff:
        director_centers = s_centers.union(i_centers)
    is_director = len(director_centers) > 0
    is_instructor = models.Grade.objects.filter(
        (Q(course__instructor=request.user.person) |
         Q(course__associate_instructors=request.user.person))
    ).filter(person=student).exists()
    if not is_director and not is_instructor:
        raise PermissionDenied()
    s_applications = []
    i_applications = []
    transcript = []
    contact_form = None
    contact_form_open = False
    if is_director:
        transcript = student.grade_set.all()
        s_applications = student.studentrecord_set.all().filter(
            center__in=director_centers)
        i_applications = student.staffrecord_set.all().filter(
            center__in=director_centers)
        if request.method == 'POST':
            contact_form = forms.ContactUpdateForm(request.POST,
                                                   instance=student)
            if contact_form.is_valid():
                contact_form.save()
            else:
                contact_form_open = True
        else:
            contact_form = forms.ContactUpdateForm(instance=student)
    return render(request, 'app/student_info.html',
                  {'student': student,
                   'emails': student.emails.filter(active=True),
                   'phones': student.phones.filter(active=True),
                   'mailings': student.mailings.filter(active=True),
                   'is_director': is_director,
                   'transcript': transcript,
                   'student_applications': s_applications,
                   'instructor_applications': i_applications,
                   'contact_form': contact_form,
                   'contact_form_open': contact_form_open,
                   })

@login_required
def current_popups(request, dismiss=None):
    if dismiss is not None:
        models.PopupMessage.objects.filter(id=dismiss).update(
            dismissed=True)
    popups = models.PopupMessage.objects.filter(
        person=request.user.person, dismissed=False).order_by('sent')
    return render(request, 'app/popup_list.html',
                  {'popups': popups[:3],
                   'remaining': max(popups.count()-3, 0)})

def send_message(sender, recipients, text):
    from django.utils.timezone import now
    # TODO: send email
    for recipient in recipients:
        p = models.PopupMessage()
        p.person = recipient
        p.sent = now()
        p.text = text
        p.sender = sender
        p.save()

####################
### CENTERS
####################

def center_admin(fn):
    @login_required
    def _fn(request, centerid, *args, **kwargs):
        center = get_object_or_404(models.Center, pk=centerid)
        if not center.is_admin(request.user.person):
            raise PermissionDenied()
        return fn(request, center, *args, **kwargs)
    return _fn

@center_admin
def new_course(request, center):
    if request.method == 'POST':
        form = forms.NewCourseForm(center, request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.center = center
            course.save()
            return redirect('app:course', course.id)
    else:
        form = forms.NewCourseForm(center)
    return render(request, 'app/new_course.html', {'form': form})

@center_admin
def view_instructors(request, center):
    qs = models.StaffRecord.objects.filter(center=center)
    if request.method == 'GET':
        filter_form = forms.StaffRecordFilterForm(request.GET)
        qs = filter_form.make_queryset(center)
        form = forms.StaffRecordFormset(queryset=qs)
    else:
        filter_form = forms.StaffRecordFilterForm(request.POST)
        qs = filter_form.make_queryset(center)
        form = forms.StaffRecordFormset(request.POST, queryset=qs)
        if form.is_valid():
            form.save()
            for sr, changed in form.changed_objects:
                if 'status' in changed and sr.status == 'C' and sr.acceptance_date is None:
                    sr.center_approved = True
                    if sr.role in ['A', 'R'] or request.user.is_staff:
                        sr.advance_approved = True
                    sr.save()
    return render(request, 'app/view_instructors.html',
                  {'instructors': form, 'filter_form': filter_form,
                   'center': center})

@center_admin
def view_students(request, center, status):
    qs = models.StudentRecord.objects.filter(center=center)
    if status is not None:
        qs = qs.filter(status=status)
    if request.method == 'POST':
        form = forms.StudentRecordFormset(request.POST, queryset=qs)
        if form.is_valid():
            form.save()
    else:
        form = forms.StudentRecordFormset(queryset=qs)
    return render(request, 'app/view_students.html',
                  {'students': form, 'count': qs.count(), 'status': status,
                   'center': center})

class CenterAdminMixin(AccessMixin):
    def dispatch(self, request, centerid, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.center = get_object_or_404(models.Center, pk=centerid)
        if not self.center.is_admin(request.user.person):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

class MessageCenterStudentsView(CenterAdminMixin, FormView):
    form_class = forms.NewPopupForm
    template_name = 'app/message_center_students.html'
    success_url = '/dashboard' # TODO

    def form_valid(self, form):
        send_message(self.request.user.person,
                     [sr.person
                      for sr in models.StudentRecord.objects.filter(
                              center=self.center, status='C')],
                     form.cleaned_data['text'])
        return super().form_valid(form)

@center_admin
def center_report(request, center):
    return render(request, 'app/reports.html',
                  {'center': center, 'form': forms.TallySheetForm(
                      initial={'year': datetime.date.today().year})})

@center_admin
def center_tally(request, center):
    form = forms.TallySheetForm(request.GET)
    form.is_valid()
    year = form.cleaned_data.get('year', datetime.date.today().year)
    semester = semester=form.cleaned_data.get('semester')
    courses = models.Course.objects.filter(year=year, semester=semester,
                                           center=center)
    grades = models.Grade.objects.filter(course__in=courses).exclude(
        value='W')
    ct = collections.Counter()
    for g in grades:
        ct[g.person] += g.course.template.credits
    rows = []
    semester_seq = [None, 'Wi', 'Sp', 'Su', 'Fa']
    for person in ct:
        home, known = person.home_country
        charge = ct[person]*home.credit_fee
        new_student = False
        graduating = False
        deg_charge = 0
        if models.StudentRecord.objects.filter(
                person=person, center=center, status='C').exists():
            if not models.Grade.objects.filter(person=person, course__year__lt=year).exists():
                gr_list = sorted(models.Grade.objects.filter(
                    person=person, course__year=year),
                                 key=lambda g: g.course.sort_key())
                new_student = ((gr_list[0].course.semester == semester)
                               and (gr_list[0].course.center == center))
            if new_student:
                charge += home.student_fee
            degrees = models.DegreeAward.objects.filter(
                person=person, year=year, semester=semester, status='A')
            for degree in degrees:
                if degree.walking:
                    deg_charge += 90
                else:
                    deg_charge += min(home.student_fee, 10)
            charge += deg_charge
        rows.append((person, home, known, ct[person], new_student,
                     deg_charge, charge))
    rows.sort(key=lambda r: str(r[0]))
    return render(request, 'app/tally_sheet.html', {
        'rows': rows, 'total_fee': sum(r[6] for r in rows),
        'total_degree': sum(r[5] for r in rows),
        'total_credits': sum(r[3] for r in rows)})

class NewCenterApplyView(AccessMixin, FormView):
    form_class = forms.NewCenterApplicationForm
    template_name = 'app/new_center_apply.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.person = request.user.person
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        center = form.save()
        center.sponsor_emails.add(models.EmailAddress.objects.create(
            email=form.cleaned_data['sponsor_email'],
            category='W'))
        center.sponsor_phones.add(models.PhoneAddress.objects.create(
            phone=form.cleaned_data['sponsor_phone'],
            category='W'))
        models.StaffRecord.objects.create(center=center, person=self.person,
                                          status='C', role='D')
        models.MOU.objects.create(center=center,
                                  director_sig=datetime.date.today(),
                                  sponsor_sig=datetime.date.today())
        return render(self.request, 'app/new_center_apply_success.html',
                      {'center': center})

@center_admin
def center_budget(request, center, year=None):
    year = year or datetime.date.today().year
    all_budgets = models.CenterBudget.objects.filter(center=center)
    budget = all_budgets.filter(year=year).first()
    if budget is None:
        if all_budgets.exists():
            last_year = all_budgets.aggregate(Max('year'))['year__max']
            old_budget = all_budgets.filter(year=last_year).first()
            budget = all_budgets.filter(year=last_year).first()
            budget.pk = None
            budget._state.adding = True
            budget.year = year
            budget.save()
            for fee in old_budget.centerfees_set.all():
                fee.pk = None
                fee._state.adding = True
                fee.budget = budget
                fee.save()
        else:
            budget = models.CenterBudget()
            budget.center = center
            budget.year = year
            budget.save()
        for sr in center.staffrecord_set.all().filter(status='C'):
            cs = models.CenterStipend()
            cs.budget = budget
            cs.staff = sr
            cs.save()
    return render(request, 'app/center_budget.html', {
        'budget': budget,
        'other_budgets': all_budgets.order_by('year'),
        'fees': budget.centerfees_set.all().order_by('country__name'),
        'courses': budget.expectedcourse_set.all().order_by('course__title'),
        'stipends': budget.centerstipend_set.all().order_by('-stipend'),
        'add_fee': forms.NewCenterFeeForm(),
        'add_course': forms.NewExpectedCourseForm(),
        'countries': json.dumps(dict([
            (i, float(v)) for i, v in
            models.Country.objects.all().values_list('id', 'credit_fee')])),
    })
@center_admin
def center_budget_expenses(request, center, budgetid):
    budget = get_object_or_404(models.CenterBudget, pk=budgetid)
    form = forms.CenterBudgetExpenseForm(request.POST, instance=budget)
    if form.is_valid():
        form.save()
    return render(request, 'app/center_budget_expenses.html',
                  {'budget': budget})
@center_admin
def center_budget_income(request, center, budgetid):
    budget = get_object_or_404(models.CenterBudget, pk=budgetid)
    form = forms.CenterBudgetIncomeForm(request.POST, instance=budget)
    if form.is_valid():
        form.save()
    return render(request, 'app/center_budget_income.html',
                  {'budget': budget})
@center_admin
def center_budget_stipend(request, center, stipendid):
    stipend = get_object_or_404(models.CenterStipend, pk=stipendid)
    form = forms.CenterStipendForm(request.POST, instance=stipend)
    if form.is_valid():
        form.save()
    return render(request, 'app/center_budget_stipend.html',
                  {'stipend': stipend})
@center_admin
def center_budget_fee(request, center, feeid):
    fee = get_object_or_404(models.CenterFees, pk=feeid)
    form = forms.CenterFeeForm(request.POST, instance=fee)
    if form.is_valid():
        form.save()
    return render(request, 'app/center_budget_fee.html', {'fee': fee})
@center_admin
def center_budget_new_fee(request, center, budgetid):
    budget = get_object_or_404(models.CenterBudget, pk=budgetid)
    form = forms.NewCenterFeeForm(request.POST)
    if form.is_valid():
        fee = form.save(commit=False)
        fee.budget = budget
        fee.save()
        return render(request, 'app/center_budget_fee.html', {'fee': fee})
    return render(request, 'app/empty_response.html')
@center_admin
def center_budget_new_course(request, center, budgetid):
    budget = get_object_or_404(models.CenterBudget, pk=budgetid)
    form = forms.NewExpectedCourseForm(request.POST)
    if form.is_valid():
        course = form.save(commit=False)
        course.budget = budget
        course.save()
        return render(request, 'app/center_budget_course.html',
                      {'course': course})
    return render(request, 'app/empty_response.html')
@center_admin
def center_budget_enrollment(request, center, enrollmentid):
    enrollment = get_object_or_404(models.ExpectedEnrollment,
                                   pk=enrollmentid)
    form = forms.ExpectedEnrollmentForm(request.POST, instance=enrollment)
    if form.is_valid():
        form.save()
    return render(request, 'app/center_budget_enrollment.html',
                  {'enrollment': enrollment})
@center_admin
def center_budget_new_enrollment(request, center, courseid):
    course = get_object_or_404(models.ExpectedCourse, pk=courseid)
    form = course.new_country_form(request.POST)
    if form.is_valid():
        enrollment = form.save(commit=False)
        enrollment.course = course
        enrollment.save()
        return render(request, 'app/center_budget_enrollment.html',
                      {'enrollment': enrollment})
    print(request.POST)
    print(form.errors)
    return render(request, 'app/empty_response.html')

####################
### Instructors
####################

class StaffApplyView(AccessMixin, FormView):
    form_class = forms.StaffApplicationForm
    template_name = 'app/staff_apply.html'

    def dispatch(self, request, centerid, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.center = get_object_or_404(models.Center, pk=centerid)
        self.person = request.user.person
        if models.StaffRecord.objects.filter(
                center=self.center, person=self.person).exists():
            # TODO: explain?
            return redirect('app:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['center'] = self.center
        return ctx

    def form_valid(self, form):
        form.instance.center = self.center
        form.instance.person = self.person
        sr = form.save()
        # TODO: notify director?
        return render(self.request, 'app/student_apply_success.html',
                      {'sr': sr})

class MessageCourseStudentsView(AccessMixin, FormView):
    form_class = forms.NewPopupForm
    template_name = 'app/message_center_students.html' # TOOD?
    success_url = '/dashboard' # TODO

    def dispatch(self, request, courseid, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.course = get_object_or_404(models.Course, pk=courseid)
        if not self.course.can_edit(request.user.person):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        send_message(self.request.user.person,
                     [grade.person for grade in models.Grade.objects.filter(
                         course=self.course)],
                     form.cleaned_data['text'])
        return super().form_valid(form)

####################
### Students
####################

class StudentApplyView(AccessMixin, FormView):
    form_class = forms.StudentApplicationForm
    template_name = 'app/student_apply.html'

    def dispatch(self, request, centerid, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.center = get_object_or_404(models.Center, pk=centerid)
        self.person = request.user.person
        if models.StudentRecord.objects.filter(
                center=self.center, person=self.person).exists():
            # TODO: explain?
            return redirect('app:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['center'] = self.center
        return ctx

    def form_valid(self, form):
        form.instance.center = self.center
        form.instance.person = self.person
        form.instance.church_membership = str(form.cleaned_data['membership_number']) + ' ' + form.cleaned_data['membership_unit']
        sr = form.save()
        message = make_email('Gateway ADVANCE Church Recommendation',
                             sr.church_rec_email,
                             'app/church_recommendation_email.html',
                             {'sr': sr})
        message.send()
        return render(self.request, 'app/student_apply_success.html',
                      {'sr': sr})

class ChurchEndorsementView(UpdateView):
    model = models.StudentRecord
    form_class = forms.ChurchEndorsementForm
    template_name_suffix = '_endorsement_form'

    def form_valid(self, form):
        form.instance.pastor_date = datetime.date.today()
        expl = []
        if not form.instance.good_character:
            expl += ['Character', form.cleaned_data['good_character_expl']]
        if not form.instance.good_standing:
            expl += ['Standing', form.cleaned_data['good_standing_expl']]
        if not form.instance.endorsement:
            expl += ['Endorsement', form.cleaned_data['endorsement_expl']]
        form.instance.pastor_explanation = '\n\n'.join(expl)
        form.save()
        return render(self.request, 'app/endorsement_submitted.html',
                      {'sr': self.object})

@login_required
def course_search(request):
    centers = models.StudentRecord.objects.filter(
        person=request.user.person, status='C').values_list(
            'center', flat=True)
    courses = models.Course.objects.filter(
        Q(center__in=centers) | Q(multi_center=True),
        accepting_enrollments=True).exclude(
            grade__person=request.user.person).order_by(
                'center__name', 'template__title')
    return render(request, 'app/course_search.html',
                  {'courses': courses})

@login_required
def enroll(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    qr = models.StudentRecord.objects.filter(
        person=request.user.person, status='C')
    if not course.multi_center:
        qr = qr.filter(center=course.center)
    if qr.exists():
        grade = models.Grade.objects.get_or_create(
            course=course, person=request.user.person,
            defaults={'value': 'IP'})[0]
        return render(request, 'app/confirm_enrollment.html',
                      {'grade': grade})
    else:
        raise PermissionDenied()

@login_required
def degree_search(request):
    person = request.user.person
    has_already = person.degreeaward_set.filter(
        status__in=['S', 'A']).values_list('degree', 'degree__category')
    qr = models.Degree.objects.order_by('name').filter(active=True).exclude(
        Q(category='C', credits__gt=(person.credits_earned
                                     + person.credits_in_progress
                                     - person.certificate_credits))
    ).exclude(id__in=[h[0] for h in has_already])
    if any(h[1] == 'D' for h in has_already):
        qr = qr.exclude(category='D')
    if any(h[1] == 'L' for h in has_already):
        qr = qr.exclude(category='L')
    return render(request, 'app/degree_search.html',
                  {'degrees': [d for d in qr
                               if d.check_requirements(person, False)]})

def check_degree(degree, person):
    cond = Q(degree=degree)
    credits = person.credits_earned + person.credits_in_progress
    if degree.category in ['D', 'L']:
        cond = cond | Q(degree__category=degree.category)
    else:
        credits -= person.certificate_credits
    if credits < degree.credits:
        return False
    return not models.DegreeAward.objects.filter(cond).exclude(status='R').exists()
@login_required
def degree_apply(request, degreeid):
    degree = get_object_or_404(models.Degree, pk=degreeid)
    person = request.user.person
    if check_degree(degree, person):
        cls = forms.CertificateForm if degree.category == 'C' else forms.DiplomaForm
        if request.method == 'POST':
            form = cls(request.POST)
            if form.is_valid():
                app = form.save(commit=False)
                app.person = person
                app.degree = degree
                app.save()
                return render(request, 'app/degree_apply_success.html',
                              {'degree': degree})
        else:
            form = cls()
        return render(request, 'app/degree_apply_form.html',
                      {'form': form, 'degree': degree})
    else:
        return render(request, 'app/degree_apply_reject.html',
                      {'degree': degree})

GPA_VALUES = {
    'A': 4.0,
    'A-': 3.7,
    'B+': 3.3,
    'B': 3.0,
    'B-': 2.7,
    'C+': 2.3,
    'C': 2.0,
    'C-': 1.7,
    'D+': 1.3,
    'D': 1.0,
    'D-': 0.7,
    'F': 0.0,
}

@login_required
def transcript(request):
    import io
    import collections
    from django.http import FileResponse
    from django_tex.core import compile_template_to_pdf
    person = request.user.person
    context = {
        'person': person,
        'achievements': models.DegreeAward.objects.filter(
            person=person, status='A').order_by('awarded'),
        'email': person.emails.all().filter(active=True).first(),
        'address': person.mailings.all().filter(active=True).first(),
    }
    sr = models.StudentRecord.objects.filter(person=person, status='C').first()
    if sr is None:
        sr = models.StudentRecord.objects.filter(person=person, status='F').first()
    if sr is not None:
        context['center'] = sr.center
        context['center_address'] = sr.center.mailings.all().filter(
            active=True).first()
    grades = models.Grade.objects.filter(person=person).order_by('course__template__title')
    semesters = collections.defaultdict(list)
    for grade in grades:
        semesters[grade.course.sort_key()[:2]].append(grade)
    blocks = []
    total_att = 0
    total_get = 0
    gpa_att = 0
    gpa_get = 0
    for key in sorted(semesters.keys()):
        y0 = key[0]
        y1 = y0 + 1
        if semesters[key][0].course.semester != 'Fa':
            y0, y1 = y0 - 1, y0
        dct = {
            'header': f'{y0}-{y1} {semesters[key][0].course.get_semester_display()} Semester',
            'grades': sorted(semesters[key], key=lambda x: x.course.sort_key()),
        }
        att = 0
        get = 0
        for g in dct['grades']:
            if g.value != 'Au':
                cr = g.course.template.credits
                att += cr
                if g.value not in ['F', 'IP', 'W']:
                    get += cr
                if g.value in GPA_VALUES:
                    gpa_att += cr
                    gpa_get += GPA_VALUES[g.value] * cr
        dct['attempted'] = att
        dct['earned'] = get
        blocks.append(dct)
        total_att += att
        total_get += get
    context['semesters'] = blocks
    context['attempted'] = total_att
    context['earned'] = total_get
    if gpa_att > 0:
        context['gpa'] = round(gpa_get/gpa_att, 2)
    else:
        context['gpa'] = 0
    print(context)
    PDF = compile_template_to_pdf('app/transcript.tex', context)
    buf = io.BytesIO(PDF)
    return FileResponse(buf, as_attachment=True, filename="transcript.pdf")

####################
### Staff
####################

class MessageAllUsersView(AccessMixin, FormView):
    form_class = forms.NewPopupForm
    template_name = 'app/message_center_students.html' # TOOD?
    success_url = '/dashboard' # TODO

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        send_message(self.request.user.person,
                     models.Person.objects.all(),
                     form.cleaned_data['text'])
        return super().form_valid(form)

class StaffReportView(AccessMixin, FormView):
    form_class = forms.StaffStatsForm
    template_name = 'app/staff_stats.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        term = get_current_term()
        return {
            'start_year': datetime.date.today().year - 1,
            'start_semester': term,
            'end_year': datetime.date.today().year,
            'end_semester': term,
        }

    def make_date_query(self, form, prefix, **other):
        seq = ['Sp', 'Su', 'Fa', 'Wi']
        s1 = form.cleaned_data['start_semester']
        s2 = form.cleaned_data['end_semester']
        si1 = seq.index(s1)
        si2 = seq.index(s2)
        y1 = form.cleaned_data['start_year']
        y2 = form.cleaned_data['end_year']
        if y1 == y2:
            sems = [] if si1 > si2 else seq[si1:si2+1]
            return Q(**{prefix+'year': y1,
                        prefix+'semester__in': sems}, **other)
        else:
            return (Q(**{prefix+'year': y1,
                         prefix+'semester__in': seq[si1:]}, **other) |
                    Q(**{prefix+'year__gt': y1,
                         prefix+'year__lt': y2}, **other) |
                    Q(**{prefix+'year': y2,
                         prefix+'semester__in': seq[:si2+1]}, **other))

    def make_date_range(self, form):
        s1 = form.cleaned_data['start_semester']
        s2 = form.cleaned_data['end_semester']
        y1 = form.cleaned_data['start_year']
        y2 = form.cleaned_data['end_year']
        start_month = {'Sp': 1, 'Su': 6, 'Fa': 8, 'Wi': 12}
        end_month = {'Sp': 6, 'Su': 8, 'Fa': 12, 'Wi': 1}
        return (datetime.date(year=y1, month=start_month[s1], day=1),
                datetime.date(year=y2 + int(s2 == 'Wi'),
                              month=end_month[s2], day=1))

    def form_valid(self, form):
        grades = models.Grade.objects.filter(
            self.make_date_query(form, 'course__')).exclude(value='W')
        person_keys = ['sex', 'ethnicity', 'marital_status',
                       'denomination']
        for key in person_keys:
            if form.cleaned_data[key]:
                grades = grades.filter(
                    **{'person__'+key: form.cleaned_data[key]})
        course_keys = ['language', 'country', 'delivery_format']
        for key in course_keys:
            if form.cleaned_data[key]:
                grades = grades.filter(
                    **{'course__'+key: form.cleaned_data[key]})
        sbc = form.cleaned_data['sbc_fundable']
        if sbc is not None:
            grades = grades.filter(course__center__fte_eligible=sbc)
        centers = form.cleaned_data['center']
        if centers:
            grades = grades.filter(course__center__in=centers)

        students = set()
        gpa_att = 0
        gpa_get = 0
        credits = 0
        for g in grades:
            students.add(g.person)
            cr = g.course.template.credits
            credits += cr
            if g.value in GPA_VALUES:
                gpa_att += cr
                gpa_get += cr * GPA_VALUES[g.value]

        dates = self.make_date_range(form)

        inactive_students = set(models.StudentRecord.objects.filter(
            acceptance_date__lte=dates[1], status='C').values_list(
                'person', flat=True)) - students

        # TODO: new centers
        # TODO: eligible to graduate

        stats = {
            'headcount': len(students),
            'new_students': models.StudentRecord.objects.filter(
                acceptance_date__range=dates).count(),
            'new_instructors': models.StaffRecord.objects.filter(
                acceptance_date__range=dates, role__in=['I', 'A']).count(),
            'new_staff': models.StaffRecord.objects.filter(
                acceptance_date__range=dates).count(),
            'inactive_students': len(inactive_students),
            'total_credits': credits,
            'gpa': round(gpa_get/max(gpa_att, 1), 2),
            'degree_awards': models.DegreeAward.objects.filter(
                awarded__range=dates).count(),
        }
        return render(self.request, self.template_name,
                      {'form': form, 'stats': stats})
