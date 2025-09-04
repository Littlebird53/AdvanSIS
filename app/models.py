from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import modelform_factory
from django.shortcuts import render, get_object_or_404
from django.template import Context, Template
from django.template.loader import get_template
import datetime
from functools import cached_property

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

def calc_gpa(grades, unique_only=False):
    att = 0
    get = 0
    seen = set()
    if unique_only:
        # comma sorts after +, so this makes A+ < A < A-
        grades = sorted(grades, key=lambda g: str(g.value)+',')
    for g in grades:
        if g.value in GPA_VALUES:
            if unique_only:
                if g.course and g.course.template in seen:
                    continue
                seen.add(g.course.template)
            cr = g.course.template.credits
            att += cr
            get += cr * GPA_VALUES[g.value]
    return round(get / max(att, 1), 2)

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

class AutosaveFormMixin:
    urls = []
    create_views = {}
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        from django.urls import path
        name = cls.__name__.lower()
        cls.urls += [
            path(name + '/<int:instanceid>/', cls.change_view, name=name),
            path(name + '/new/', cls.create_view, name='new_'+name),
        ]
        cls.edit_url_name = 'app:'+name
        cls.create_url_name = 'app:new_'+name
        cls.create_views[name] = cls
    @classmethod
    def build_form(cls, name, *args, **kwargs):
        blob = cls.forms[name]
        fcls = modelform_factory(cls, fields=blob['fields'])
        prefix = cls.__name__.lower() + '_' + name
        if 'instance' in kwargs:
            prefix += '_' + str(kwargs['instance'].pk)
        form = fcls(*args, **kwargs, prefix=prefix)
        for wname, attrs in blob.get('widgets', {}).items():
            form.fields[wname].widget.attrs.update(attrs)
        cls.modify_form(form)
        return form
    @classmethod
    def change_view(cls, request, instanceid):
        instance = get_object_or_404(cls, pk=instanceid)
        if not cls.check_permissions(request, instance, {}):
            raise PermissionDenied()
        if request.method == 'DELETE':
            instance.delete()
            return render(request, 'app/empty_response.html')
        fname = request.POST.get('form', 'default')
        form = cls.build_form(fname, request.POST, instance=instance)
        if form.is_valid():
            form.save()
        return render(request, cls.forms[fname]['template'],
                      instance.as_context(fname))
    @classmethod
    def create_view(cls, request):
        fname = request.POST.get('form', 'new')
        by_id = {}
        for name, model in cls.forms[fname].get('id_fields', {}).items():
            val = request.POST.get(name)
            if not val or not val.isdigit():
                val = -1
            val = int(val)
            by_id[name] = get_object_or_404(model, pk=val)
        if not cls.check_permissions(request, None, by_id):
            raise PermissionDenied()
        form = cls.build_form(fname, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            for name, obj in by_id.items():
                setattr(instance, name, obj)
            instance.save()
            return render(request, cls.forms[fname]['template'],
                          instance.as_context(fname))
        return render(request, 'app/empty_response.html')
    @classmethod
    def check_permissions(cls, request, instance, by_id):
        return True
    @classmethod
    def modify_form(cls, form):
        pass
    def as_context(self, name):
        from django.utils.safestring import mark_safe
        rid = self.__class__.__name__.lower()
        rid += '_' + name
        rid += '_' + str(self.pk)
        fields = f'id="{rid}" hx-target="#{rid}" hx-swap="outerHTML"'
        return {'instance': self, 'id_fields': mark_safe(fields)}
    def as_row(self, name='default'):
        from django.utils.safestring import mark_safe
        tname = self.forms[name]['template']
        return get_template(tname).render(self.as_context(name))

class Language(models.Model):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    @classmethod
    def get_english(cls):
        return cls.objects.filter(code='eng')

class EmailAddress(models.Model):
    active = models.BooleanField(default=True)
    email = models.EmailField()
    category = models.CharField(
        choices=[('P', 'Personal'), ('W', 'Work'), ('O', 'Other')],
        max_length=1, null=True)

class PhoneAddress(models.Model):
    active = models.BooleanField(default=True)
    phone = models.CharField(max_length=30)
    category = models.CharField(
        choices=[('H', 'Home'), ('M', 'Mobile'), ('W', 'Work'),
                 ('O', 'Other')],
        max_length=1, null=True)

class Country(models.Model):
    name = models.CharField(max_length=50)
    credit_fee = models.DecimalField(max_digits=5, decimal_places=2)
    student_fee = models.DecimalField(max_digits=5, decimal_places=2)
    postal_code = models.CharField(max_length=3)

    def __str__(self):
        return f'{self.name} ({self.postal_code})'

    class Meta:
        ordering = ['name']

class MailingAddress(models.Model):
    active = models.BooleanField(default=True)
    address = models.TextField()
    attention = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=10, blank=True, null=True)
    zip_code = models.CharField(max_length=10, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL,
                                null=True)
    category = models.CharField(
        choices=[('H', 'Home'), ('W', 'Work'), ('S', 'Shipping'),
                 ('O', 'Other')],
        max_length=1, null=True)

    @property
    def last_line(self):
        pieces = [self.city, self.state, self.zip_code]
        if self.country:
            pieces.append(self.country.postal_code)
        else:
            pieces.append('US')
        return ', '.join(p for p in pieces if p)

    @property
    def single_line(self):
        pieces = [self.address, self.last_line]
        def lineify(s):
            return ', '.join(l.strip() for l in s.splitlines())
        return ', '.join([lineify(x) for x in pieces if x])

    @property
    def as_block(self):
        lines = []
        if self.attention:
            lines.append('ATTN: ' + self.attention)
        lines.append(self.address)
        lines.append(self.last_line)
        return '\n'.join(lines)

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    given_name = models.CharField(max_length=100, null=True,
                                  verbose_name='Given (First) Name')
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    family_name = models.CharField(max_length=100,
                                   verbose_name='Family (Last) Name')
    title = models.CharField(
        choices=[('1LT', '1st Lt.'), ('ATT', 'Attorney'), ('BR', 'Brother'),
                 ('CAP', 'Captain'), ('CHP', 'Chaplain'), ('COL', 'Col.'),
                 ('DR', 'Dr.'), ('ENS', 'Ensign'), ('HON', 'Hon.'),
                 ('JU', 'Judge'), ('LC', 'Lt. Com.'), ('LT', 'Lt.'),
                 ('LTC', 'Lt. Col.'), ('MAJ', 'Major'), ('MIN', 'Minister'),
                 ('MIS', 'Miss'), ('MR', 'Mr.'), ('MRS', 'Mrs.'),
                 ('MS', 'Ms.'), ('MSG', 'MSgt.'), ('PAS', 'Pastor'),
                 ('PRF', 'Prof.'), ('PRO', 'Prof.'), ('RAB', 'Rabbi'),
                 ('RDR', 'Rev. Dr.'), ('REV', 'Rev.'), ('SGT', 'Sgt.'),
                 ('SIS', 'Sister'), ('SM', 'Sgt. Major'), ('SSG', 'SSgt,'),
                 ('TSG', 'TSGT')],
        max_length=3, blank=True, null=True)
    joint_title = models.CharField(
        choices=[('1LM', '1st Lt. and Mrs.'), ('1LT', '1st Lt.'),
                 ('ATM', 'Atty. and Mrs.'), ('ATT', 'Atty.'),
                 ('B/M', 'Bro. and Mrs.'), ('BR', 'Brother'),
                 ('C/C', 'Chaplain and Chaplain'),
                 ('C/D', 'Chaplain and Dr.'), ('C/M', 'Captain and Mrs.'),
                 ('CAP', 'Captain'), ('CH', 'Chaplain'),
                 ('CHP', 'Chaplain and Mrs.'), ('CLL', 'Col.'),
                 ('COL', 'Col. and Mrs.'), ('D/D', 'Dr. and Dr.'),
                 ('D/M', 'Dr. and Mrs.'), ('D/R', 'Dr. and Rev.'),
                 ('DR', 'Dr.'), ('DRS', 'Drs.'), ('E/M', 'Ensign and Mrs.'),
                 ('H/M', 'Hon. and Mrs.'), ('HON', 'Hon.'),
                 ('J/M', 'Judge and Mrs.'), ('L/T', 'Lt. Col.'),
                 ('LC', 'Lt. Com.'), ('LCM', 'Lt. Com. and Mrs.'),
                 ('LT', 'Lt.'), ('LTC', 'Lt. Col. and Mrs.'),
                 ('LTM', 'Lt. and Mrs.'), ('M/C', 'Mr. and Chaplain'),
                 ('M/D', 'Mr. and Dr.'), ('M/M', 'Mr. and Mrs.'),
                 ('M/R', 'Mr. and Rev.'), ('MAJ', 'Major'),
                 ('MAM', 'Major and Mrs.'), ('MIN', 'Minister'),
                 ('MIS', 'Miss'), ('MNM', 'Minister and Mrs.'),
                 ('MR', 'Mr.'), ('MRD', 'Mr. and Rev. Dr.'),
                 ('MRS', 'Mrs.'), ('MS', 'Ms.'), ('MSG', 'MSgt.'),
                 ('MSM', 'MSgt. and Mrs.'), ('P/M', 'Prof. and Mrs.'),
                 ('P/P', 'Profs.'), ('P/S', 'Pastor and Sister'),
                 ('PAD', 'Pastor and Dr.'), ('PAM', 'Pastor and Mrs.'),
                 ('PAS', 'Pastor'), ('PRF', 'Prof.'),
                 ('R/C', 'Rev. and Chaplain'), ('R/D', 'Rev. and Dr.'),
                 ('R/R', 'Rev. and Rev.'), ('RAB', 'Rabbi'),
                 ('RDD', 'Rev. Dr. and Dr.'), ('RDM', 'Rev. Dr. and Mrs.'),
                 ('RDR', 'Rev. Dr.'), ('RE', 'Rev.'),
                 ('REV', 'Rev. and Mrs.'), ('S/M', 'Sgt. and Mrs.'),
                 ('SGM', 'SSgt. and Mrs.'), ('SGT', 'Sgt.'),
                 ('SIS', 'Sister'), ('SMM', 'Sgt. Major and Mrs.'),
                 ('SSG', 'SSgt.'), ('TSG', 'TSGT'),
                 ('TSM', 'TSGT and Mrs.')],
        max_length=100, blank=True, null=True)
    suffix = models.CharField(max_length=100, blank=True, null=True,
                              choices=[('Jr.', 'Jr.'), ('Sr.', 'Sr.'),
                                       ('I', 'I'), ('II', 'II'),
                                       ('III', 'III'), ('IV', 'IV'),
                                       ('V', 'V')])
    preferred_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    sex = models.CharField(choices=[('M', 'Male'), ('F', 'Female')],
                           max_length=1, null=True)
    marital_status = models.CharField(
        choices=[('S', 'Single'), ('M', 'Married'),
                 ('D', 'Divorced or Separated'), ('W', 'Widowed')],
        max_length=1, blank=True, null=True)
    denomination = models.CharField(
        choices=[('A', 'Anglican'),
                 ('B', 'Baptist (Non-SBC)'),
                 ('C', 'Catholic'),
                 ('c', 'Church of Christ'),
                 ('G', 'Church of God'),
                 ('E', 'Eastern Orthodox'),
                 ('e', 'Episcopalian'),
                 ('L', 'Lutheran'),
                 ('J', 'Messianic Judaism'),
                 ('M', 'Methodist'),
                 ('N', 'Nondenominational'),
                 ('P', 'Pentecostal'),
                 ('7', 'Seventh Day Adventist'),
                 ('S', 'Southern Baptist'),
                 ('T', 'Presbyterian'),
                 ('R', 'Reformed (Non-Baptist)'),
                 ('O', 'Other Denomination'),
                 ('U', 'Unknown')],
        max_length=1, default='U')
    ethnicity = models.CharField(
        choices=[('0', 'Unknown'), ('1', 'African'),
                 ('2', 'Native American'),
                 ('3', 'Asian or Pacific Islander'), ('4', 'Hispanic'),
                 ('5', 'Caucasian'), ('6', 'Other')],
        max_length=1, blank=True, null=True)
    languages_spoken = models.ManyToManyField(Language, blank=True)
    ed_level = models.CharField(max_length=3, choices=[
        ('N', 'No formal education'), ('J', 'Middle/Junior High School'),
        ('H', 'High School'), ('C', 'Some College'), ('A', 'Associates'),
        ('B', 'Bachelors'), ('m', 'Current Masters Student'),
        ('M', 'Masters'), ('d', 'Current Doctoral Student'),
        ('D', 'Doctoral/Professional Degree')],
                                blank=True, null=True,
                                verbose_name='Education Level')
    deceased = models.BooleanField(default=False)
    emails = models.ManyToManyField(EmailAddress)
    phones = models.ManyToManyField(PhoneAddress)
    mailings = models.ManyToManyField(MailingAddress)

    def __str__(self):
        return f'{self.given_name} {self.family_name} ({self.user.username})'

    @property
    def credits_earned(self):
        return sum([t.credits for t in set(
            g.course.template for g in self.grade_set.exclude(
                value__in=['F', 'Au', 'IP', 'W']))])

    @property
    def credits_in_progress(self):
        return self.grade_set.filter(value='IP').aggregate(
            v=models.Sum('course__template__credits'))['v'] or 0

    @property
    def certificate_credits(self):
        return self.achievementaward_set.filter(
            status__in=['S', 'A', 'P', 'D'], achievement__category='C',
        ).aggregate(v=models.Sum('achievement__credits'))['v'] or 0

    @property
    def potential_achievement_credits(self):
        has = sum([t.credits for t in set(
            g.course.template for g in self.grade_set.exclude(
                value__in=['F', 'Au', 'W']))])
        return has - self.certificate_credits

    @property
    def full_name(self):
        ls = [n for n in [self.given_name, self.middle_name,
                          self.family_name] if n]
        return ' '.join(ls)

    @cached_property
    def home_address(self):
        return self.mailings.all().filter(active=True, category='H').first()

    @property
    def home_country(self):
        addr = self.home_address
        if addr is None or addr.country is None:
            return Country.objects.get(postal_code='US'), False
        else:
            return addr.country, True

    @property
    def main_email(self):
        e = self.emails.all().filter(active=True, category='P').first()
        if e is None:
            e = self.emails.all().filter(active=True).first()
        return e

    @property
    def main_phone(self):
        p = self.phones.all().filter(active=True,
                                     category__in=['H', 'M']).first()
        if p is None:
            p = self.phones.all().filter(active=True).first()
        return p

    @property
    def has_profile(self):
        return self.date_of_birth is not None

    @property
    def has_address(self):
        return self.mailings.all().filter(active=True).exists()

    @property
    def latex_addr1(self):
        if self.home_address:
            return self.home_address.address
        else:
            return '~'

    @property
    def latex_addr2(self):
        if self.home_address:
            return self.home_address.last_line
        else:
            return '~'

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.date.today()
        years = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month:
            years -= 1
        elif today.month == self.date_of_birth.month and today.day < self.date_of_birth.day:
            years -= 1
        return years

    @property
    def gpa(self):
        return calc_gpa(self.grade_set.all(), True)

class Center(models.Model):
    name = models.CharField(max_length=400)
    code = models.CharField(max_length=5, null=True)
    emails = models.ManyToManyField(EmailAddress, related_name='+')
    phones = models.ManyToManyField(PhoneAddress, related_name='+')
    mailings = models.ManyToManyField(MailingAddress, related_name='+')
    fte_eligible = models.BooleanField(default=False)
    sponsor = models.CharField(max_length=100, null=True)
    sponsor_rep = models.CharField(max_length=100, null=True)
    sponsor_rep_title = models.CharField(max_length=100, null=True)
    sponsor_emails = models.ManyToManyField(EmailAddress, related_name='+')
    sponsor_phones = models.ManyToManyField(PhoneAddress, related_name='+')
    sponsor_mailings = models.ManyToManyField(MailingAddress,
                                              related_name='+')
    approved = models.BooleanField(default=False, help_text='Not approved + not active = rejected')
    active = models.BooleanField(default=True)
    coi_file = models.FileField(blank=True, null=True)

    def __str__(self):
        return self.name

    def is_admin(self, person):
        if person.user.is_staff:
            return True
        return self.staffrecord_set.filter(
            person=person, role__in=['D', 'R'], status='C').exists()

    @property
    def director(self):
        sr = self.staffrecord_set.filter(
            status='C', role='D').select_related('person').first()
        if sr:
            return sr.person

    @property
    def country(self):
        addr = self.mailings.all().filter(active=True).first()
        if addr:
            return addr.country

    @property
    def current_mou(self):
        ret = self.mou_set.all().filter(status='P').first()
        if ret is None:
            ret = self.mou_set.all().filter(status='A').first()
        if ret is None:
            ret = self.mou_set.all().order_by('expiration').last()
        return ret

    def director_stats(self):
        courses = Course.objects.filter(
            center=self, year=datetime.date.today().year,
            semester=get_current_term())
        grades = Grade.objects.filter(course__in=courses)
        ret = {
            'course_count': courses.count(),
            'approve_count': courses.filter(status__in=['A', 'L']).count(),
            'approve_percent': 0,
            'grade_count': grades.count(),
            'enter_count': grades.exclude(value='IP').count(),
            'enter_percent': 0,
            'applied_students': StudentRecord.objects.filter(
                center=self, status='A').count(),
        }
        if ret['course_count'] > 0:
            ret['approve_percent'] = round(100*ret['approve_count']/ret['course_count'])
        if ret['grade_count'] > 0:
            ret['enter_percent'] = round(100*ret['enter_count']/ret['grade_count'])
        return ret

class MOU(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    director_sig = models.DateField(blank=True, null=True)
    sponsor_sig = models.DateField(blank=True, null=True)
    advance_sig = models.DateField(blank=True, null=True)
    gs_dean_sig = models.DateField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    expiration = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=1, choices=[
        ('P', 'Pending'), ('A', 'Active'), ('E', 'Expired'),
        ('R', 'Renewed')], default='P')
    template_name = models.CharField(max_length=100,
                                     default='latex/mou_2025.tex')

    @property
    def expires_soon(self):
        return (self.expiration and
                (datetime.date.today() + datetime.timedelta(days=42) >
                 self.expiration))

    @property
    def has_expired(self):
        return self.expiration and self.expiration < datetime.date.today()

class LearningObjective(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class CourseTemplate(models.Model):
    title = models.CharField(max_length=100)
    short_title = models.CharField(max_length=100, blank=True, null=True)
    credits = models.IntegerField(default=3)
    thinkific_id = models.IntegerField(null=True, blank=True)
    division = models.CharField(max_length=1, null=True)
    number = models.IntegerField(null=True)
    description = models.TextField()
    learning_objectives = models.ManyToManyField(LearningObjective)
    active = models.BooleanField(default=True)

    @property
    def code(self):
        return f'CL{self.division}{self.number}'

    def __str__(self):
        return f'{self.title} ({self.code})'

    @property
    def display_title(self):
        return self.short_title or self.title

    LO_TEMPLATE = Template('''
    <ul>
      {% for lo in course.learning_objectives.all %}
      <li>{{lo.name}}
        {% if lo.description %}
        <details>
          <summary>Description</summary>
          <p>{{lo.description|linebreaks}}</p>
        </details>
        {% endif %}
      </li>
      {% endfor %}
    </ul>
    ''')
    def learning_objectives_block(self):
        return self.LO_TEMPLATE.render(Context({'course': self}))

SEMESTERS = [('Sp', 'Spring'), ('Su', 'Summer'), ('Fa', 'Fall'),
             ('Wi', 'Winter')]

class Course(models.Model):
    template = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE)
    center = models.ForeignKey(Center, on_delete=models.SET_NULL,
                               null=True)
    year = models.IntegerField(default=2025)
    semester = models.CharField(choices=SEMESTERS, max_length=2, null=True)
    instructors = models.ManyToManyField(
        Person, related_name='instructors', blank=True)
    schedule = models.JSONField(blank=True, null=True,
                                encoder=DjangoJSONEncoder)
    delivery_format = models.CharField(
        choices=[('I', 'In-Person'), ('H', 'Hybrid'), ('O', 'Online')],
        max_length=1, null=True)
    languages = models.ManyToManyField(Language, blank=True,
                                       default=Language.get_english)
    country = models.ForeignKey(Country, blank=True, null=True,
                                on_delete=models.SET_NULL)
    accepting_enrollments = models.BooleanField(default=True)
    multi_center = models.BooleanField(
        default=False, verbose_name='Advertize to students in other centers')
    section = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(max_length=1, default='P', choices=[
        ('P', 'Pending'), ('R', 'Rejected'), ('A', 'Approved'),
        ('L', 'Locked')])

    def __str__(self):
        return f'{self.template} {self.get_semester_display()} {self.year}'

    def can_edit(self, person):
        return person in self.instructors.all() or self.center.is_admin(person)

    def sort_key(self):
        terms = ['Sp', 'Su', 'Fa', 'Wi']
        if self.semester in terms:
            order = terms.index(self.semester)
        else:
            order = 4
        return (self.year, order, self.template.title)

    def display_schedule(self):
        from django.template.loader import get_template
        tmpl = get_template('app/display_schedule.html')
        return tmpl.render(self.schedule or {'mode': 'none'})

    @property
    def enrollment(self):
        return self.grade_set.all().count()

class Grade(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    value = models.CharField(
        choices=[('A+', 'A+'), ('A', 'A'), ('A-', 'A-'),
                 ('B+', 'B+'), ('B', 'B'), ('B-', 'B-'),
                 ('C+', 'C+'), ('C', 'C'), ('C-', 'C-'),
                 ('D+', 'D+'), ('D', 'D'), ('D-', 'D-'),
                 ('F', 'F'), ('Au', 'Audit'), ('IP', 'In-Progress'),
                 ('W', 'Withdrawn'), ('Tr', 'Transferred'), ('P', 'Pass'),
                 ],
        max_length=2, default='IP')

    def __str__(self):
        return f'{self.person} {self.course}'

    def as_form(self):
        from app.forms import GradeForm as fcls
        return fcls(instance=self)

class StudentRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current Student'), ('F', 'Former Student'),
                 ('A', 'Applied Student'), ('R', 'Rejected Student'),
                 ('W', 'Student Waiting for Church Recommendation')],
        max_length=1, default='W')
    church = models.CharField(max_length=100, blank=True, null=True)
    church_membership = models.CharField(max_length=100, blank=True,
                                         null=True)
    church_sbc = models.BooleanField(null=True)
    reference1_name = models.CharField(max_length=100, blank=True, null=True)
    reference1_email = models.EmailField(max_length=100, blank=True, null=True)
    reference1_phone = models.CharField(max_length=30, blank=True, null=True)
    reference2_name = models.CharField(max_length=100, blank=True, null=True)
    reference2_email = models.EmailField(max_length=100, blank=True, null=True)
    reference2_phone = models.CharField(max_length=30, blank=True, null=True)
    church_rec_name = models.CharField(max_length=100, blank=True,
                                       null=True)
    church_rec_email = models.EmailField(max_length=100, blank=True,
                                         null=True)
    prev_gateway = models.BooleanField(null=True)
    gateway_id = models.IntegerField(blank=True, null=True)
    called_to_ministry = models.BooleanField(null=True)
    christian_year = models.BooleanField(null=True)
    conduct_standard = models.BooleanField(null=True)
    good_character = models.BooleanField(null=True)
    good_standing = models.BooleanField(null=True)
    endorsement = models.BooleanField(null=True)
    pastor_explanation = models.TextField(blank=True, null=True)
    pastor_date = models.DateField(blank=True, null=True)
    acceptance_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.person} {self.center}'

    def sort_key(self):
        return (self.center.name, self.status)

    @property
    def status_line(self):
        return self.get_status_display()

    def stats(self):
        credits = self.person.grade_set.all().aggregate(
            total=models.Sum('course__template__credits'))['total'] or 0
        avg = 0
        if credits > 0:
            semesters = len(set(self.person.grade_set.all().values_list(
                'course__year', 'course__semester')))
            avg = round(credits / semesters)
        qs = self.person.grade_set.all()
        if self.center is None:
            qs = qs.filter(course__center__isnull=False)
        else:
            qs = qs.exclude(course__center=self.center)
        other = qs.aggregate(
            total=models.Sum('course__template__credits'))['total'] or 0
        return [credits, avg, self.person.gpa, other]

class SharedFile(models.Model):
    owner = models.ForeignKey(Person, on_delete=models.SET_NULL,
                              null=True, blank=True)
    title = models.CharField(max_length=100)
    url = models.URLField(max_length=300, blank=True, null=True)
    content = models.FileField(blank=True, null=True)
    objectives = models.ManyToManyField(LearningObjective, blank=True,
                                        related_name='files')
    templates = models.ManyToManyField(CourseTemplate, blank=True,
                                       related_name='files')
    courses = models.ManyToManyField(Course, blank=True,
                                     related_name='files')

    def __str__(self):
        return self.title

    @property
    def display_url(self):
        if self.content:
            return self.content.url
        else:
            return self.url

class CourseFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    shared_file = models.ForeignKey(SharedFile, on_delete=models.CASCADE)
    order = models.IntegerField(blank=True, null=True)

class StaffRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE,
                               blank=True, null=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current'), ('F', 'Former'),
                 ('A', 'Applied'), ('R', 'Rejected')],
        max_length=1, default='A')
    role = models.CharField(
        choices=[('I', 'Instructor'), ('A', 'Assistant Instructor'),
                 ('D', 'Director'), ('R', 'Registrar')],
        max_length=1, default='I')
    reference1_name = models.CharField(max_length=100, blank=True, null=True)
    reference1_email = models.EmailField(max_length=100, blank=True, null=True)
    reference1_phone = models.CharField(max_length=30, blank=True, null=True)
    reference2_name = models.CharField(max_length=100, blank=True, null=True)
    reference2_email = models.EmailField(max_length=100, blank=True, null=True)
    reference2_phone = models.CharField(max_length=30, blank=True, null=True)
    ordained = models.BooleanField(null=True)
    church = models.CharField(max_length=100, blank=True, null=True)
    denomination = models.CharField(max_length=100, blank=True, null=True)
    transcript_mode = models.CharField(max_length=1, choices=[
        ('E', 'I will request official or unofficial transcripts from all relevant theological/ministerial education and email them to advance@gs.edu'),
        ('A', 'As a Gateway student/alum, I authorize the use of my transcripts for this purpose.'),
        ('U', 'I will upload my transcript now.'),
        ('N', 'I am an assistant instructor/registrar and do not have relevant transcripts.')], default='N')
    upload_transcript = models.FileField(blank=True, null=True)
    accept_bfm = models.BooleanField(null=True)
    acceptance_date = models.DateField(blank=True, null=True,
                                       help_text='Date welcome letter was sent')
    center_approved = models.BooleanField(default=False)
    advance_approved = models.BooleanField(default=False)
    profile = models.JSONField(blank=True, null=True,
                               encoder=DjangoJSONEncoder)
    resume = models.FileField(blank=True, null=True)

    TIME_OF_DAY = [('M', 'Morning'), ('D', 'Midday'), ('A', 'Afternoon'),
                   ('E', 'Evening')]

    def __str__(self):
        return f'{self.person} {self.center}'

    @property
    def status_line(self):
        return self.get_status_display() + ' ' + self.get_role_display()

    def sort_key(self):
        return (self.center.name if self.center else '', self.role)

    def interested_courses(self):
        ls = (self.profile or {}).get('courses')
        if ls:
            return CourseTemplate.objects.filter(pk__in=ls, active=True).order_by('title')
        return []

    @property
    def get_time_of_day_display(self):
        ls = (self.profile or {}).get('time_of_day', [])
        return ', '.join([l for a, l in StaffRecord.TIME_OF_DAY if a in ls])

    @property
    def get_semester_display(self):
        return ', '.join((self.profile or {}).get('terms', []))

    def stats(self):
        courses = Course.objects.filter(instructors=self.person,
                                        status__in=['A', 'L'])
        course_count = courses.count()
        semester_count = len(set(courses.values_list('year', 'semester')))
        cps = 0
        if semester_count > 0:
            cps = round(course_count / semester_count)
        grades = Grade.objects.filter(course__in=courses)
        spc = round(grades.count() / max(course_count, 1))
        gpa = calc_gpa(grades)
        return [course_count, semester_count, cps,
                spc, gpa, not grades.filter(value='IP').exists()]

class AchievementRequirement(models.Model):
    courses = models.ManyToManyField(CourseTemplate)
    count = models.IntegerField(default=1)

    REQ_TEMPLATE = Template('''
    <li>
      {% if count == 1 %}
        {{courses.0}}
      {% else %}
        {{req.count}} of the following:
        <ul>
          {% for course in req.courses.all %}
          <li>
            <a href="{% url 'app:course_catalog' %}#c{{course.id}}">
              {{course}}
            </a>
          </li>
          {% endfor %}
        </ul>
      {% endif %}
    </li>
    ''')
    def display(self):
        crs = list(self.courses.all())
        return self.REQ_TEMPLATE.render(
            Context({'req': self, 'courses': crs, 'count': len(crs)}))

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    description = models.TextField()
    requirements = models.ManyToManyField(AchievementRequirement)
    prerequisites = models.ManyToManyField('self', blank=True,
                                           symmetrical=False)
    credits = models.IntegerField()
    category = models.CharField(
        choices=[('C', 'Certificate'), ('D', 'Diploma'),
                 ('L', 'Leadership Diploma')],
        max_length=1)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def check_requirements(self, student, completed_only):
        courses = []
        credits = 0
        exclude = ['F', 'Au', 'W']
        if completed_only:
            exclude.append('IP')
        for grade in student.grade_set.all().exclude(value=exclude):
            courses.append(grade.course.template)
            credits += grade.course.template.credits
        if credits < self.credits:
            return False
        for req in self.requirements.all():
            cls = [c for c in courses if c in req.courses.all()]
            if len(cls) < req.count:
                return False
        for req in self.prerequisites.all():
            if not AchievementAward.objects.filter(person=student, achievement=req, status__in=['A', 'P', 'D']).exists():
                return False
        return True

    @property
    def short_name(self):
        return self.name.replace('Leadership Diploma', '').replace('Diploma', '').replace('Certificate', '').strip()

class AchievementAward(models.Model, AutosaveFormMixin):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('S', 'Submitted'), ('A', 'Approved'), ('R', 'Rejected'),
                 ('P', 'Printed'), ('D', 'Received')],
        default='S', max_length=1)
    applied = models.DateField(blank=True, null=True)
    awarded = models.DateField(blank=True, null=True)
    display_name = models.CharField(max_length=100)
    walking = models.BooleanField(default=False)
    campus = models.CharField(
        choices=[('ONT', 'Ontario'), ('RMC', 'Rocky Mountain'),
                 ('BAC', 'Bay Area'), ('AZC', 'Arizona'),
                 ('PNWC', 'Pacific Northwest')],
        max_length=5, blank=True, null=True)
    year = models.IntegerField(default=2025, blank=False)
    semester = models.CharField(choices=SEMESTERS,
                                max_length=2, blank=False, null=True)
    shirt_size = models.CharField(
        choices=[('S', 'Small'), ('M', 'Medium'), ('L', 'Large'),
                 ('XL', 'X-Large'), ('XXL', 'XX-Large'),
                 ('XXXL', 'XXX-Large')],
        max_length=4, blank=True, null=True)

    forms = {'default': {'fields': ['display_name'],
                         'template': 'app/student_info_achievement.html'}}

    def save(self, *args, **kwargs):
        if not self.id:
            self.applied = datetime.date.today()
        return super().save(*args, **kwargs)

class PopupMessage(models.Model):
    # always implicitly send a copy to the sender
    # but with dismissed=True
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    sent = models.DateTimeField()
    text = models.TextField()
    sender = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL,
                               related_name='+')
    dismissed = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)

    def __str__(self):
        return f'From: {self.sender}, To: {self.person}, {self.text[:40]}'

class CenterBudget(models.Model, AutosaveFormMixin):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    year = models.IntegerField()
    other_income = models.DecimalField(max_digits=8, decimal_places=2,
                                     blank=True, null=True)
    marketing = models.DecimalField(max_digits=7, decimal_places=2,
                                     blank=True, null=True)
    office = models.DecimalField(max_digits=7, decimal_places=2,
                                     blank=True, null=True)
    books = models.DecimalField(max_digits=7, decimal_places=2,
                                     blank=True, null=True)
    other_expense = models.DecimalField(max_digits=7, decimal_places=2,
                                     blank=True, null=True)

    forms = {
        'income': {'fields': ['other_income'],
                   'widgets': {'other_income': {'placeholder': '$'}},
                   'template': 'app/center_budget_income.html'},
        'expenses': {'fields': ['marketing', 'office', 'books',
                                'other_expense'],
                     'widgets': {'marketing': {'placeholder': '$'},
                                 'office': {'placeholder': '$'},
                                 'books': {'placeholder': '$'},
                                 'other_expense': {'placeholder': '$'}},
                     'template': 'app/center_budget_expenses.html'},
    }

    @property
    def display_year(self):
        n = (self.year + 1) % 100
        return f'{self.year}-{n}'

    @classmethod
    def check_permissions(cls, request, instance, by_id):
        return (instance and
                request.user.is_authenticated and
                instance.center.is_admin(request.user.person))

class CenterFees(models.Model, AutosaveFormMixin):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    credit_fee = models.DecimalField(max_digits=5, decimal_places=2,
                                     blank=True, null=True)

    forms = {
        'default': {'fields': ['credit_fee'],
                    'widgets': {'credit_fee': {'placeholder': '$'}},
                    'template': 'app/center_budget_fee.html'},
        'new': {'fields': ['country'],
                'id_fields': {'budget': CenterBudget},
                'widgets': {'country': {'class': 'filter-select'}},
                'template': 'app/center_budget_fee.html'},
    }

    @classmethod
    def check_permissions(cls, request, instance, by_id):
        budget = by_id.get('budget') or instance.budget
        return (budget and request.user.is_authenticated and
                budget.center.is_admin(request.user.person))

class ExpectedCourse(models.Model, AutosaveFormMixin):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    course = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE)
    semester = models.CharField(choices=SEMESTERS, max_length=2, null=True)

    forms = {
        'new': {'fields': ['course', 'semester'],
                'id_fields': {'budget': CenterBudget},
                'widgets': {'course': {'class': 'filter-select'}},
                'template': 'app/center_budget_course.html'},
    }

    @classmethod
    def modify_form(cls, form):
        form.fields['course'].queryset = CourseTemplate.objects.filter(
            active=True).order_by('title')

    @classmethod
    def check_permissions(cls, request, instance, by_id):
        budget = by_id.get('budget') or instance.budget
        return (budget and request.user.is_authenticated and
                budget.center.is_admin(request.user.person))

    def iter_enrollments(self):
        yield from self.expectedenrollment_set.all().order_by(
            'country__name')

class ExpectedEnrollment(models.Model, AutosaveFormMixin):
    course = models.ForeignKey(ExpectedCourse, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    students = models.IntegerField(default=1)

    forms = {
        'default': {'fields': ['students'],
                    'widgets': {'students': {'style': 'width: 3.5em'}},
                    'template': 'app/center_budget_enrollment.html'},
        'new': {'fields': ['country'],
                'id_fields': {'course': ExpectedCourse},
                'widgets': {'country': {'class': 'filter-select'}},
                'template': 'app/center_budget_enrollment.html'},
    }

class CenterStipend(models.Model, AutosaveFormMixin):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffRecord, on_delete=models.CASCADE)
    stipend = models.DecimalField(max_digits=7, decimal_places=2,
                                  blank=True, null=True)

    forms = {
        'default': {'fields': ['stipend'],
                    'widgets': {'stipend': {'placeholder': '$'}},
                    'template': 'app/center_budget_stipend.html'},
    }

class ExpectedRoster(models.Model, AutosaveFormMixin):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    new_students = models.IntegerField(default=1)
    certificates = models.IntegerField(default=0)
    in_person = models.IntegerField(default=0)

    forms = {
        'default': {'fields': ['new_students'],
                    'template': 'app/center_budget_roster.html'},
        'new_students': {'fields': ['new_students'],
                         'template': 'app/center_budget_roster.html'},
        'certificates': {'fields': ['certificates'],
                         'template': 'app/center_budget_roster.html'},
        'in_person': {'fields': ['in_person'],
                      'template': 'app/center_budget_roster.html'},
        'new': {'fields': ['country'],
                'id_fields': {'budget': CenterBudget},
                'widgets': {'country': {'class': 'filter-select'}},
                'template': 'app/center_budget_roster.html'},
    }

class Prospect(models.Model):
    given_name = models.CharField(max_length=100, null=True,
                                  verbose_name='Given (First) Name')
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    family_name = models.CharField(max_length=100,
                                   verbose_name='Family (Last) Name')
    center = models.ForeignKey(Center, blank=True, null=True,
                               on_delete=models.SET_NULL)
    emails = models.ManyToManyField(EmailAddress)
    phones = models.ManyToManyField(PhoneAddress)
    mailings = models.ManyToManyField(MailingAddress)
    role = models.CharField(max_length=1, default='S', choices=[
        ('S', 'Student'), ('I', 'Instructor'), ('D', 'Director')])

    @property
    def last_contact(self):
        ret = self.prospectcontact_set.all().order_by('date').last()
        if ret:
            return ret.date

class ProspectContact(models.Model):
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE)
    date = models.DateField()
    method = models.CharField(max_length=1, choices=[
        ('E', 'Email'), ('P', 'Phone'), ('I', 'In-Person')])
    notes = models.TextField(blank=True, null=True)
