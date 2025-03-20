from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from app import models

@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Center)
class CenterAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Grade)
class GradeAdmin(admin.ModelAdmin):
    pass

class PersonInline(admin.StackedInline):
    model = models.Person
    can_delete = False

class UserAdmin(BaseUserAdmin):
    inlines = [PersonInline]
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
