from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.template import Context, Template
from app.languages import LANGUAGES
import datetime
from functools import cached_property

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
        choices=[('MR', 'Mr.'), ('MS', 'Ms.'), ('MRS', 'Mrs.'),
                 ('MIS', 'Miss'),
                 ('DR', 'Dr.'), ('REV', 'Rev.'), ('PAS', 'Pastor'),
                 ('PRF', 'Prof.'), ('CHP', 'Chaplin'), ('MAJ', 'Major'),
                 ('BR', 'Br.'), ('MIN', 'Minister')],
        max_length=3, blank=True, null=True)
    joint_title = models.CharField(max_length=100, blank=True, null=True)
    suffix = models.CharField(max_length=100, blank=True, null=True,
                              choices=[('Jr.', 'Jr.'), ('Sr.', 'Sr.'),
                                       ('I', 'I'), ('II', 'II'),
                                       ('III', 'III'), ('IV', 'IV'),
                                       ('V', 'V')])
    preferred_name = models.CharField(max_length=100, null=True)
    date_of_birth = models.DateField(null=True)
    sex = models.CharField(choices=[('M', 'Male'), ('F', 'Female')],
                           max_length=1, null=True)
    marital_status = models.CharField(
        choices=[('S', 'Single'), ('M', 'Married'),
                 ('D', 'Divorced or Separated'), ('W', 'Widowed')],
        max_length=1, null=True)
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
        max_length=1, null=True)
    preferred_language = models.CharField(choices=LANGUAGES, max_length=3,
                                          blank=True, null=True)
    deceased = models.BooleanField(default=False)
    emails = models.ManyToManyField(EmailAddress)
    phones = models.ManyToManyField(PhoneAddress)
    mailings = models.ManyToManyField(MailingAddress)

    def __str__(self):
        return f'{self.given_name} {self.family_name} ({self.user.username})'

    @property
    def credits_earned(self):
        return self.grade_set.exclude(
            value__in=['F', 'Au', 'IP', 'W']).aggregate(
                v=models.Sum('course__template__credits'))['v'] or 0

    @property
    def credits_in_progress(self):
        return self.grade_set.filter(value='IP').aggregate(
            v=models.Sum('course__template__credits'))['v'] or 0

    @property
    def certificate_credits(self):
        return self.achievementaward_set.filter(
            status__in=['S', 'A'], achievement__category='C',
        ).aggregate(v=models.Sum('achievement__credits'))['v'] or 0

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
        sr = self.staffrecord_set.filter(status='C', role='D').first()
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
    instructor = models.ForeignKey(Person, on_delete=models.SET_NULL,
                                   null=True)
    associate_instructors = models.ManyToManyField(
        Person, related_name='associates')
    schedule = models.JSONField(null=True, encoder=DjangoJSONEncoder)
    delivery_format = models.CharField(
        choices=[('I', 'In-Person'), ('H', 'Hybrid'), ('O', 'Online')],
        max_length=1, null=True)
    language = models.CharField(max_length=50, null=True,
                                choices=LANGUAGES, default='eng')
    country = models.ForeignKey(Country, null=True,
                                on_delete=models.SET_NULL)
    accepting_enrollments = models.BooleanField(default=True)
    multi_center = models.BooleanField(default=False)
    section = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f'{self.template} {self.semester}{self.year}'

    def can_edit(self, person):
        return person == self.instructor or self.center.is_admin(person)

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

class Grade(models.Model):
    course = models.ForeignKey(Course, on_delete=models.SET_NULL,
                               null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL,
                               null=True)
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

class StudentRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current Student'), ('F', 'Former Student'),
                 ('A', 'Applied Student'), ('R', 'Rejected Student')],
        max_length=1, default='A')
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
    ed_level = models.CharField(max_length=3, choices=[
        ('N', 'No formal education'), ('J', 'Middle/Junior High School'),
        ('H', 'High School'), ('C', 'Some College'), ('A', 'Associates'),
        ('B', 'Bachelors'), ('M', 'Masters'),
        ('D', 'Doctoral/Professional Degree')],
                                blank=True, null=True)
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

class SharedFile(models.Model):
    owner = models.ForeignKey(Person, on_delete=models.SET_NULL,
                              null=True, blank=True)
    title = models.CharField(max_length=100)
    course = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE)
    content = models.FileField()

    def __str__(self):
        return self.title

class CourseFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    shared_file = models.ForeignKey(SharedFile, on_delete=models.CASCADE)
    order = models.IntegerField(blank=True, null=True)

class StaffRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current'), ('F', 'Former'),
                 ('A', 'Applied'), ('R', 'Rejected')],
        max_length=1, default='A')
    role = models.CharField(
        choices=[('I', 'Instructor'), ('A', 'Associate Instructor'),
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
    email_transcript = models.BooleanField(default=False)
    alum_transcript = models.BooleanField(default=False)
    upload_transcript = models.FileField(blank=True, null=True)
    no_transcript = models.BooleanField(default=False)
    accept_bfm = models.BooleanField(null=True)
    acceptance_date = models.DateField(blank=True, null=True,
                                       help_text='Date welcome letter was sent')
    center_approved = models.BooleanField(default=False)
    advance_approved = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.person} {self.center}'

    @property
    def status_line(self):
        return self.get_status_display() + ' ' + self.get_role_display()

    def sort_key(self):
        return (self.center.name, self.role)

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
        ok = set(['A', 'B', 'C', 'D'])
        if not completed_only:
            ok.add('IP')
        for grade in student.grade_set.all():
            if grade.value in ok:
                courses.append(grade.course.template)
                credits += grade.course.template.credits
        if credits < self.credits:
            return False
        for req in self.requirements.all():
            cls = [c for c in courses if c in req.courses.all()]
            if len(cls) < req.count:
                return False
        for req in self.prerequisites.all():
            if not AchievementAward.objects.filter(person=student, achievement=req).exists():
                return False
        return True

    @property
    def short_name(self):
        return self.name.replace('Leadership Diploma', '').replace('Diploma', '').replace('Certificate', '').strip()

class AchievementAward(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('S', 'Submitted'), ('A', 'Approved'), ('R', 'Rejected')],
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

    def save(self, *args, **kwargs):
        if not self.id:
            import datetime
            self.applied = datetime.date.today()
        return super().save(*args, **kwargs)

class PopupMessage(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    sent = models.DateTimeField()
    text = models.TextField()
    sender = models.ForeignKey(Person, null=True, on_delete=models.SET_NULL,
                               related_name='+')
    dismissed = models.BooleanField(default=False)

class CenterBudget(models.Model):
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

    @property
    def display_year(self):
        n = (self.year + 1) % 100
        return f'{self.year}-{n}'

    def as_income_form(self):
        from app.forms import CenterBudgetIncomeForm as fcls
        return fcls(instance=self)

    def as_expense_form(self):
        from app.forms import CenterBudgetExpenseForm as fcls
        return fcls(instance=self)

class CenterFees(models.Model):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    credit_fee = models.DecimalField(max_digits=5, decimal_places=2,
                                     blank=True, null=True)

    def as_form(self):
        from app.forms import CenterFeeForm as fcls
        return fcls(instance=self)

class ExpectedCourse(models.Model):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    course = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE)
    semester = models.CharField(choices=SEMESTERS, max_length=2, null=True)

    def iter_enrollments(self):
        yield from self.expectedenrollment_set.all().order_by(
            'country__name')

    def new_country_form(self, post=None):
        from app.forms import NewExpectedEnrollmentForm
        return NewExpectedEnrollmentForm(post,
                                         prefix=f'new_enrollment_{self.id}')

class ExpectedEnrollment(models.Model):
    course = models.ForeignKey(ExpectedCourse, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    students = models.IntegerField(default=1)

    def as_form(self):
        from app.forms import ExpectedEnrollmentForm as fcls
        return fcls(instance=self)

class CenterStipend(models.Model):
    budget = models.ForeignKey(CenterBudget, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffRecord, on_delete=models.CASCADE)
    stipend = models.DecimalField(max_digits=7, decimal_places=2,
                                  blank=True, null=True)

    def as_form(self):
        from app.forms import CenterStipendForm as fcls
        return fcls(instance=self)

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
