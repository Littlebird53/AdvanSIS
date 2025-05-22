from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.views.generic.edit import FormView
from app import models
from app import forms
import itertools

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('app:dashboard')
    return render(request, 'app/index.html')

def permission_denied_page(request, exception):
    return render(request, 'errors/403.html')

def sort_courses(courses):
    seq = ['Sp', 'Su', 'Fa', 'Wi']
    term_map = [0, # skip
                0, 0, 0, 0, 0, # Jan-May
                1, 1, # Jun-Jul
                2, 2, 2, 2, # Aug-Nov
                3, # Dec
                ]
    import datetime
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
        if record.status in ['CI', 'CA', 'D', 'R']:
            current.append((record, courses, False))
        else:
            other.append((record, courses, False))
    current.sort(key=lambda x: (x[0].center.name, x[0].status))
    other.sort(key=lambda x: (x[0].center.name, x[0].status))
    print(current, other)
    return render(request, 'app/dashboard.html',
                  {
                      'form': form,
                      'message': message,
                      'records': current + other,
                  })

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
        for w in form.cleaned_data['query'].split():
            qr = qr.filter(Q(given_name__icontains=w) | \
                           Q(family_name__icontains=w) | \
                           Q(user__username=w))
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
def list_centers(request):
    return render(request, 'app/center_catalog.html',
                  {'centers': models.Center.objects.filter(
                      active=True).order_by('name')})

@login_required
def course_catalog(request):
    return render(request, 'app/course_catalog.html',
                  {'courses': models.CourseTemplate.objects.filter(
                      active=True).order_by('title')})

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
    is_director = models.StaffRecord.objects.filter(
        person=request.user.person, status__in=['D', 'G'],
        center__in=s_centers.union(i_centers)).exists()
    is_instructor = models.Grade.objects.filter(
        (Q(course__instructor=request.user.person) |
         Q(course__associate_instructors=request.user.person))
    ).filter(person=student).exists()
    if not is_director and not is_instructor:
        raise PermissionDenied()
    return render(request, 'app/student_info.html',
                  {'student': student,
                   'emails': student.emails.filter(active=True),
                   'phones': student.phones.filter(active=True),
                   'mailings': student.mailings.filter(active=True),
                   'transcript': student.grade_set.all() if is_director else []})

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

@login_required
def new_course(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    if not center.is_admin(request.user.person):
        raise PermissionDenied()
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

@login_required
def view_instructors(request, centerid, status):
    center = get_object_or_404(models.Center, pk=centerid)
    if not center.is_admin(request.user.person):
        raise PermissionDenied()
    qs = models.StaffRecord.objects.filter(center=center)
    if status is not None:
        qs = qs.filter(status=status)
    if request.method == 'POST':
        form = forms.StaffRecordFormset(request.POST, queryset=qs)
        if form.is_valid():
            form.save()
    else:
        form = forms.StudentRecordFormset(queryset=qs)
    header = [(None, 'All Staff'),
              ('CI', 'Current Instructors'),
              ('FI', 'Former Instructors'),
              ('AI', 'Pending Applications'),
              ('RI', 'Rejected Applications'),
              ('CA', 'Current Associate Instructors'),
              ('FA', 'Former Associate Instructors'),
              ('D', 'Directors'),
              ('R', 'Registrars')]
    return render(request, 'app/view_instructors.html',
                  {'instructors': form, 'count': len(qs), 'status': status,
                   'center': center, 'header': header})

@login_required
def view_students(request, centerid, status):
    center = get_object_or_404(models.Center, pk=centerid)
    if not center.is_admin(request.user.person):
        raise PermissionDenied()
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

####################
### Instructors
####################

@login_required
def instructor_apply(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    models.StaffRecord.objects.get_or_create(
        center=center, person=request.user.person)
    return redirect('app:dashboard')

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

@login_required
def student_apply(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    models.StudentRecord.objects.get_or_create(
        center=center, person=request.user.person)
    return redirect('app:dashboard')

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
