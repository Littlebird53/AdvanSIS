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
         name='center_instructors'),
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
    path('center/<int:centerid>/instructor_apply/',
         views.StaffApplyView.as_view(), name='instructor_apply'),
    path('center/<int:centerid>/apply/', views.StudentApplyView.as_view(),
         name='student_apply'),
    path('center/new/', views.NewCenterApplyView.as_view(),
         name='new_center'),
    path('endorsement/<int:pk>/', views.ChurchEndorsementView.as_view(),
         name='church_endorsement'),
    path('course/<int:courseid>/enroll', views.enroll, name='enroll'),
    path('degree/<int:degreeid>/', views.degree_apply, name='degree_apply'),

    # Budgets
    path('center/<int:centerid>/budget/', views.center_budget,
         name='center_budget'),
    path('center/<int:centerid>/budget/<int:year>/', views.center_budget,
         name='old_center_budget'),
    path('center/<int:centerid>/budget/expenses/<int:budgetid>/',
         views.center_budget_expenses, name='center_budget_expenses'),
    path('center/<int:centerid>/budget/income/<int:budgetid>/',
         views.center_budget_income, name='center_budget_income'),
    path('center/<int:centerid>/budget/stipend/<int:stipendid>/',
         views.center_budget_stipend, name='center_budget_stipend'),
    path('center/<int:centerid>/budget/fee/<int:feeid>/',
         views.center_budget_fee, name='center_budget_fee'),
    path('center/<int:centerid>/budget/fee/new/<int:budgetid>/',
         views.center_budget_new_fee, name='center_budget_new_fee'),
    path('center/<int:centerid>/budget/<int:budgetid>/course/',
         views.center_budget_new_course, name='center_budget_new_course'),
    path('center/<int:centerid>/budget/enrollment/<int:enrollmentid>/',
         views.center_budget_enrollment, name='center_budget_enrollment'),
    path('center/<int:centerid>/budget/enrollment/new/<int:courseid>/',
         views.center_budget_new_enrollment, name='center_budget_new_enrollment'),

    # Catalogs
    path('course/', views.course_search, name='course_search'),
    path('course/catalog/', views.course_catalog, name='course_catalog'),
    path('course/catalog/<int:courseid>/', views.course_resources,
         name='course_resources'),
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
    path('address/email/<int:personid>/', views.edit_email_address, name='edit_email'),
    path('address/phone/<int:personid>/', views.edit_phone_address, name='edit_phone'),
    path('address/mailing/<int:personid>/', views.edit_mailing_address, name='edit_mailing'),

    # Reports
    path('report/center/<int:centerid>/', views.center_report, name='center_report'),
    path('report/center/<int:centerid>/tally/', views.center_tally, name='center_tally'),
    path('report/staff/', views.StaffReportView.as_view(), name='staff_reports'),
]
