from django import forms
from app import models
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import widgets as admin_widgets

class DateWidget(forms.DateInput):
    input_type = 'date'
class TimeWidget(forms.TimeInput):
    input_type = 'time'

class ContactUpdateForm(forms.ModelForm):
    class Meta:
        model = models.Person
        fields = ['given_name', 'middle_name', 'family_name',
                  'title', 'suffix', 'preferred_name', 'date_of_birth',
                  'sex', 'marital_status', 'denomination']
        widgets = {'date_of_birth': DateWidget}

class NewEmailForm(forms.ModelForm):
    def __init__(self, person, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
    def clean_category(self):
        cat = self.cleaned_data['category']
        if self.person.emails.all().filter(active=True, category=cat).exists():
            raise forms.ValidationError(_('You already have an email address of that type.'), code='reuse-type')
        return cat
    class Meta:
        model = models.EmailAddress
        fields = ['email', 'category']

class NewPhoneForm(forms.ModelForm):
    def __init__(self, person, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
    def clean_category(self):
        cat = self.cleaned_data['category']
        if self.person.phones.all().filter(active=True, category=cat).exists():
            raise forms.ValidationError(_('You already have a phone number of that type.'), code='reuse-type')
        return cat
    class Meta:
        model = models.PhoneAddress
        fields = ['phone', 'category']

class NewMailingForm(forms.ModelForm):
    def __init__(self, person, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
    def clean_category(self):
        cat = self.cleaned_data['category']
        if self.person.mailings.all().filter(active=True, category=cat).exists():
            raise forms.ValidationError(_('You already have an address of that type.'), code='reuse-type')
        return cat
    class Meta:
        model = models.MailingAddress
        fields = ['address', 'attention', 'city', 'state', 'zip_code',
                  'country', 'category']

class NewCourseForm(forms.ModelForm):
    def __init__(self, center, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center = center
        self.fields['instructor'].queryset = models.Person.objects.filter(
            staffrecord__center=self.center,
            staffrecord__status__in=['C', 'D', 'G'])
        self.fields['template'].queryset = models.CourseTemplate.objects.filter(active=True).order_by('title')
        self.fields['template'].widget.attrs['class'] = 'filter-select'
        self.fields['language'].widget.attrs['class'] = 'filter-select'
        self.fields['country'].widget.attrs['class'] = 'filter-select'
        self.fields['country'].initial = center.country
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
    include = forms.BooleanField(
        required=False, label='Include students from other centers')

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

class NewPopupForm(forms.Form):
    text = forms.CharField(label='Message Body', widget=forms.Textarea)

class CalendarForm(forms.Form):
    days = forms.MultipleChoiceField(
        label='Days of the Week',
        choices=[('Sunday', 'Sunday'), ('Monday', 'Monday'),
                 ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
                 ('Thursday', 'Thursday'), ('Friday', 'Friday'),
                 ('Saturday', 'Saturday')])
    time = forms.TimeField(widget=TimeWidget)
    end_time = forms.TimeField(widget=TimeWidget, required=False)
    start = forms.DateField(label='First Meeting', widget=DateWidget)
    end = forms.DateField(label='Last Meeting', widget=DateWidget)
    location = forms.CharField(label='Location')

class TallySheetForm(forms.Form):
    semester = forms.ChoiceField(choices=models.SEMESTERS)
    year = forms.IntegerField()
