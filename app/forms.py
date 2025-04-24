from django import forms
from app import models
from django.template import Context, Template
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
            staffrecord__center=self.center,
            staffrecord__status__in=['C', 'D', 'G'])
        self.fields['template'].queryset = models.CourseTemplate.objects.filter(active=True)
    class Meta:
        model = models.Course
        fields = ['template', 'year', 'semester', 'instructor',
                  'delivery_format', 'language', 'country',
                  'multi_center']

class DisplayPersonWidget(forms.widgets.Widget):
    DISPLAY_TEMPLATE = Template('''<span><a href="{% url 'app:student_info' value.id %}">{{value}}</a></span>''')
    def render(self, value, **kwargs):
        person = models.Person.objects.filter(pk=value).first()
        return self.DISPLAY_TEMPLATE.render(Context({'value': person}))

class GradeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].disabled = True
    class Meta:
        model = models.Grade
        fields = ['person', 'value']
        widgets = {'person': DisplayPersonWidget}
GradeFormset = forms.modelformset_factory(
    models.Grade, form=GradeForm, edit_only=True, extra=0)

class StudentSearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False)
    include = forms.BooleanField(required=False)

class StudentRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].disabled = True
    class Meta:
        model = models.StudentRecord
        fields = ['person', 'status']
        widgets = {'person': DisplayPersonWidget}
StudentRecordFormset = forms.modelformset_factory(
    models.StudentRecord, form=StudentRecordForm, extra=0, edit_only=True)

class StaffRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].disabled = True
    class Meta:
        model = models.StaffRecord
        fields = ['person', 'status']
StaffRecordFormset = forms.modelformset_factory(
    models.StaffRecord, form=StaffRecordForm,
    extra=0, edit_only=True)

class CertificateForm(forms.ModelForm):
    class Meta:
        model = models.DegreeAward
        fields = ['display_name']
class DiplomaForm(forms.ModelForm):
    def clean(self):
        super().clean()
        if self.cleaned_data.get('walking'):
            for key in ['campus', 'year', 'semester', 'shirt_size']:
                if not self.cleaned_data[key]:
                    self.add_error(key, _('This field is required if you are walking for graduation.'))
    class Meta:
        model = models.DegreeAward
        fields = ['display_name', 'walking', 'campus', 'year', 'semester',
                  'shirt_size']

class CourseFileForm(forms.ModelForm):
    def __init__(self, *args, files, course, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shared_file'].queryset = files
        self.course = course
    def save(self, *args, **kwargs):
        ret = super().save(commit=False)
        ret.course = self.course
        if kwargs.get('commit'):
            ret.save()
        return ret
    class Meta:
        model = models.CourseFile
        fields = ['shared_file', 'order']
CourseFileFormset = forms.modelformset_factory(
    models.CourseFile, form=CourseFileForm, extra=0, can_delete=True)

class AddFileForm(forms.ModelForm):
    class Meta:
        model = models.SharedFile
        fields = ['title', 'content']
