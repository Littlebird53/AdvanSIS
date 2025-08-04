from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.template import Context, Template
from nonrelated_inlines.admin import NonrelatedStackedInline, NonrelatedTabularInline
from app import models
import collections
import datetime

class M2MMixin:
    save_to = None
    extra = 0
    def get_set(self, obj):
        return getattr(obj, self.save_to)
    def get_form_queryset(self, obj):
        return self.get_set(obj).all()
    def save_new_instance(self, parent, instance):
        instance.save()
        self.get_set(parent).add(instance)

class CenterEmailAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.EmailAddress
    save_to = 'emails'
class CenterPhoneAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.PhoneAddress
    save_to = 'phones'
class CenterMailingAddressInline(M2MMixin, NonrelatedStackedInline):
    model = models.MailingAddress
    save_to = 'mailings'
class CenterSponsorEmailAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.EmailAddress
    save_to = 'sponsor_emails'
    verbose_name = 'Sponsor Email'
class CenterSponsorPhoneAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.PhoneAddress
    save_to = 'sponsor_phones'
    verbose_name = 'Sponsor Phone'
class CenterSponsorMailingAddressInline(M2MMixin, NonrelatedStackedInline):
    model = models.MailingAddress
    save_to = 'sponsor_mailings'
    verbose_name = 'Sponsor Mailing Address'
class CenterStudentRecords(admin.TabularInline):
    model = models.StudentRecord
    autocomplete_fields = ['person']
    fields = ['person', 'status']
    extra = 0
class CenterStaffRecords(admin.TabularInline):
    model = models.StaffRecord
    autocomplete_fields = ['person']
    fields = ['person', 'status']
    extra = 0
class CenterMOUInline(admin.TabularInline):
    model = models.MOU
    extra = 0
    readonly_fields = ['start_date', 'expiration']
@admin.register(models.Center)
class CenterAdmin(admin.ModelAdmin):
    exclude = ['emails', 'phones', 'mailings',
               'sponsor_emails', 'sponsor_phones', 'sponsor_mailings']
    inlines = [CenterEmailAddressInline,
               CenterPhoneAddressInline,
               CenterMailingAddressInline,
               CenterSponsorEmailAddressInline,
               CenterSponsorPhoneAddressInline,
               CenterSponsorMailingAddressInline,
               CenterStudentRecords, CenterStaffRecords, CenterMOUInline]
    search_fields = ['name', 'code']
    list_display = ['name', 'code', 'fte_eligible', 'active', 'approved']
    list_filter = ['fte_eligible', 'active', 'approved']

class CourseGradeAdmin(admin.TabularInline):
    model = models.Grade
    autocomplete_fields = ['person']
class CourseFileAdmin(admin.TabularInline):
    model = models.CourseFile
    extra = 0
    autocomplete_fields = ['course', 'shared_file']
@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [CourseGradeAdmin, CourseFileAdmin]
    autocomplete_fields = ['template', 'center', 'instructor',
                           'assistant_instructors']
    search_fields = ['template__title', 'instructor__given_name',
                     'instructor__family_name', 'center__name']
    list_display = ['template__title', 'center', 'instructor',
                    'semester', 'year', 'status']
    list_filter = ['semester', 'template__division', 'delivery_format',
                   'status']

class AchievementRequirementInline(M2MMixin, NonrelatedTabularInline):
    model = models.AchievementRequirement
    autocomplete_fields = ['courses']
    save_to = 'requirements'
@admin.register(models.Achievement)
class AchievementAdmin(admin.ModelAdmin):
    exclude = ['requirements']
    inlines = [AchievementRequirementInline]
    list_display = ['name', 'abbreviation', 'credits', 'category']
    list_filter = ['credits', 'category']
    search_fields = ['name']

@admin.register(models.SharedFile)
class FileAdmin(admin.ModelAdmin):
    list_display = ['title', 'course__title']
    search_fields = ['title', 'course__title']
    autocomplete_fields = ['owner', 'course']
    inlines = [CourseFileAdmin]

class CourseTemplateInline(admin.TabularInline):
    model = models.CourseTemplate.learning_objectives.through
    verbose_name_plural = 'Courses with this objective'
@admin.register(models.LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    inlines = [CourseTemplateInline]
    search_fields = ['name']

class LearningObjectiveInline(M2MMixin, NonrelatedTabularInline):
    model = models.LearningObjective
    save_to = 'learning_objectives'
@admin.register(models.CourseTemplate)
class CourseTemplateAdmin(admin.ModelAdmin):
    exclude = ['learning_objectives']
    inlines = [LearningObjectiveInline]
    list_filter = ['division', 'credits', 'active']
    search_fields = ['title']
    list_display = ['title', 'code', 'credits']

@admin.register(models.MOU)
class MOUAdmin(admin.ModelAdmin):
    list_display = ['center', 'status', 'start_date', 'expiration']
    readonly_fields = ['start_date', 'expiration']
    list_filter = ['status']
    search_fields = ['center__name']

@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    search_fields = ['given_name', 'family_name', 'user__username']
    readonly_fields = ['user']
    exclude = ['emails', 'phones', 'mailings']
    verbose_name_plural = 'People (use Users table instead)'

class PersonInline(admin.StackedInline):
    model = models.Person
    can_delete = False
    exclude = ['emails', 'phones', 'mailings']
class UserEmailAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.EmailAddress
    def get_set(self, obj):
        return obj.person.emails
class UserPhoneAddressInline(M2MMixin, NonrelatedTabularInline):
    model = models.PhoneAddress
    def get_set(self, obj):
        return obj.person.phones
class UserMailingAddressInline(M2MMixin, NonrelatedStackedInline):
    model = models.MailingAddress
    def get_set(self, obj):
        return obj.person.mailings
class StudentRecordInline(NonrelatedTabularInline):
    model = models.StudentRecord
    extra = 0
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.studentrecord_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
class StaffRecordInline(NonrelatedTabularInline):
    model = models.StaffRecord
    extra = 0
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.staffrecord_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
class PersonGradeInline(NonrelatedTabularInline):
    model = models.Grade
    extra = 0
    autocomplete_fields = ['course']
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.grade_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
class AchievementAwardInline(NonrelatedTabularInline):
    model = models.AchievementAward
    extra = 0
    exclude = ['person']
    def get_form_queryset(self, obj):
        return obj.person.achievementaward_set.all()
    def save_new_instance(self, parent, instance):
        instance.person = parent.person
        instance.save()
    readonly_fields = ['satisfy']

    def satisfy(self, instance):
        if instance.achievement.check_requirements(instance.person, True):
            return 'Yes'
        elif instance.achievement.check_requirements(instance.person, False):
            return 'Yes, with in-progress'
        else:
            return 'No'
class UserAdmin(BaseUserAdmin):
    inlines = [PersonInline, UserEmailAddressInline,
               UserPhoneAddressInline, UserMailingAddressInline,
               StudentRecordInline, StaffRecordInline,
               PersonGradeInline, AchievementAwardInline]
    list_display = ['username', 'person__given_name', 'person__family_name']
    list_select_related = ['person']
    search_fields = ['username', 'person__given_name',
                     'person__family_name']
    readonly_fields = ['credits_earned', 'credits_in_progress']
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'classes': ['collapse']}),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ['collapse']}),
        ('Grade Summary', {'fields': ('credits_earned', 'credits_in_progress')}),
    )
    actions = ['compare_users', 'merge_users']

    def credits_earned(self, instance):
        return instance.person.credits_earned
    def credits_in_progress(self, instance):
        return instance.person.credits_in_progress

    @admin.action(description='Compare selected accounts')
    def compare_users(self, request, queryset, is_merge=False):
        values = collections.defaultdict(set)
        names = {}
        for user in queryset:
            person = user.person
            for field in person._meta.get_fields():
                if 'Many' in field.__class__.__name__:
                    continue
                if field.name in ['id', 'user']:
                    continue
                disp = f'get_{field.name}_display'
                if hasattr(person, disp):
                    val = getattr(person, disp)()
                else:
                    val = getattr(person, field.name)
                names[field.name] = field.verbose_name
                if val is not None:
                    values[field.name].add(val)
        diff = []
        for key in values:
            if len(values[key]) > 1:
                diff.append(names[key] + ': ' + ' vs '.join(sorted(values[key])))
        if diff:
            self.message_user(request, Template('Users differ in the following fields:<br/><ul>{% for d in diff %}<li>{{d}}</li>{% endfor %}</ul>').render(Context({'diff': diff})))
        elif not is_merge:
            self.message_user(request, 'User profiles are compatible.')
    @admin.action(description='Merge selected accounts')
    def merge_users(self, request, queryset):
        if queryset.count() < 2:
            return
        self.compare_users(request, queryset, True)
        ls = list(queryset)
        ls.sort(key=lambda u: u.id)
        main = ls[0].person
        old = list(models.Person.objects.filter(user__in=queryset).exclude(
            pk=main.pk))
        emails = set(a.email for a in main.emails.all())
        phones = set(a.phone for a in main.phones.all())
        def mailcomp(a):
            return (a.address, a.attention, a.city, a.state,
                    a.zip_code, a.country_id)
        mailings = set(mailcomp(a) for a in main.mailings.all())
        models.Course.objects.filter(instructor__in=old).update(
            instructor=main)
        for course in models.Course.objects.filter(
                assistant_instructors__in=old):
            course.assistant_instructors.remove(old)
            course.assistant_instructors.add(main)
        models.Grade.objects.filter(person__in=old).update(person=main)
        models.StudentRecord.objects.filter(person__in=old).update(
            person=main)
        models.StaffRecord.objects.filter(person__in=old).update(
            person=main)
        models.SharedFile.objects.filter(owner__in=old).update(
            owner=main)
        models.AchievementAward.objects.filter(person__in=old).update(
            person=main)
        models.PopupMessage.objects.filter(person__in=old).update(
            person=main)
        models.PopupMessage.objects.filter(sender__in=old).update(
            sender=main)
        for other in ls[1:]:
            other.active = False
            other.save()
            person = other.person
            for field in person._meta.get_fields():
                if 'Many' in field.__class__.__name__:
                    continue
                if field.name in ['id', 'user']:
                    continue
                if getattr(main, field.name) is not None:
                    setattr(main, field.name, getattr(person, field.name))
            for addr in person.emails.all():
                if addr.email not in emails:
                    emails.add(addr.email)
                    main.emails.add(addr)
            person.emails.clear()
            for addr in person.phones.all():
                if addr.phone not in phones:
                    phones.add(addr.phone)
                    main.phones.add(addr)
            person.phones.clear()
            for addr in person.mailings.all():
                comp = mailcomp(addr)
                if comp not in mailings:
                    mailings.add(comp)
                    main.mailings.add(addr)
            person.mailings.clear()
        main.save()
        self.message_user(request, f'Merged {queryset.count()} accounts.')
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(models.PopupMessage)
class PopupAdmin(admin.ModelAdmin):
    autocomplete_fields = ['person', 'sender']
    search_fields = ['person__given_name', 'person__family_name',
                     'sender__given_name', 'sender__family_name']

class ProspectDateFilter(admin.SimpleListFilter):
    # https://hakibenita.com/how-to-add-a-text-filter-to-django-admin
    template = 'admin/date_filter.html'
    parameter_name = 'last_contact'
    title = 'Last Contact Before'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice

    def queryset(self, request, queryset):
        if self.value() is not None:
            try:
                limit = datetime.date.fromisoformat(self.value())
                return queryset.exclude(
                    prospectcontact__date__gte=limit)
            except:
                pass
        return queryset

class ProspectContactInline(admin.TabularInline):
    model = models.ProspectContact
    extra = 0
@admin.register(models.Prospect)
class ProspectAdmin(admin.ModelAdmin):
    autocomplete_fields = ['center']
    search_fields = ['given_name', 'middle_name', 'family_name']
    list_display = ['given_name', 'middle_name', 'family_name', 'role',
                    'last_contact']
    list_filter = ['role', ProspectDateFilter]
    exclude = ['emails', 'phones', 'mailings']
    inlines = [CenterEmailAddressInline, CenterPhoneAddressInline,
               CenterMailingAddressInline, ProspectContactInline]

@admin.register(models.StaffRecord)
class StaffAdmin(admin.ModelAdmin):
    readonly_fields = ['center', 'person', 'acceptance_date']
    list_filter = ['status', 'role', 'center_approved', 'advance_approved']
    list_display = ['person', 'center', 'role', 'status']
    search_fields = ['person__given_name', 'person__family_name',
                     'center__name']

@admin.register(models.StudentRecord)
class StudentAdmin(admin.ModelAdmin):
    readonly_fields = ['center', 'person', 'acceptance_date']
    list_filter = ['status']
    list_display = ['person', 'center', 'status']
    search_fields = ['person__given_name', 'person__family_name',
                     'center__name']

class AwardYearFilter(admin.SimpleListFilter):
    # https://hakibenita.com/how-to-add-a-text-filter-to-django-admin
    template = 'admin/int_filter.html'
    parameter_name = 'year'
    title = 'Year'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice

    def queryset(self, request, queryset):
        if isinstance(self.value(), str) and self.value().isdigit():
            return queryset.filter(year=int(self.value()))
        return queryset

@admin.register(models.AchievementAward)
class AchievementAwardAdmin(admin.ModelAdmin):
    list_filter = ['status', 'campus', 'walking',
                   AwardYearFilter, 'semester']
    list_display = ['person', 'status', 'campus', 'walking', 'year', 'semester']
    readonly_fields = ['person']
    search_fields = ['person__given_name', 'person__family_name']
