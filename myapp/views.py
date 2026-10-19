from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime, date
from django.utils import timezone
from .models import Employee, Attendance, EmployeeRequest, Payroll, TravelCalculationHistory
import math

# --- นำเข้า Django REST Framework ---
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response

# --- นำเข้า Serializers และ Forms ---
from .forms import EmployeeForm, UserProfileForm, CustomRegisterForm
from .serializers import (
    EmployeeSerializer, 
    AttendanceSerializer, 
    EmployeeRequestSerializer, 
    PayrollSerializer
)

# ================= Django REST Framework ViewSets =================
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('id')
    serializer_class = EmployeeSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('-date')
    serializer_class = AttendanceSerializer

class EmployeeRequestViewSet(viewsets.ModelViewSet):
    queryset = EmployeeRequest.objects.all().order_by('-created_at')
    serializer_class = EmployeeRequestSerializer

class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all().order_by('-year', '-month')
    serializer_class = PayrollSerializer


# ================= ฟังก์ชันตรวจสอบสิทธิ์ (Admin Only) =================
def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def index(request):
    query = request.GET.get('q', '').strip()
    employees = Employee.objects.all().order_by('-id')
    
    if query:
        keywords = query.split()
        for kw in keywords:
            employees = employees.filter(
                Q(first_name__icontains=kw) | 
                Q(last_name__icontains=kw) | 
                Q(position__icontains=kw) |
                Q(address__icontains=kw)
            )

    paginator = Paginator(employees, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'index.html', {'page_obj': page_obj, 'query': query})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
@permission_required('myapp.add_employee', raise_exception=True)
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มข้อมูลพนักงานสำเร็จ')
            return redirect('index')
    else:
        form = EmployeeForm()
    return render(request, 'form_view.html', {'form': form, 'title': 'เพิ่มพนักงาน'})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
@permission_required('myapp.change_employee', raise_exception=True)
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขข้อมูลสำเร็จ')
            return redirect('index')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'form_view.html', {'form': form, 'title': 'แก้ไขพนักงาน'})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
@permission_required('myapp.delete_employee', raise_exception=True)
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'ลบข้อมูลสำเร็จ')
        return redirect('index')
    return render(request, 'delete.html', {'employee': employee})

def register(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST) if 'CustomRegisterForm' in globals() else UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                Employee.objects.get_or_create(
                    first_name=user.username,
                    defaults={
                        'last_name': '',
                        'position': 'พนักงานทั่วไป',
                        'department': 'IT',
                        'birth_date': date(2000, 1, 1),
                        'hire_date': date.today(),
                        'salary': 0.00
                    }
                )
            except Exception as e:
                print("Auto create employee error:", e)

            messages.success(request, '🎉 สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบเพื่อใช้งาน')
            return redirect('login') 
    else:
        form = CustomRegisterForm() if 'CustomRegisterForm' in globals() else UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            
            if 'profile_image' in request.FILES:
                try:
                    user.profile.image = request.FILES['profile_image']
                    user.profile.save()
                except Exception as e:
                    print("Profile image save error:", e)

            messages.success(request, 'อัปเดตโปรไฟล์สำเร็จ')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return render(request, 'detail.html', {'employee': employee})

def custom_permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)


# ================= ฟังก์ชันระบบแอดมินและบันทึกเวลา (รองรับพนักงานทั่วไป) =================

@login_required
def attendance_view(request):
    # ค้นหาข้อมูลพนักงานที่ผูกกับ User ปัจจุบัน
    try:
        current_employee = Employee.objects.get(
            Q(first_name__iexact=request.user.username) | 
            Q(last_name__iexact=request.user.username)
        )
    except Employee.DoesNotExist:
        current_employee = Employee.objects.create(
            first_name=request.user.username,
            last_name='',
            position='พนักงานทั่วไป',
            department='IT',
            birth_date=date(2000, 1, 1),
            hire_date=date.today(),
            salary=0.00
        )

    # ถ้าเป็น Admin ให้เห็นทั้งหมด ถ้าไม่ใช่ให้เห็นเฉพาะของตัวเอง
    if request.user.is_staff:
        attendances = Attendance.objects.all().order_by('-date')
    else:
        attendances = Attendance.objects.filter(employee=current_employee).order_by('-date')

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        action = request.POST.get('action')
        
        # ถ้าเป็น Admin เลือกพนักงานจากฟอร์มได้ แต่ถ้าเป็นพนักงานทั่วไปใช้ชื่อตัวเอง
        if request.user.is_staff and emp_id:
            employee = get_object_or_404(Employee, id=emp_id)
        else:
            employee = current_employee

        today = date.today()
        now = datetime.now().time()
        
        att, created = Attendance.objects.get_or_create(employee=employee, date=today)
        if action == 'check_in':
            att.check_in = now
            messages.success(request, f'บันทึกเวลาเข้างานของ {employee.first_name} เวลา {now.strftime("%H:%M")} น. สำเร็จ')
        elif action == 'check_out':
            att.check_out = now
            messages.success(request, f'บันทึกเวลาออกงานของ {employee.first_name} เวลา {now.strftime("%H:%M")} น. สำเร็จ')
        att.save()
        return redirect('attendance')

    employees = Employee.objects.all()
    return render(request, 'attendance.html', {
        'attendances': attendances, 
        'employees': employees,
        'current_employee': current_employee
    })

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def approval_view(request):
    requests = EmployeeRequest.objects.all().order_by('-created_at')
    return render(request, 'approval.html', {'requests': requests})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def admin_approval_dashboard(request):
    requests_list = EmployeeRequest.objects.all().order_by('-created_at')
    context = {'requests_list': requests_list}
    return render(request, 'admin_approval.html', context)

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def update_request_status(request, req_id, status):
    req_item = get_object_or_404(EmployeeRequest, id=req_id)
    if status in ['approved', 'rejected']:
        req_item.status = status
        req_item.save()
    return redirect('admin_approval_dashboard')

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def payroll_view(request):
    employees = Employee.objects.all()
    payrolls = []

    for emp in employees:
        base = float(emp.salary) if emp.salary else 0
        sso = min(base * 0.05, 750.0)
        tax = base * 0.03
        net = base - sso - tax

        payrolls.append({
            'employee': emp,
            'base': base,
            'sso': sso,
            'tax': tax,
            'net': net
        })

    return render(request, 'payroll.html', {'payrolls': payrolls})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def export_bank_file(request):
    current_date = timezone.now().strftime("%Y%m%d")
    filename = f"payroll_bank_transfer_{current_date}.txt"
    
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    lines = ["Bank|Account_No|Employee_Name|Net_Salary"]
    employees = Employee.objects.all()
    
    for emp in employees:
        base = float(emp.salary) if emp.salary else 0.0
        sso = min(base * 0.05, 750.0)
        tax = base * 0.03
        net = base - sso - tax
        
        bank = emp.get_bank_name_display() if hasattr(emp, 'get_bank_name_display') and emp.bank_name else "ไม่ระบุ"
        acc = getattr(emp, 'bank_account', '-') or "-"
        
        if net > 0:
            name = f"{emp.first_name} {emp.last_name}".strip()
            line = f"{bank}|{acc}|{name}|{net:.2f}"
            lines.append(line)

    response.write("\n".join(lines))
    return response

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def report_view(request):
    total_employees = Employee.objects.count()
    pending_leaves = EmployeeRequest.objects.filter(request_type='leave', status='pending').count()
    approved_ot = EmployeeRequest.objects.filter(request_type='ot', status='approved').count()
    
    employees = Employee.objects.all()
    total_salary = sum([float(emp.salary) for emp in employees if emp.salary])
    total_sso = sum([min(float(emp.salary) * 0.05, 750.0) for emp in employees if emp.salary])
    total_tax = total_salary * 0.03

    context = {
        'total_employees': total_employees,
        'pending_leaves': pending_leaves,
        'approved_ot': approved_ot,
        'total_salary': total_salary,
        'total_sso': total_sso,
        'total_tax': total_tax,
    }
    return render(request, 'report.html', context)


# ================= ฟังก์ชันระบบพนักงาน (ESS) =================

@login_required
def ess_dashboard(request):
    try:
        current_employee = Employee.objects.get(
            Q(first_name__iexact=request.user.username) | 
            Q(last_name__iexact=request.user.username)
        )
    except Employee.DoesNotExist:
        current_employee = Employee.objects.create(
            first_name=request.user.username,
            last_name='',
            position='พนักงานทั่วไป',
            department='IT',
            birth_date=date(2000, 1, 1),
            hire_date=date.today(),
            salary=0.00
        )

    employees = Employee.objects.all().order_by('first_name')
    recent_requests = EmployeeRequest.objects.all().order_by('-created_at')[:10]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action in ['check_in', 'check_out']:
            emp_id = request.POST.get('employee_id')
            emp = get_object_or_404(Employee, id=emp_id) if emp_id else current_employee
            
            today = date.today()
            now = datetime.now().time()
            att, created = Attendance.objects.get_or_create(employee=emp, date=today)
            
            if action == 'check_in':
                att.check_in = now
                messages.success(request, f'บันทึกเวลาเข้างานของ {emp.first_name} เวลา {now.strftime("%H:%M")} น. สำเร็จ')
            elif action == 'check_out':
                att.check_out = now
                messages.success(request, f'บันทึกเวลาออกงานของ {emp.first_name} เวลา {now.strftime("%H:%M")} น. สำเร็จ')
            att.save()
            
        elif action == 'submit_request':
            req_type = request.POST.get('request_type')
            title = request.POST.get('title')
            amount = request.POST.get('amount') or 0
            emp_id = request.POST.get('employee_id')
            
            target_employee = get_object_or_404(Employee, id=emp_id) if emp_id else current_employee
            
            EmployeeRequest.objects.create(
                employee=target_employee,
                request_type=req_type,
                title=title,
                amount=amount
            )
            messages.success(request, 'ส่งคำขอสำเร็จ ระบบส่งเรื่องให้เรียบร้อยแล้ว')
            
        return redirect('ess_dashboard')

    return render(request, 'ess_dashboard.html', {
        'employee': current_employee,
        'employees': employees, 
        'recent_requests': recent_requests
    })

@login_required
def ess_update_status(request, req_id, status_type):
    req_item = get_object_or_404(EmployeeRequest, id=req_id)
    if status_type in ['approved', 'rejected']:
        req_item.status = status_type
        req_item.save()
        messages.success(request, 'อัปเดตสถานะคำขอเรียบร้อยแล้ว')
    return redirect('ess_dashboard')


# ================= ฟังก์ชันแสดงหน้า API =================
def api_page(request):
    return render(request, 'api.html')


# ================= ฟังก์ชันแสดงหน้าแดชบอร์ดภาพรวม =================
@login_required
def dashboard_view(request):
    total_employees = Employee.objects.count()
    
    travel_history = TravelCalculationHistory.objects.all().order_by('-id')
    total_travel_requests = travel_history.count()
    recent_travels = travel_history[:5]
    
    total_requests = EmployeeRequest.objects.count()
    approved_count = EmployeeRequest.objects.filter(status='approved').count()
    pending_count = EmployeeRequest.objects.filter(status='pending').count()
    rejected_count = EmployeeRequest.objects.filter(status='rejected').count()
    
    leave_count = EmployeeRequest.objects.filter(request_type='leave').count()
    expense_count = EmployeeRequest.objects.filter(request_type='expense').count()
    ot_count = EmployeeRequest.objects.filter(request_type='ot').count()

    recent_requests = EmployeeRequest.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_employees': total_employees,
        'total_travel_requests': total_travel_requests,
        'travel_history': recent_travels,
        'total_requests': total_requests,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'leave_count': leave_count,
        'expense_count': expense_count,
        'ot_count': ot_count,
        'recent_requests': recent_requests,
    }
    return render(request, 'dashboard.html', context)


# ================= ฟังก์ชันรายงาน =================
@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def export_sso_report(request):
    current_date = timezone.now().strftime("%Y%m%d")
    filename = f"social_security_report_{current_date}.txt"
    
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    lines = ["=== รายงานการนำส่งเงินสมทบประกันสังคม (สปส. 1-10) ==="]
    employees = Employee.objects.all()
    total_sso_all = 0
    
    for emp in employees:
        base = float(emp.salary) if emp.salary else 0.0
        sso = min(base * 0.05, 750.0)
        total_sso_all += sso
        name = f"{emp.first_name} {emp.last_name}".strip()
        lines.append(f"พนักงาน: {name} | เงินเดือน: {base:.2f} | ประกันสังคม: {sso:.2f}")
        
    lines.append(f"\nรวมยอดเงินสมทบประกันสังคมทั้งสิ้น: {total_sso_all:.2f} บาท")
    response.write("\n".join(lines))
    return response

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def export_pnd1_report(request):
    current_date = timezone.now().strftime("%Y%m%d")
    filename = f"pnd1_tax_report_{current_date}.txt"
    
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    lines = ["=== รายงานภาษีเงินได้หัก ณ ที่จ่าย (ภ.ง.ด.1) ==="]
    employees = Employee.objects.all()
    total_tax_all = 0
    
    for emp in employees:
        base = float(emp.salary) if emp.salary else 0.0
        tax = base * 0.03
        total_tax_all += tax
        name = f"{emp.first_name} {emp.last_name}".strip()
        lines.append(f"พนักงาน: {name} | เงินเดือน: {base:.2f} | ภาษีหัก ณ ที่จ่าย: {tax:.2f}")
        
    lines.append(f"\nรวมยอดภาษีหัก ณ ที่จ่ายทั้งสิ้น: {total_tax_all:.2f} บาท")
    response.write("\n".join(lines))
    return response

@login_required
def employee_payslip(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    base = float(employee.salary) if employee.salary else 0
    sso = min(base * 0.05, 750.0)
    tax = base * 0.03
    net = base - sso - tax

    context = {
        'employee': employee,
        'base': base,
        'sso': sso,
        'tax': tax,
        'net': net
    }
    return render(request, 'payslip.html', context)


# ================= คำนวณเบี้ยเลี้ยงเดินทาง =================

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 2)


class TravelAllowanceAPI(APIView):
    def post(self, request):
        try:
            emp_lat = request.data.get('latitude')
            emp_lon = request.data.get('longitude')
            
            if not emp_lat or not emp_lon:
                return Response({"error": "กรุณาส่งพิกัด Latitude และ Longitude ของพนักงาน"}, status=status.HTTP_400_BAD_REQUEST)

            COMPANY_LAT = 13.7563 
            COMPANY_LON = 100.5018

            distance_km = calculate_distance(emp_lat, emp_lon, COMPANY_LAT, COMPANY_LON)
            allowance_rate = 5 
            total_allowance = round(distance_km * allowance_rate, 2)

            TravelCalculationHistory.objects.create(
                employee_name="พนักงานทั่วไป (จากการคำนวณ)",
                distance=distance_km,
                allowance=total_allowance
            )

            return Response({
                "status": "success",
                "distance_km": distance_km,
                "allowance_baht": total_allowance,
                "message": f"ระยะทาง {distance_km} กม. ได้รับเงินอุดหนุน {total_allowance} บาท"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)