from django.db import models
from django.contrib.auth.models import User
from django.template import Context, Template

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

class MailingAddress(models.Model):
    active = models.BooleanField(default=True)
    address = models.TextField()
    attention = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=10, blank=True, null=True)
    zip_code = models.CharField(max_length=10, null=True)
    country = models.CharField(max_length=10, default='US')
    category = models.CharField(
        choices=[('H', 'Home'), ('W', 'Work'), ('S', 'Shipping'),
                 ('O', 'Other')],
        max_length=1, null=True)

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    given_name = models.CharField(max_length=100, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    family_name = models.CharField(max_length=100)
    title = models.CharField(
        choices=[('MR', 'Mr.'), ('MS', 'Ms.'), ('MRS', 'Mrs.'),
                 ('MIS', 'Miss'),
                 ('DR', 'Dr.'), ('REV', 'Rev.'), ('PAS', 'Pastor'),
                 ('PRF', 'Prof.'), ('CHP', 'Chaplin'), ('MAJ', 'Major'),
                 ('BR', 'Br.'), ('MIN', 'Minister')],
        max_length=3, blank=True, null=True)
    joint_title = models.CharField(max_length=100, blank=True, null=True)
    suffix = models.CharField(max_length=100, blank=True, null=True)
    preferred_name = models.CharField(max_length=100, null=True)
    date_of_birth = models.DateField(null=True)
    sex = models.CharField(choices=[('M', 'Male'), ('F', 'Female')],
                           max_length=1, null=True)
    marital_status = models.CharField(
        choices=[('S', 'Single'), ('M', 'Married'),
                 ('D', 'Divorced or Separated'), ('W', 'Widowed')],
        max_length=1, null=True)
    denomination = models.CharField(
        choices=[('B', 'Baptist'), ('L', 'Lutheran'), ('M', 'Methodist'),
                 ('N', 'Nondenominational'), ('P', 'Pentecostal'),
                 ('T', 'Presbyterian'), ('R', 'Reformed'),
                 ('O', 'Other Denomination'), ('U', 'Unknown')],
        max_length=1, default='U')
    ethnicity = models.CharField(
        choices=[('0', 'Unknown'), ('1', 'African'),
                 ('2', 'Native American'),
                 ('3', 'Asian or Pacific Islander'), ('4', 'Hispanic'),
                 ('5', 'Caucasian'), ('6', 'Other')],
        max_length=1, null=True)
    deceased = models.BooleanField(default=False)
    emails = models.ManyToManyField(EmailAddress)
    phones = models.ManyToManyField(PhoneAddress)
    mailings = models.ManyToManyField(MailingAddress)

    def __str__(self):
        return f'{self.given_name} {self.family_name} ({self.user.username})'

    @property
    def credits_earned(self):
        return self.grade_set.filter(
            value__in=['A', 'B', 'C', 'D']).aggregate(
                v=models.Sum('course__template__credits'))['v'] or 0

    @property
    def credits_in_progress(self):
        return self.grade_set.filter(value='IP').aggregate(
            v=models.Sum('course__template__credits'))['v'] or 0

    @property
    def certificate_credits(self):
        return self.degreeaward_set.filter(
            status__in=['S', 'A'], degree__category='C',
        ).aggregate(v=models.Sum('degree__credits'))['v'] or 0

class Center(models.Model):
    name = models.CharField(max_length=400)
    code = models.CharField(max_length=5)
    emails = models.ManyToManyField(EmailAddress, related_name='+')
    phones = models.ManyToManyField(PhoneAddress, related_name='+')
    mailings = models.ManyToManyField(MailingAddress, related_name='+')
    fte_eligible = models.BooleanField(default=False)
    sponsor = models.CharField(max_length=100, null=True)
    sponsor_emails = models.ManyToManyField(EmailAddress, related_name='+')
    sponsor_phones = models.ManyToManyField(PhoneAddress, related_name='+')
    sponsor_mailings = models.ManyToManyField(MailingAddress,
                                              related_name='+')
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def is_admin(self, person):
        return self.staffrecord_set.filter(
            person=person, status__in=['D', 'G']).exists()

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

class Course(models.Model):
    template = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE)
    center = models.ForeignKey(Center, on_delete=models.SET_NULL,
                               null=True)
    year = models.IntegerField(default=2025)
    semester = models.CharField(
        choices=[('Sp', 'Spring'), ('Su', 'Summer'), ('Fa', 'Fall'),
                 ('Wi', 'Winter')],
        max_length=2, null=True)
    instructor = models.ForeignKey(Person, on_delete=models.SET_NULL,
                                   null=True)
    associate_instructors = models.ManyToManyField(
        Person, related_name='associates')
    schedule = models.JSONField(null=True)
    delivery_format = models.CharField(
        choices=[('I', 'In-Person'), ('H', 'Hybrid'), ('O', 'Online')],
        max_length=1, null=True)
    language = models.CharField(max_length=50, null=True)
    country = models.CharField(max_length=50, null=True)
    accepting_enrollments = models.BooleanField(default=True)
    multi_center = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.template} {self.semester}{self.year}'

    def can_edit(self, person):
        return person == self.instructor or self.center.is_admin(person)

class Grade(models.Model):
    course = models.ForeignKey(Course, on_delete=models.SET_NULL,
                               null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL,
                               null=True)
    value = models.CharField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('F', 'F'),
                 ('Au', 'Audit'), ('IP', 'In-Progress'), ('W', 'Withdrawn'),
                 ],
        max_length=2, default='IP')

    def __str__(self):
        return f'{self.person} {self.course}'

class StudentRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current'), ('F', 'Former'), ('A', 'Applied'),
                 ('R', 'Rejected')],
        max_length=1, default='A')

    def __str__(self):
        return f'{self.person} {self.center}'

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
        choices=[('CI', 'Current'), ('FI', 'Former'), ('AI', 'Applied'),
                 ('RI', 'Rejected'), ('CA', 'Current Associate'),
                 ('FA', 'Former Associate'),
                 ('D', 'Director'), ('R', 'Registrar')],
        max_length=2, default='AI')

    def __str__(self):
        return f'{self.person} {self.center}'

class DegreeRequirement(models.Model):
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
          <li>{{course}}</li>
          {% endfor %}
        </ul>
      {% endif %}
    </li>
    ''')
    def display(self):
        crs = list(self.courses.all())
        return self.REQ_TEMPLATE.render(
            Context({'req': self, 'courses': crs, 'count': len(crs)}))

class Degree(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    description = models.TextField()
    requirements = models.ManyToManyField(DegreeRequirement)
    prerequisites = models.ManyToManyField('self', blank=True,
                                           symmetrical=False)
    credits = models.IntegerField()
    category = models.CharField(
        choices=[('C', 'Certificate'), ('D', 'Diploma'),
                 ('L', 'Leadership Diploma')],
        max_length=1)

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
            if not DegreeAward.objects.filter(person=student, degree=req).exists():
                return False
        return True

class DegreeAward(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
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
    year = models.IntegerField(default=2025)
    semester = models.CharField(
        choices=[('Sp', 'Spring'), ('Su', 'Summer'), ('Fa', 'Fall'),
                 ('Wi', 'Winter')],
        max_length=2, blank=True, null=True)
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
