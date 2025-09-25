from import_export.fields import Field
from import_export.resources import ModelResource
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, Widget
from app import models
from functools import partial

# https://stackoverflow.com/questions/39674976/django-import-export-choices-field
class ChoicesWidget(Widget):
    """
    Widget that uses choice display values in place of database values
    """
    def __init__(self, choices, *args, **kwargs):
        """
        Creates a self.choices dict with a key, display value, and value,
        db value, e.g. {'Chocolate': 'CHOC'}
        """
        self.choices = dict(choices)
        self.revert_choices = dict((v, k) for k, v in self.choices.items())

    def clean(self, value, row=None, *args, **kwargs):
        """Returns the db value given the display value"""
        return self.revert_choices.get(value, value) if value else None

    def render(self, value, obj=None, **kwargs):
        """Returns the display value given the db value"""
        return self.choices.get(value, value)

BOOL_CHOICES = [(True, 'Y'), (False, 'N')]
class ChoicesResource(ModelResource):
    @classmethod
    def widget_from_django_field(cls, f, default=Widget):
        if f.choices:
            return partial(ChoicesWidget, f.choices)
        if callable(getattr(f, "get_internal_type", None)):
            if f.get_internal_type() == 'BooleanField':
                return partial(ChoicesWidget, BOOL_CHOICES)
        return super(ChoicesResource, cls).widget_from_django_field(
            f, default)

class PersonResource(ChoicesResource):
    credits_earned = Field(attribute='credits_earned', readonly=True)
    credits_in_progress = Field(attribute='credits_in_progress',
                                readonly=True)
    gpa = Field(attribute='gpa', readonly=True)
    languages_spoken = Field(attribute='languages_spoken',
                             widget=ManyToManyWidget(models.Language,
                                                     field='name'))
    account_email = Field(attribute='user__email')
    personal_email = Field(attribute='personal_email')
    work_email = Field(attribute='work_email')
    other_email = Field(attribute='other_email')
    home_phone = Field(attribute='home_phone')
    mobile_phone = Field(attribute='mobile_phone')
    work_phone = Field(attribute='work_phone')
    other_phone = Field(attribute='other_phone')
    category = Field(attribute='best_mailing_category',
                     widget=ChoicesWidget(
                         models.MailingAddress.category.field.choices))
    address = Field(attribute='best_mailing_address')
    attention = Field(attribute='best_mailing_attention')
    city = Field(attribute='best_mailing_city')
    state = Field(attribute='best_mailing_state')
    country = Field(attribute='best_mailing_country',
                    widget=ForeignKeyWidget(models.Country, 'name'))
    zip_code = Field(attribute='best_mailing_zip_code')
    is_staff = Field(attribute='is_staff', readonly=True,
                     widget=ChoicesWidget(BOOL_CHOICES))
    is_student = Field(attribute='is_student', readonly=True,
                       widget=ChoicesWidget(BOOL_CHOICES))

    def after_init_instance(self, instance, new, row, **kwargs):
        if new:
            import uuid
            instance.user = models.User(username=str(uuid.uuid1()))

    def before_save_instance(self, instance, row, **kwargs):
        instance.user.save()

    def after_save_instance(self, instance, row, **kwargs):
        if not kwargs['dry_run'] and not instance.user.username.isdigit():
            instance.user.set_password(instance.user.username)
            instance.user.username = str(instance.user.id)
            instance.user.save()

    class Meta:
        model = models.Person
        fields = [
            'id', 'user', 'user__username',
            'given_name', 'middle_name', 'family_name', 'title',
            'joint_title', 'suffix', 'preferred_name', 'date_of_birth',
            'sex', 'marital_status', 'denomination', 'ethnicity',
            'languages_spoken', 'ed_level', 'deceased',
            'account_email', 'personal_email', 'work_email',
            'other_email',
            'home_phone', 'mobile_phone', 'work_phone', 'other_phone',
            'category', 'address', 'attention', 'city', 'state',
            'country', 'zip_code',
            'is_staff', 'is_student',
            'credits_earned', 'credits_in_progress', 'gpa',
            'user__date_joined', 'user__last_login',
            'user__is_staff', 'user__is_superuser',
        ]

class GradeResource(ChoicesResource):
    course_code = Field(attribute='course__template__code', readonly=True)
    class Meta:
        model = models.Grade
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'course',
                  'course__template__title',
                  'course_code',
                  'course__template__credits',
                  'value', 'course__year', 'course__semester',
                  'course__center__code',
                  'course__instructors',
                  ]

class AwardResource(ChoicesResource):
    gpa = Field(attribute='person__gpa', readonly=True)
    languages = Field(attribute='person__languages_spoken',
                      widget=ManyToManyWidget(models.Language,
                                              field='name'),
                      readonly=True)
    primary_center = Field(attribute='person__primary_center',
                           readonly=True)
    phone = Field(attribute='person__best_phone__phone', readonly=True)
    email = Field(attribute='person__best_email__email', readonly=True)
    attn = Field(attribute='person__best_mailing__attention', readonly=True)
    address = Field(attribute='person__best_mailing__address',
                    readonly=True)
    city = Field(attribute='person__best_mailing__city', readonly=True)
    state = Field(attribute='person__best_mailing__state', readonly=True)
    zip_code = Field(attribute='person__best_mailing__zip_code',
                     readonly=True)
    country = Field(attribute='person__best_mailing__country__name',
                    readonly=True)
    class Meta:
        model = models.AchievementAward
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'primary_center',
                  'achievement', 'achievement__name',
                  'achievement__abbreviation', 'status', 'year',
                  'walking', 'campus', 'home_state',
                  'display_name', 'applied', 'awarded', 'gpa',
                  'shirt_size', 'languages',
                  'phone', 'email',
                  'attn', 'address', 'city', 'state', 'zip_code', 'country',
                ]

class AchievementResource(ChoicesResource):
    recipient_count = Field(attribute='recipient_count', readonly=True)
    last_awarded = Field(attribute='last_awarded', readonly=True)
    class Meta:
        model = models.Achievement
        fields = ['id', 'name', 'abbreviation', 'credits', 'category',
                  'active', 'recipient_count', 'last_awarded',
                  'description']

class RequirementResource(ChoicesResource):
    course_codes = Field(attribute='courses', readonly=True,
                         widget=ManyToManyWidget(models.CourseTemplate,
                                                 field='code'))
    achievements = Field(attribute='achievement_set', readonly=True,
                         widget=ManyToManyWidget(models.Achievement,
                                                field='name'))
    class Meta:
        model = models.AchievementRequirement
        fields = ['id', 'courses', 'course_codes', 'count', 'achievements']

class CenterResource(ChoicesResource):
    mou_expiration = Field(attribute='current_mou__expiration',
                           readonly=True)
    city = Field(attribute='best_mailing__city', readonly=True)
    zip_code = Field(attribute='best_mailing__zip_code', readonly=True)
    country = Field(attribute='best_mailing__country__name',
                    readonly=True)
    all_students = Field(attribute='all_students', readonly=True)
    current_students = Field(attribute='current_students', readonly=True)
    all_staff = Field(attribute='all_staff', readonly=True)
    current_staff = Field(attribute='current_staff', readonly=True)
    total_hours = Field(attribute='total_hours', readonly=True)
    total_courses = Field(attribute='total_courses', readonly=True)
    class Meta:
        model = models.Center
        fields = ['id', 'name', 'code', 'sponsor', 'sponsor_rep',
                  'sponsor_rep_title',
                  'city', 'zip_code', 'country',
                  'approved', 'active', 'fte_eligible',
                  'all_students', 'current_students',
                  'all_staff', 'current_staff',
                  'total_hours', 'total_courses',
                  'mou_expiration',
                  ]

class CountryResource(ChoicesResource):
    class Meta:
        model = models.Country
        fields = ['id', 'name', 'postal_code', 'credit_fee', 'student_fee']

class BudgetResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    class Meta:
        model = models.CenterBudget
        fields = ['id', 'center_code', 'year', 'other_income',
                  'marketing', 'office', 'books', 'other_expenses']

class FeeResource(ChoicesResource):
    center_code = Field(attribute='budget__center__code', readonly=True)
    year = Field(attribute='budget__display_year', readonly=True)
    country = Field(attribute='country',
                    widget=ForeignKeyWidget(models.Country, 'name'))
    class Meta:
        model = models.CenterFees
        fields = ['id', 'budget', 'center_code', 'year', 'country',
                  'credit_fee']

class CourseResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    enrollment = Field(attribute='enrollment', readonly=True)
    title = Field(attribute='template__display_title', readonly=True)
    code = Field(attribute='template__code', readonly=True)
    languages = Field(attribute='languages',
                      widget=ManyToManyWidget(models.Language,
                                              field='name'))
    country = Field(attribute='country',
                    widget=ForeignKeyWidget(models.Country, 'name'))
    class Meta:
        model = models.Course
        fields = ['id', 'template', 'code', 'title',
                  'template__credits', 'center_code', 'center__name',
                  'year', 'semester', 'instructors', 'delivery_format',
                  'languages', 'country', 'accepting_enrollments',
                  'multi_center', 'section', 'status', 'enrollment']

class TemplateResource(ChoicesResource):
    total_instances = Field(attribute='total_instances', readonly=True)
    total_enrollment = Field(attribute='total_enrollment', readonly=True)
    class Meta:
        model = models.CourseTemplate
        fields = ['id', 'title', 'short_title', 'credits',
                  'division', 'number', 'active', 'total_instances',
                  'total_enrollment', 'thinkific_id', 'description']

class ObjectiveResource(ChoicesResource):
    course_codes = Field(attribute='coursetemplate_set', readonly=True,
                         widget=ManyToManyWidget(models.CourseTemplate,
                                                 field='code'))
    class Meta:
        model = models.LearningObjective
        fields = ['id', 'name', 'description', 'course_codes']


class StudentResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    courses = Field(attribute='total_courses', readonly=True)
    credits = Field(attribute='total_credits', readonly=True)
    class Meta:
        model = models.StudentRecord
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'center_code', 'center__name',
                  'status', 'church_sbc', 'church_membership',
                  'prev_gateway', 'gateway_id', 'pastor_date',
                  'acceptance_date', 'courses', 'credits',
                  ]

class StaffResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    courses_taught = Field(attribute='courses_taught', readonly=True)
    students_taught = Field(attribute='students_taught', readonly=True)
    registrations = Field(attribute='registrations', readonly=True)
    average_enrollment = Field(attribute='average_enrollment',
                               readonly=True)
    class Meta:
        model = models.StaffRecord
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'center_code', 'center__name',
                  'status', 'role', 'acceptance_date',
                  'courses_taught', 'students_taught',
                  'registrations', 'average_enrollment',
                  ]
        widgets = {
            'center': {'field': 'code'},
        }

class MessageResource(ChoicesResource):
    sender_name = Field(attribute='sender__full_name', readonly=True)
    recipient_name = Field(attribute='person__full_name', readonly=True)
    class Meta:
        model = models.PopupMessage
        fields = ['id', 'sender', 'sender_name', 'person',
                  'recipient_name', 'sent', 'dismissed', 'emailed', 'text']

class ProspectResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    contact_date = Field(attribute='last_contact_record__date',
                         readonly=True)
    method = Field(attribute='last_contact_record__get_method_display',
                   readonly=True)
    notes = Field(attribute='last_contact_record__notes', readonly=True)
    class Meta:
        model = models.Prospect
        fields = ['id', 'given_name', 'middle_name', 'family_name',
                  'status', 'center_code',
                  'contact_date', 'method', 'notes',
                  ]

class FileResource(ChoicesResource):
    owner_name = Field(attribute='owner__full_name', readonly=True)
    class Meta:
        model = models.SharedFile
        fields = ['id', 'title', 'owner', 'owner_name',
                  'objectives', 'templates', 'courses']
