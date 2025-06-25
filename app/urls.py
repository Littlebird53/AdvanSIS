from django.urls import path
from app import views

app_name = 'app'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create_account/', views.CreateAccountView.as_view(), name='create_account'),
    path('course/<int:courseid>/', views.course_details, name='course'),
    path('course/<int:courseid>/manage/', views.manage_course,
         name='manage_course'),
    path('course/<int:courseid>/add/', views.add_student_search,
         name='add_student'),
    path('course/<int:courseid>/add/query/', views.add_student_query,
         name='add_student_query'),
    path('course/<int:courseid>/add/list/', views.add_student_list,
         name='add_student_list'),
    path('course/<int:courseid>/add/<int:studentid>/', views.add_student,
         name='add_student_confirm'),
    path('course/<int:courseid>/schedule/', views.edit_schedule,
         name='edit_schedule'),
    path('center/<int:centerid>/add_course/', views.new_course,
         name='new_course'),
    path('person/<int:studentid>/', views.student_info, name='student_info'),

    # Rosters
    path('center/<int:centerid>/instructors/', views.view_instructors,
         {'status': None}, name='center_instructors'),
    path('center/<int:centerid>/instructors/<slug:status>/',
         views.view_instructors, name='center_instructors_by_status'),
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
    path('center/<int:centerid>/apply/', views.StudentApplyView.as_view(),
         name='student_apply'),
    path('endorsement/<int:pk>/', views.ChurchEndorsementView.as_view(),
         name='church_endorsement'),
    path('course/<int:courseid>/enroll', views.enroll, name='enroll'),
    path('degree/<int:degreeid>/', views.degree_apply, name='degree_apply'),

    # Catalogs
    path('course/', views.course_search, name='course_search'),
    path('course/catalog/', views.course_catalog, name='course_catalog'),
    path('center/', views.list_centers, name='center_search'),
    path('degree/', views.degree_search, name='degree_search'),
    path('degree/catalog/', views.degree_catalog, name='degree_catalog'),
    path('transcript/', views.transcript, name='transcript'),

    # Messages
    path('messages/popups/', views.current_popups, name='list_popups'),
    path('messages/popups/<int:dismiss>/dismiss/',
         views.current_popups, name='dismiss_popup'),
    path('messages/center/<int:centerid>/',
         views.MessageCenterStudentsView.as_view(),
         name='message_center_students'),
    path('messages/course/<int:courseid>/',
         views.MessageCourseStudentsView.as_view(),
         name='message_course_students'),
    path('messages/global/',
         views.MessageAllUsersView.as_view(), name='message_global'),

    # Addresses
    path('address/email/', views.edit_email_address, name='edit_email'),
    path('address/phone/', views.edit_phone_address, name='edit_phone'),
    path('address/mailing/', views.edit_mailing_address, name='edit_mailing'),

    # Reports
    path('report/center/<int:centerid>/', views.center_report, name='center_report'),
    path('report/center/<int:centerid>/tally/', views.center_tally, name='center_tally'),
]
