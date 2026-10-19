from django.contrib import admin
from .models import Employee, EmployeeRequest, Attendance, Payroll, TravelCalculationHistory

# 1. ลงทะเบียน Employee แบบเดิมของแก
admin.site.register(Employee)

# 2. ลงทะเบียนระบบอนุมัติคำขอ (ใช้ EmployeeRequest ที่ถูกต้องตาม models.py)
@admin.register(EmployeeRequest)
class EmployeeRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'request_type', 'title', 'amount', 'status', 'created_at')
    list_filter = ('status', 'request_type', 'created_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'title', 'request_type')

# 3. ลงทะเบียนโมเดลอื่นๆ ในระบบ
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'overtime_hours')
    list_filter = ('date',)

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'base_salary', 'net_salary')
    list_filter = ('year', 'month')

@admin.register(TravelCalculationHistory)
class TravelHistoryAdmin(admin.ModelAdmin):
    list_display = ('employee_name', 'distance', 'allowance', 'calculated_at')