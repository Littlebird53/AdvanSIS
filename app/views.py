from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from app import models
from app import forms
import itertools

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('app:dashboard')
    return render(request, 'app/index.html')

@login_required
def dashboard(request):
    message = None
    if request.method == 'POST':
        form = forms.ContactUpdateForm(request.POST,
                                       instance=request.user.person)
        if form.is_valid():
            message = 'Personal information updated successfully'
            form.save()
        else:
            message = 'There were errors. Please correct them below.'
    else:
        form = forms.ContactUpdateForm(instance=request.user.person)
    return render(request, 'app/dashboard.html',
                  {
                      'form': form,
                      'message': message,
                      'centers': models.Center.objects.filter(
                          director=request.user.person),
                      'teaching': models.Course.objects.filter(
                          instructor=request.user.person),
                      'enrolled': models.Grade.objects.filter(
                          person=request.user.person),
                  })

# TODO: this should probably be multiple views,
# since these conditions are not mutually exclusive
@login_required
def course(request, courseid):
    course = get_object_or_404(models.Course, pk=courseid)
    if request.user.person == course.instructor:
        pass # editable roster
    elif models.Grade.objects.filter(course=course, person=request.user.person).exists():
        grade = models.Grade.objects.filter(
            course=course, person=request.user.person).get()
        files = models.CourseFile.objects.filter(
            course=course).order_by('order')
        return render(request, 'app/course_enrolled.html',
                      {'course': course, 'grade': grade, 'files': files})
    elif request.user.person == course.center.director:
        pass # view roster + add student
    elif models.StudentRecord.objects.filter(center=course.center, person=request.user.person).exists():
        pass # student view non-entrolled course
    else:
        pass # permission error

@login_required
def list_centers(request):
    pass

####################
### CENTERS
####################

@login_required
def new_course(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    if request.user.person != center.director:
        pass # TODO: permission error
    if request.method == 'POST':
        form = forms.NewCourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.center = center
            course.save()
            return redirect('app:course', course.id)
    else:
        form = forms.NewCourseForm()
    return render(request, 'app/new_course.html', {'form': form})

@login_required
def view_instructors(request, centerid):
    pass # TODO

@login_required
def view_students(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    if request.user.person != center.director:
        pass # TODO: permission error
    # TODO: grouping
    return render(request, 'app/view_students.html',
                  {'students': itertools.groupby(
                      models.StudentRecord.objects.filter(
                          center=center).order_by('status'),
                      key=lambda x: x.status)})

####################
### Instructors
####################

@login_required
def instructor_apply(request, centerid):
    pass

####################
### Students
####################

@login_required
def student_apply(request, centerid):
    center = get_object_or_404(models.Center, pk=centerid)
    models.StudentRecord.objects.get_or_create(
        center=center, person=request.user.person)
    return redirect('app:dashboard')

@login_required
def course_search(request):
    centers = models.StudentRecord.objects.filter(
        person=request.user.person, status='C').values_list(
            'center', flat=True)
    return render(request, 'app/course_search.html',
                  {'courses': models.Course.objects.filter(
                      Q(center__in=centers) | Q(multi_center=True),
                      accepting_enrollments=True)})
