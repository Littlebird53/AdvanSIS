from django.db import models
from django.contrib.auth.models import User

class Address(models.Model):
    active = models.BooleanField(default=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    mailing = models.TextField(blank=True, null=True)

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    given_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    suffix = models.CharField(max_length=100)
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
    addresses = models.ManyToManyField(Address)

class Center(models.Model):
    name = models.CharField(max_length=400)
    code = models.CharField(max_length=5)
    director = models.ForeignKey(Person, on_delete=models.SET_NULL,
                                 null=True)
    addresses = models.ManyToManyField(Address, related_name='centers')
    fte_eligible = models.BooleanField(default=False)
    sponsor = models.CharField(max_length=100, null=True)
    sponsor_addresses = models.ManyToManyField(Address,
                                               related_name='sponsors')

class Course(models.Model):
    center = models.ForeignKey(Center, on_delete=models.SET_NULL,
                               null=True)
    title = models.CharField(max_length=100)
    division = models.CharField(max_length=1, null=True)
    number = models.IntegerField(null=True)
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

    @property
    def code(self):
        return f'CL{self.division}{self.number}'

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
