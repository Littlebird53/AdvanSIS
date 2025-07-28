from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _
from app import models
import datetime
from functools import cache
import zoneinfo

class DateWidget(forms.DateInput):
    input_type = 'date'
class TimeWidget(forms.TimeInput):
    input_type = 'time'

class RequiredMixin:
    make_required = []
    make_filtered = []
    widget_attrs = {}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.make_required:
            self.fields[field].required = True
        for field in self.make_filtered:
            self.fields[field].widget.attrs['class'] = 'filter-select'
        for field, attrs in self.widget_attrs.items():
            self.fields[field].widget.attrs.update(attrs)

class NewUserForm(RequiredMixin, forms.ModelForm):
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    make_filtered = ['languages_spoken']
    make_required = ['ed_level']

    def clean_confirm_password(self):
        p1 = self.cleaned_data.get('password')
        p2 = self.cleaned_data.get('confirm_password')
        if p1 != p2:
            raise forms.ValidationError(_('The passwords do not match.'),
                                        code='password-mismatch')
        return p2

    class Meta:
        model = models.Person
        fields = ['given_name', 'middle_name', 'family_name',
                  'title', 'suffix', 'preferred_name', 'date_of_birth',
                  'sex', 'marital_status', 'denomination', 'ed_level',
                  'languages_spoken']
        widgets = {'date_of_birth': DateWidget}

class ContactUpdateForm(RequiredMixin, forms.ModelForm):
    make_filtered = ['languages_spoken']
    make_required = ['ed_level']
    class Meta:
        model = models.Person
        fields = ['given_name', 'middle_name', 'family_name',
                  'title', 'suffix', 'preferred_name', 'date_of_birth',
                  'sex', 'marital_status', 'denomination', 'ed_level',
                  'languages_spoken']
        widgets = {'date_of_birth': DateWidget}

class NewEmailForm(RequiredMixin, forms.ModelForm):
    prefix = 'email'
    make_default = forms.BooleanField(required=False, label='Set as account email (e.g. for password resets)')

    widget_attrs = {'email': {'style': 'width: 20em'}}
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
    prefix = 'phone'
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
    prefix='mailing'
    def __init__(self, person, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
        self.fields['address'].widget.attrs['rows'] = '3'
        self.fields['country'].widget.attrs['class'] = 'filter-select'
    def clean_category(self):
        cat = self.cleaned_data['category']
        if self.person.mailings.all().filter(active=True, category=cat).exists():
            raise forms.ValidationError(_('You already have an address of that type.'), code='reuse-type')
        return cat
    class Meta:
        model = models.MailingAddress
        fields = ['address', 'attention', 'city', 'country', 'state',
                  'zip_code', 'category']

class NewCourseForm(RequiredMixin, forms.ModelForm):
    make_filtered = ['template', 'language', 'country']

    def __init__(self, center, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center = center
        self.fields['instructor'].queryset = models.Person.objects.filter(
            staffrecord__center=self.center,
            staffrecord__status='C', staffrecord__role__in=['I', 'D'])
        self.fields['template'].queryset = models.CourseTemplate.objects.filter(active=True).order_by('title')
        self.fields['country'].initial = center.country
    class Meta:
        model = models.Course
        fields = ['template', 'year', 'semester', 'instructor',
                  'delivery_format', 'language', 'country',
                  'multi_center']

class GradeForm(forms.ModelForm):
    class Meta:
        model = models.Grade
        fields = ['value']

class StudentSearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False)
    courses = forms.ModelMultipleChoiceField(
        queryset=models.CourseTemplate.objects.filter(
            active=True).order_by('title'),
        required=False, label='Is taking or has taken')
    courses.widget.attrs.update({'class': 'filter-select',
                                 'style': 'width: 100%'})

class StudentRecordForm(forms.ModelForm):
    class Meta:
        model = models.StudentRecord
        fields = ['status']
StudentRecordFormset = forms.modelformset_factory(
    models.StudentRecord, form=StudentRecordForm, extra=0, edit_only=True)

class StaffRecordForm(forms.ModelForm):
    class Meta:
        model = models.StaffRecord
        fields = ['status', 'role']
StaffRecordFormset = forms.modelformset_factory(
    models.StaffRecord, form=StaffRecordForm,
    extra=0, edit_only=True)
class StaffRecordFilterForm(forms.Form):
    any_option = [(None, 'All')]
    status = forms.ChoiceField(
        choices=any_option+models.StaffRecord.status.field.choices,
        required=False)
    role = forms.ChoiceField(
        choices=any_option+models.StaffRecord.role.field.choices,
        required=False)
    def make_queryset(self, center):
        qs = models.StaffRecord.objects.filter(center=center)
        status = self.data.get('status')
        if status:
            qs = qs.filter(status=status)
        role = self.data.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

class CertificateForm(forms.ModelForm):
    class Meta:
        model = models.AchievementAward
        fields = ['display_name', 'year', 'semester']
class DiplomaForm(forms.ModelForm):
    def clean(self):
        super().clean()
        if self.cleaned_data.get('walking'):
            for key in ['campus', 'shirt_size']:
                if not self.cleaned_data[key]:
                    self.add_error(key, _('This field is required if you are walking for graduation.'))
    class Meta:
        model = models.AchievementAward
        fields = ['display_name', 'year', 'semester', 'walking', 'campus',
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

class NewInstructorPopupForm(forms.Form):
    text = forms.CharField(label='Message Body', widget=forms.Textarea)

class NewPopupForm(RequiredMixin, forms.Form):
    roles = forms.MultipleChoiceField(initial='S', choices=[
        ('S', 'Students'), ('I', 'Instructors'), ('D', 'Staff')])
    status = forms.MultipleChoiceField(initial='C', choices=[
        ('C', 'Current'), ('F', 'Former'), ('A', 'Applied')])
    text = forms.CharField(label='Message Body', widget=forms.Textarea)

    make_filtered = ['roles', 'status']
    widget_attrs = {
        'roles': {'style': 'width: 85%'},
        'status': {'style': 'width: 80%'},
    }

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

class StudentApplicationForm(RequiredMixin, forms.ModelForm):
    church_sbc = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    prev_gateway = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    called_to_ministry = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    christian_year = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    conduct_standard = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    membership_number = forms.IntegerField()
    membership_unit = forms.ChoiceField(
        choices=[('Months', 'Months'), ('Years', 'Years')])

    make_required = ['church', 'church_rec_name', 'church_rec_email',
                     'reference1_name', 'reference1_email',
                     'reference1_phone', 'reference2_name',
                     'reference2_email', 'reference2_phone']
    class Meta:
        model = models.StudentRecord
        fields = ['church', 'church_sbc',
                  'reference1_name', 'reference1_email', 'reference1_phone',
                  'reference2_name', 'reference2_email', 'reference2_phone',
                  'church_rec_name', 'church_rec_email',
                  'prev_gateway', 'gateway_id', 'called_to_ministry',
                  'christian_year', 'conduct_standard']

class ChurchEndorsementForm(forms.ModelForm):
    good_character = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    good_character_expl = forms.CharField(label='If not, please explain.',
                                          widget=forms.Textarea,
                                          required=False)
    good_standing = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    good_standing_expl = forms.CharField(label='If not, please explain.',
                                         widget=forms.Textarea,
                                         required=False)
    endorsement = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    endorsement_expl = forms.CharField(label='If not, please explain.',
                                       widget=forms.Textarea,
                                       required=False)
    class Meta:
        model = models.StudentRecord
        fields = ['good_character', 'good_standing', 'endorsement']

class StaffApplicationForm(RequiredMixin, forms.ModelForm):
    ordained = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    accept_bfm = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)

    make_required = ['church', 'denomination']

    def clean_upload_transcript(self):
        val = self.cleaned_data.get('upload_transcript')
        if val is None and self.data.get('transcript_mode') == 'U':
            raise forms.ValidationError(_('Please upload your transcript.'),
                                        code='no-transcript')
        return val

    def clean_transcript_mode(self):
        val = self.cleaned_data.get('transcript_mode')
        if val == 'N' and self.data.get('role') in ['I', 'D']:
            raise forms.ValidationError(_('Transcripts are required for instructors and directors.'), code='instructor-no-transcript')
        return val

    class Meta:
        model = models.StaffRecord
        fields = ['role', 'church', 'denomination', 'accept_bfm',
                  'reference1_name', 'reference1_email', 'reference1_phone',
                  'reference2_name', 'reference2_email', 'reference2_phone',
                  'transcript_mode', 'upload_transcript']
        widgets = {'transcript_mode': forms.RadioSelect}

class InstructorAtLargeApplicationForm(RequiredMixin, forms.ModelForm):
    ordained = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)
    accept_bfm = forms.TypedChoiceField(
        choices=[(False, 'No'), (True, 'Yes')],
        widget=forms.RadioSelect)

    make_required = ['church', 'denomination']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcript_mode'].choices = [c for c in self.fields['transcript_mode'].choices if c[0] != 'N']

    def clean_upload_transcript(self):
        val = self.cleaned_data.get('upload_transcript')
        if val is None and self.data.get('transcript_mode') == 'U':
            raise forms.ValidationError(_('Please upload your transcript.'),
                                        code='no-transcript')
        return val

    class Meta:
        model = models.StaffRecord
        fields = ['church', 'denomination', 'accept_bfm',
                  'reference1_name', 'reference1_email', 'reference1_phone',
                  'reference2_name', 'reference2_email', 'reference2_phone',
                  'transcript_mode', 'upload_transcript']
        widgets = {'transcript_mode': forms.RadioSelect}

class NewCenterApplicationForm(forms.ModelForm):
    sponsor_email = forms.EmailField()
    sponsor_phone = forms.CharField(max_length=30)
    director_sig = forms.BooleanField()
    sponsor_sig = forms.BooleanField()
    class Meta:
        model = models.Center
        fields = ['name', 'sponsor', 'sponsor_rep', 'sponsor_rep_title',
                  'coi_file']

class CenterBudgetExpenseForm(RequiredMixin, forms.ModelForm):
    widget_attrs = {'marketing': {'placeholder': '$'},
                    'office': {'placeholder': '$'},
                    'books': {'placeholder': '$'},
                    'other_expense': {'placeholder': '$'}}
    class Meta:
        model = models.CenterBudget
        fields = ['marketing', 'office', 'books', 'other_expense']

class CenterBudgetIncomeForm(RequiredMixin, forms.ModelForm):
    widget_attrs = {'other_income': {'placeholder': '$'}}
    class Meta:
        model = models.CenterBudget
        fields = ['other_income']

class CenterStipendForm(RequiredMixin, forms.ModelForm):
    widget_attrs = {'stipend': {'placeholder': '$'}}
    class Meta:
        model = models.CenterStipend
        fields = ['stipend']

class CenterFeeForm(RequiredMixin, forms.ModelForm):
    widget_attrs = {'credit_fee': {'placeholder': '$'}}
    class Meta:
        model = models.CenterFees
        fields = ['credit_fee']

class NewCenterFeeForm(RequiredMixin, forms.ModelForm):
    make_filtered = ['country']
    class Meta:
        model = models.CenterFees
        fields = ['country']

class NewExpectedCourseForm(RequiredMixin, forms.ModelForm):
    make_filtered = ['course']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = models.CourseTemplate.objects.filter(active=True).order_by('title')
    class Meta:
        model = models.ExpectedCourse
        fields = ['course', 'semester']

class ExpectedEnrollmentForm(RequiredMixin, forms.ModelForm):
    widget_attrs = {'students': {'style': 'width: 3.5em'}}
    class Meta:
        model = models.ExpectedEnrollment
        fields = ['students']

class NewExpectedEnrollmentForm(RequiredMixin, forms.ModelForm):
    make_filtered = ['country']
    class Meta:
        model = models.ExpectedEnrollment
        fields = ['country']

class StaffStatsForm(RequiredMixin, forms.Form):
    any_choice = [('', 'Any')]
    start_year = forms.IntegerField()
    start_semester = forms.ChoiceField(choices=models.SEMESTERS)
    end_year = forms.IntegerField()
    end_semester = forms.ChoiceField(choices=models.SEMESTERS)
    language = forms.ModelChoiceField(queryset=models.Language.objects.all(),
                                      required=False)
    country = forms.ModelChoiceField(queryset=models.Country.objects.all(),
                                     required=False)
    delivery_format = forms.ChoiceField(choices=any_choice+models.Course.delivery_format.field.choices, required=False)
    sex = forms.ChoiceField(choices=any_choice+models.Person.sex.field.choices, required=False)
    ethnicity = forms.ChoiceField(choices=any_choice+models.Person.ethnicity.field.choices, required=False)
    marital_status = forms.ChoiceField(choices=any_choice+models.Person.marital_status.field.choices, required=False)
    denomination = forms.ChoiceField(choices=any_choice+models.Person.denomination.field.choices, required=False)
    center = forms.ModelMultipleChoiceField(queryset=models.Center.objects.all(), required=False)
    sbc_fundable = forms.NullBooleanField()

    make_filtered = ['language', 'country', 'center']

class LockCoursesForm(RequiredMixin, forms.Form):
    centers = forms.ModelMultipleChoiceField(queryset=models.Center.objects.all())
    year = forms.IntegerField()
    semester = forms.ChoiceField(choices=models.SEMESTERS)
    prior = forms.BooleanField(required=False, label='Include prior terms?')

    make_filtered = ['centers']

@cache
def timezone_values():
    now = datetime.datetime.now()
    ret = [('', '---')]
    for name in zoneinfo.available_timezones():
        offset = now.astimezone(zoneinfo.ZoneInfo(name)).strftime('%z')
        ret.append((name, f'{name} (UTC{offset})'))
    return sorted(ret)

class InstructorAtLargeProfileForm(RequiredMixin, forms.Form):
    courses = forms.TypedMultipleChoiceField(choices=[], coerce=int)
    terms = forms.MultipleChoiceField(choices=[])
    time_of_day = forms.MultipleChoiceField(
        choices=models.StaffRecord.TIME_OF_DAY)
    timezone = forms.ChoiceField(choices=timezone_values)
    preferred_contact_method = forms.ChoiceField(choices=[
        ('phone', 'phone'), ('email', 'email')])
    bio = forms.CharField(max_length=2000, widget=forms.Textarea)

    make_filtered = ['courses', 'terms', 'time_of_day', 'timezone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['courses'].choices = models.CourseTemplate.objects.filter(active=True).values_list('id', 'title')
        import datetime
        cur_year = datetime.date.today().year
        self.fields['terms'].choices = [
            (f'{abbr}-{y}', f'{name} {y}')
            for y in range(cur_year, cur_year+5)
            for abbr, name in models.SEMESTERS
        ]
