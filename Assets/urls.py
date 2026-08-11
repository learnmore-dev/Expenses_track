from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),   # empty path redirects to login
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='Assets/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('home/', views.home, name='home'),
    path('registered-assets/', views.registered_assets, name='registered_assets'),  # Registered Assets list
    path('assets/<str:asset_type>/', views.add_asset, name='add_asset'),  # Add asset form for each type
    path('edit-asset/<int:pk>/', views.edit_asset, name='edit_asset'),  # Edit existing asset
    path('delete-asset/<int:pk>/', views.delete_asset, name='delete_asset'),  # Delete asset confirmation
    path('placements/', views.placements, name='placements'),
    path('placements/add/', views.add_student, name='add_student'),
    path('placements/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('placements/delete/<int:pk>/', views.delete_student, name='delete_student'),
    path('placements/upload/', views.upload_students, name='upload_students'),
    path('placements/download/', views.download_students, name='download_students'),
    path('companies/', views.manage_companies, name='manage_companies'),
    path('companies/delete/<int:pk>/', views.delete_company, name='delete_company'),
    path('portals/', views.manage_portals, name='manage_portals'),
    path('portals/delete/<int:pk>/', views.delete_portal, name='delete_portal'),
    path('events/', views.manage_events, name='manage_events'),
    path('events/delete/<int:pk>/', views.delete_event, name='delete_event'),
    path('events-gallery/', views.student_events, name='student_events'),
    path('it-courses/', views.it_courses, name='it_courses'),
    path('business/', views.business, name='business'),
    path('management/', views.management, name='management'),
    path('personal/', views.personal, name='personal'),
    path('teaching/', views.teaching, name='teaching'),
    path('placements/<int:student_id>/', views.placement_detail, name='placement_detail'),
    path('expense-tracker/', views.expense_tracker, name='expense_tracker'),
    path('expense-registered/', views.expense_registered, name='expense_registered'),
    path('expense-update/<int:pk>/', views.expense_update, name='expense_update'),
    path('expense/approve/<int:pk>/', views.approve_expense, name='approve_expense'),
    path('expense/reject/<int:pk>/', views.reject_expense, name='reject_expense'),
    path('faculty-login/', views.faculty_login, name='faculty_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('create-user/', views.create_user_account, name='create_user_account'),
    path('delete-user/<int:pk>/', views.delete_user_account, name='delete_user_account'),
    path('roles/', views.manage_roles, name='manage_roles'),
    path('roles/delete/<int:pk>/', views.delete_role, name='delete_role'),
    path('api/upload-call-recording/', views.upload_call_recording_api, name='upload_call_recording_api'),
    path('call-recordings/', views.call_recordings_hub, name='call_recordings_hub'),
    path('call-recordings/delete/<int:pk>/', views.delete_call_recording, name='delete_call_recording'),
]
