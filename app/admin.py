from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from nonrelated_inlines.admin import NonrelatedTabularInline
from app import models

class M2MInline(NonrelatedTabularInline):
    save_to = None
    extra = 0
    def get_set(self, obj):
        return getattr(obj, self.save_to)
    def get_form_queryset(self, obj):
        return self.get_set(obj).all()
    def save_new_instance(self, parent, instance):
        instance.save()
        self.get_set(parent).add(instance)

class CenterEmailAddressInline(M2MInline):
    model = models.EmailAddress
    save_to = 'emails'
class CenterPhoneAddressInline(M2MInline):
    model = models.PhoneAddress
    save_to = 'phones'
class CenterMailingAddressInline(M2MInline):
    model = models.MailingAddress
    save_to = 'mailings'
class CenterSponsorEmailAddressInline(M2MInline):
    model = models.EmailAddress
    save_to = 'sponsor_emails'
    verbose_name = 'Sponsor Email'
class CenterSponsorPhoneAddressInline(M2MInline):
    model = models.PhoneAddress
    save_to = 'sponsor_phones'
    verbose_name = 'Sponsor Phone'
class CenterSponsorMailingAddressInline(M2MInline):
    model = models.MailingAddress
    save_to = 'sponsor_mailings'
    verbose_name = 'Sponsor Mailing Address'

@admin.register(models.Center)
class CenterAdmin(admin.ModelAdmin):
    exclude = ['emails', 'phones', 'mailings',
               'sponsor_emails', 'sponsor_phones', 'sponsor_mailings']
    inlines = [CenterEmailAddressInline,
               CenterPhoneAddressInline,
               CenterMailingAddressInline,
               CenterSponsorEmailAddressInline,
               CenterSponsorPhoneAddressInline,
               CenterSponsorMailingAddressInline]
    search_fields = ['name']
    raw_id_fields = ['director']
    list_display = ['name', 'code', 'director', 'fte_eligible']
    list_filter = ['fte_eligible']

class CourseGradeAdmin(admin.TabularInline):
    model = models.Grade
    raw_id_fields = ['person']
class CourseFileAdmin(admin.TabularInline):
    model = models.CourseFile
@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [CourseGradeAdmin, CourseFileAdmin]
    raw_id_fields = ['center', 'instructor']
    search_fields = ['template__title', 'instructor__given_name',
                     'instructor__family_name', 'center__name']
    list_display = ['template__title', 'center', 'instructor',
                    'semester', 'year']
    list_filter = ['semester', 'template__division', 'delivery_format']

class DegreeRequirementInline(M2MInline):
    model = models.DegreeRequirement
    save_to = 'requirements'
@admin.register(models.Degree)
class DegreeAdmin(admin.ModelAdmin):
    exclude = ['requirements']
    inlines = [DegreeRequirementInline]
    list_display = ['name', 'abbreviation', 'credits', 'category']
    list_filter = ['credits', 'category']

@admin.register(models.SharedFile)
class FileAdmin(admin.ModelAdmin):
    pass

@admin.register(models.LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    pass

class LearningObjectiveInline(M2MInline):
    model = models.LearningObjective
    save_to = 'learning_objectives'
@admin.register(models.CourseTemplate)
class CourseTemplateAdmin(admin.ModelAdmin):
    exclude = ['learning_objectives']
    inlines = [LearningObjectiveInline]
    list_filter = ['division', 'credits']
    search_fields = ['title']
    list_display = ['title', 'code', 'credits']

@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    search_fields = ['given_name', 'family_name', 'user__username']
    raw_id_fields = ['user']
    exclude = ['emails', 'phones', 'mailings']

@admin.register(models.StudentRecord)
class StudentRecordAdmin(admin.ModelAdmin):
    pass

@admin.register(models.InstructorRecord)
class InstructorRecordAdmin(admin.ModelAdmin):
    pass

class PersonInline(admin.StackedInline):
    model = models.Person
    can_delete = False
    exclude = ['emails', 'phones', 'mailings']
class UserEmailAddressInline(M2MInline):
    model = models.EmailAddress
    def get_set(self, obj):
        return obj.person.emails
class UserPhoneAddressInline(M2MInline):
    model = models.PhoneAddress
    def get_set(self, obj):
        return obj.person.phones
class UserMailingAddressInline(M2MInline):
    model = models.MailingAddress
    def get_set(self, obj):
        return obj.person.mailings
class PersonGradeInline(NonrelatedTabularInline):
    model = models.Grade
    extra = 0
    raw_id_fields = ['course']
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.grade_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
class DegreeAwardInline(NonrelatedTabularInline):
    model = models.DegreeAward
    extra = 0
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.degreeaward_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
    readonly_fields = ['satisfy']

    def satisfy(self, instance):
        if instance.degree.check_requirements(instance.person, True):
            return 'Yes'
        elif instance.degree.check_requirements(instance.person, False):
            return 'Yes, with in-progress'
        else:
            return 'No'
class UserAdmin(BaseUserAdmin):
    inlines = [PersonInline, UserEmailAddressInline,
               UserPhoneAddressInline, UserMailingAddressInline,
               PersonGradeInline, DegreeAwardInline]
    list_display = ['username', 'person__given_name', 'person__family_name']
    search_fields = ['username', 'person__given_name',
                     'person__family_name']
    readonly_fields = ['credits_earned', 'credits_in_progress']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Grade Summary',
         {'fields': ['credits_earned', 'credits_in_progress']}),
    )
    def credits_earned(self, instance):
        return instance.person.credits_earned
    def credits_in_progress(self, instance):
        return instance.person.credits_in_progress
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
