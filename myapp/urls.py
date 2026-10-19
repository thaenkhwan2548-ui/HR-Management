from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

# ================= REST Framework Router =================
router = DefaultRouter()
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'attendances', views.AttendanceViewSet, basename='attendance-api')
router.register(r'requests', views.EmployeeRequestViewSet, basename='request-api')
router.register(r'payrolls', views.PayrollViewSet, basename='payroll-api')

# ================= URL Patterns =================
urlpatterns = [
    # API Endpoints (Django REST Framework)
    path('api/', include(router.urls)),

    # --- API คำนวณเบี้ยเลี้ยงเดินทาง ---
    path('api/calculate-allowance/', views.TravelAllowanceAPI.as_view(), name='api_calculate_allowance'),

    # --- หน้าแรก ('') ให้แสดงหน้า Login ตามที่ขอ ---
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='home_login'),
    
    path('employee/payslip/<int:pk>/', views.employee_payslip, name='payslip'),
    
    # Web View Endpoints (ระบบจัดการพนักงาน)
    path('index/', views.index, name='index'),
    path('create/', views.employee_create, name='create'),
    path('detail/<int:pk>/', views.employee_detail, name='detail'),
    path('update/<int:pk>/', views.employee_update, name='update'),
    path('delete/<int:pk>/', views.employee_delete, name='delete'),
    
    # User Authentication Endpoints
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # User / Admin / ESS System Endpoints
    path('profile/', views.profile, name='profile'),
    path('attendance/', views.attendance_view, name='attendance'),
    path('payroll/', views.payroll_view, name='payroll'),
    path('payroll/export-bank/', views.export_bank_file, name='export_bank_file'),
    path('reports/', views.report_view, name='reports'),
    path('export/sso/', views.export_sso_report, name='export_sso_report'),
    path('export/pnd1/', views.export_pnd1_report, name='export_pnd1_report'),
    path('ess/', views.ess_dashboard, name='ess_dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # --- ระบบอนุมัติคำขอ (Approval Endpoints) ---
    path('approval/', views.approval_view, name='approval'),
    path('approval/update/<int:req_id>/<str:status>/', views.update_request_status, name='update_request_status'),
    
    # หน้าแดชบอร์ดแอดมินอนุมัติคำขอ
   path('hr-approvals/', views.admin_approval_dashboard, name='admin_approval_dashboard'),
path('hr-approvals/update/<int:req_id>/<str:status>/', views.update_request_status, name='update_request_status'),
    
    # อัปเดตสถานะจากหน้าพนักงาน (ESS)
    path('ess/update-status/<int:req_id>/<str:status_type>/', views.ess_update_status, name='ess_update_status'),
    
    # หน้าจัดการ API
    path('api-manage/', views.api_page, name='api_manage'),
    path('api-page/', views.api_page, name='api_page'),
]