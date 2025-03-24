from django import forms
from app import models
from django.utils.translation import gettext_lazy as _

class DateWidget(forms.DateInput):
    input_type = 'date'

class ContactUpdateForm(forms.ModelForm):
    class Meta:
        model = models.Person
        fields = ['given_name', 'middle_name', 'family_name',
                  'title', 'suffix', 'preferred_name', 'date_of_birth',
                  'sex', 'marital_status', 'denomination']
        widgets = {'date_of_birth': DateWidget}

class NewCourseForm(forms.ModelForm):
    def __init__(self, center, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center = center
        self.fields['instructor'].queryset = models.Person.objects.filter(
            instructorrecord__center=self.center,
            instructorrecord__status='C')
    class Meta:
        model = models.Course
        fields = ['template', 'year', 'semester', 'instructor',
                  'delivery_format', 'language', 'country',
                  'multi_center']

class GradeForm(forms.ModelForm):
    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].queryset = models.Person.objects.filter(
            studentrecord__center=course.center,
            studentrecord__status='C')
        if self.instance and self.instance.pk:
            self.fields['person'].disabled = True
        self.course = course
    def save(self, *args, commit=True, **kwargs):
        ret = super().save(*args, **kwargs, commit=False)
        if ret.pk is None:
            ret.course = self.course
        if commit:
            ret.save()
        return ret
    def clean_person(self):
        person = self.cleaned_data['person']
        if self.instance and self.instance.pk:
            return person
        elif models.Grade.objects.filter(person=person, course=self.course).exists():
            raise forms.ValidationError(
                _('This student is already enrolled.'),
                code='duplicate-student')
        else:
            return person
    class Meta:
        model = models.Grade
        fields = ['person', 'value']
class GradeFormset(forms.BaseModelFormSet):
    model = models.Grade
    form = GradeForm
    renderer = None
    min_num = 0
    max_num = 100
    absolute_max = 1000
    validate_min = True
    validate_max = True
    extra = 0
    can_order = False
    can_delete = False
    def __init__(self, course, *args, **kwargs):
        kwargs['queryset'] = models.Grade.objects.filter(
            course=course).order_by('person__family_name',
                                    'person__given_name')
        super().__init__(*args, **kwargs)
        self.course = course
        self.form_kwargs['course'] = self.course

class StudentRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].disabled = True
    class Meta:
        model = models.StudentRecord
        fields = ['person', 'status']
StudentRecordFormset = forms.modelformset_factory(
    models.StudentRecord, form=StudentRecordForm, extra=0, edit_only=True)

class InstructorRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].disabled = True
    class Meta:
        model = models.InstructorRecord
        fields = ['person', 'status']
InstructorRecordFormset = forms.modelformset_factory(
    models.InstructorRecord, form=InstructorRecordForm,
    extra=0, edit_only=True)
