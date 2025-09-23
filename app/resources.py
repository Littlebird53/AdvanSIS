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

class ChoicesResource(ModelResource):
    @classmethod
    def widget_from_django_field(cls, f, default=Widget):
        if f.choices:
            return partial(ChoicesWidget, f.choices)
        if callable(getattr(f, "get_internal_type", None)):
            if f.get_internal_type() == 'BooleanField':
                return partial(ChoicesWidget, [(True, 'Y'), (False, 'N')])
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

    def init_instance(self, row=None):
        import uuid
        ret = self._meta.model()
        ret.user = models.User(username=uuid.uuid1())
        return ret

    def before_save_instance(self, instance, row, **kwargs):
        instance.user.save()

    def after_save_instance(self, instance, row, **kwargs):
        instanve.user.set_password(instance.user.username)
        instance.user.username = str(instance.id)
        instance.user.save()

    class Meta:
        model = models.Person
        fields = [
            'id', 'user', 'user__username',
            'given_name', 'middle_name', 'family_name', 'title',
            'joint_title', 'suffix', 'preferred_name', 'date_of_birth',
            'sex', 'marital_status', 'denomination', 'ethnicity',
            'languages_spoken', 'ed_level', 'deceased',
            # account/personal/work/other email
            # phones
            # mailings
            # has staff/student record
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
    class Meta:
        model = models.AchievementAward
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name',
                  # TODO: primary center
                  'achievement', 'achievement__name',
                  'achievement__abbreviation', 'status', 'year',
                  'walking', 'campus',
                  # TODO: home state
                  'display_name', 'applied', 'awarded', 'gpa',
                  'shirt_size', 'languages',
                  # TODO: contact info
                ]

class AchievementResource(ChoicesResource):
    recipient_count = Field(attribute='recipient_count', readonly=True)
    last_awarded = Field(attribute='last_awarded', readonly=True)
    class Meta:
        model = models.Achievement
        fields = ['id', 'name', 'abbreviation', 'credits', 'category',
                  'active', 'recipient_count', 'last_awarded',
                  'description']

# TODO: AchievementRequirement

class CenterResource(ChoicesResource):
    class Meta:
        model = models.Center
        fields = ['id', 'name', 'code', 'sponsor', 'sponsor_rep',
                  'sponsor_rep_title',
                  # address
                  'approved', 'active', 'fte_eligible',
                  # TODO: total & current students & staff
                  # TODO: total hours & courses
                  # TODO: MOU expiration
                  ]

class CountryResource(ChoicesResource):
    class Meta:
        model = models.Country
        fields = ['id', 'name', 'postal_code', 'credit_fee', 'student_fee']

# TODO: fees

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

# TODO: learning objectives

class StudentResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    class Meta:
        model = models.StudentRecord
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'center_code', 'center__name',
                  'status', 'church_sbc', 'church_membership',
                  'prev_gateway', 'gateway_id', 'pastor_date',
                  'acceptance_date',
                  # courses
                  # credits
                  ]

class StaffResource(ChoicesResource):
    center_code = Field(attribute='center',
                        widget=ForeignKeyWidget(models.Center, 'code'))
    class Meta:
        model = models.StaffRecord
        fields = ['id', 'person', 'person__given_name',
                  'person__family_name', 'center_code', 'center__name',
                  'status', 'role', 'acceptance_date',
                  # courses_taught
                  # students_taught
                  # registrations
                  # avg enrollment
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
    class Meta:
        model = models.Prospect
        fields = ['id', 'given_name', 'middle_name', 'family_name',
                  # status
                  'center_code',
                  # last contact
                  ]

class FileResource(ChoicesResource):
    owner_name = Field(attribute='owner__full_name', readonly=True)
    class Meta:
        model = models.SharedFile
        fields = ['id', 'title', 'owner', 'owner_name',
                  'objectives', 'templates', 'courses']
