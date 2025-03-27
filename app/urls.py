from django.urls import path
from app import views

app_name = 'app'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('course/<int:courseid>/', views.course_details, name='course'),
    path('course/<int:courseid>/manage/', views.manage_course,
         name='manage_course'),
    path('course/<int:courseid>/add/', views.add_student_search,
         name='add_student'),
    path('course/<int:courseid>/add/<int:studentid>/', views.add_student,
         name='add_student_confirm'),
    path('center/<int:centerid>/add_course/', views.new_course,
         name='new_course'),

    # Rosters
    path('center/<int:centerid>/instructors/', views.view_instructors,
         {'status': None}, name='center_instructors'),
    path('center/<int:centerid>/instructors/applied/',
         views.view_instructors,
         {'status': 'A'}, name='center_instructors_applied'),
    path('center/<int:centerid>/instructors/current/',
         views.view_instructors,
         {'status': 'C'}, name='center_instructors_current'),
    path('center/<int:centerid>/instructors/former/',
         views.view_instructors,
         {'status': 'F'}, name='center_instructors_former'),
    path('center/<int:centerid>/instructors/rejected/',
         views.view_instructors,
         {'status': 'R'}, name='center_instructors_rejected'),
    path('center/<int:centerid>/students/', views.view_students,
         {'status': None}, name='center_students'),
    path('center/<int:centerid>/students/applied/', views.view_students,
         {'status': 'A'}, name='center_students_applied'),
    path('center/<int:centerid>/students/current/', views.view_students,
         {'status': 'C'}, name='center_students_current'),
    path('center/<int:centerid>/students/former/', views.view_students,
         {'status': 'F'}, name='center_students_former'),
    path('center/<int:centerid>/students/rejected/', views.view_students,
         {'status': 'R'}, name='center_students_rejected'),

    # Applications
    path('center/<int:centerid>/instructor_apply/', views.instructor_apply,
         name='instructor_apply'),
    path('center/<int:centerid>/apply/', views.student_apply,
         name='student_apply'),
    path('course/<int:courseid>/enroll', views.enroll, name='enroll'),
    path('degree/<int:degreeid>/', views.degree_apply, name='degree_apply'),

    # Catalogs
    path('course/', views.course_search, name='course_search'),
    path('course/catalog/', views.course_catalog, name='course_catalog'),
    path('center/', views.list_centers, name='center_search'),
    path('degree/', views.degree_search, name='degree_search'),
    path('degree/catalog/', views.degree_catalog, name='degree_catalog'),
]
