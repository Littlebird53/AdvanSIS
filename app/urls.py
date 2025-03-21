from django.urls import path
from app import views

app_name = 'app'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('course/<int:courseid>/', views.course_details, name='course'),
    path('course/<int:courseid>/manage', views.course_details,
         name='manage_course'),
    path('course/<int:courseid>/enroll', views.enroll, name='enroll'),
    path('center/<int:centerid>/add_course/', views.new_course,
         name='new_course'),
    path('center/<int:centerid>/instructors/', views.view_instructors,
         name='center_instructors'),
    path('center/<int:centerid>/students/', views.view_students,
         name='center_students'),
    path('center/<int:centerid>/instructor_apply/', views.instructor_apply,
         name='instructor_apply'),
    path('center/<int:centerid>/apply/', views.student_apply,
         name='student_apply'),
    path('course/search/', views.course_search, name='course_search'),
    path('center/', views.list_centers, name='center_search'),
]
