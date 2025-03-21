from django.db import models
from django.contrib.auth.models import User

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
        choices=[('H', 'Home'), ('M', 'Mobile'), ('W', 'Work')],
        max_length=1, null=True)

class MailingAddress(models.Model):
    active = models.BooleanField(default=True)
    mailing = models.TextField()
    category = models.CharField(
        choices=[('H', 'Home'), ('W', 'Work'), ('S', 'Shipping')],
        max_length=1, null=True)

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    given_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    family_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)
    suffix = models.CharField(max_length=100, blank=True, null=True)
    preferred_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True)
    sex = models.CharField(choices=[('M', 'Male'), ('F', 'Female')],
                           max_length=1, null=True)
    marital_status = models.CharField(
        choices=[('S', 'Single'), ('M', 'Married'), ('D', 'Divorced'),
                 ('W', 'Widowed')],
        max_length=1, null=True)
    denomination = models.CharField(max_length=50, null=True)
    deceased = models.BooleanField(default=False)
    emails = models.ManyToManyField(EmailAddress)
    phones = models.ManyToManyField(PhoneAddress)
    mailings = models.ManyToManyField(MailingAddress)

    def __str__(self):
        return f'{self.given_name} {self.family_name} ({self.user.username})'

class Center(models.Model):
    name = models.CharField(max_length=400)
    code = models.CharField(max_length=5)
    director = models.ForeignKey(Person, on_delete=models.SET_NULL,
                                 null=True)
    emails = models.ManyToManyField(EmailAddress, related_name='+')
    phones = models.ManyToManyField(PhoneAddress, related_name='+')
    mailings = models.ManyToManyField(MailingAddress, related_name='+')
    fte_eligible = models.BooleanField(default=False)
    sponsor = models.CharField(max_length=100, null=True)
    sponsor_emails = models.ManyToManyField(EmailAddress, related_name='+')
    sponsor_phones = models.ManyToManyField(PhoneAddress, related_name='+')
    sponsor_mailings = models.ManyToManyField(MailingAddress,
                                              related_name='+')

    def __str__(self):
        return self.name

class LearningObjective(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

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
    schedule = models.JSONField(null=True)
    delivery_format = models.CharField(
        choices=[('I', 'In-Person'), ('H', 'Hybrid'), ('O', 'Online')],
        max_length=1, null=True)
    language = models.CharField(max_length=50, null=True)
    country = models.CharField(max_length=50, null=True)
    accepting_enrollments = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.template} {self.semester}{self.year}'

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

class StudentRecord(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        choices=[('C', 'Current'), ('F', 'Former'), ('A', 'Applied'),
                 ('R', 'Rejected')],
        max_length=1, default='A')

class SharedFile(models.Model):
    owner = models.ForeignKey(Person, on_delete=models.SET_NULL,
                              null=True, blank=True)
    title = models.CharField(max_length=100)
    content = models.FileField()

    def __str__(self):
        return self.title

class CourseFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    shared_file = models.ForeignKey(SharedFile, on_delete=models.CASCADE,
                                    null=True, blank=True)
    order = models.IntegerField(blank=True, null=True)
