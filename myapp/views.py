from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime, date
from django.utils import timezone
from .models import Employee, TravelCalculationHistory
import math  # --- เพิ่มบรรทัดนี้สำหรับคำนวณระยะทาง (Haversine) ---

# --- นำเข้า Django REST Framework ---
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response

# --- นำเข้า Models, Forms และ Serializers ---
from .models import Employee, Attendance, EmployeeRequest, Payroll, TravelCalculationHistory
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


# ================= API View สำหรับสร้าง Order + Payment =================
class CreateOrderTransactionView(APIView):
    def post(self, request):
        data = request.data
        try:
            # 1. บันทึกข้อมูล Order
            order = Order.objects.create(
                order_id=data.get('order_id'),
                customer_id=data.get('customer_id'),
                total_amount=data.get('total_amount'),
                order_status=data.get('order_status', 'Pending')
            )
            
            # 2. บันทึกข้อมูล Payment (ถ้ามีส่งข้อมูลชำระเงินมาด้วย)
            pay_info = data.get('payment_info')
            if pay_info:
                Payment.objects.create(
                    order=order,
                    payment_method=pay_info.get('method', 'PromptPay'),
                    amount=pay_info.get('amount', data.get('total_amount')),
                    payment_status=pay_info.get('status', 'Success'),
                    transaction_ref=pay_info.get('transaction_ref', '')
                )
                order.order_status = 'Paid'
                order.save()

            return Response({
                "status": "success",
                "message": "บันทึกรายการสั่งซื้อและการชำระเงินเรียบร้อยแล้ว",
                "order_id": order.order_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        

# ================= ฟังก์ชันสำหรับแสดงผลหน้าเว็บ (Web Views) =================

@login_required
def order_list(request):
    """หน้าแสดงรายการสั่งซื้อทั้งหมดบนเว็บ"""
    query = request.GET.get('q', '')
    orders = Order.objects.all().order_by('-created_at')
    
    if query:
        orders = orders.filter(
            Q(order_id__icontains=query) | 
            Q(customer_id__icontains=query) |
            Q(order_status__icontains=query)
        )
        
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'order_list.html', {'page_obj': page_obj, 'query': query})

@login_required
def order_detail(request, order_id):
    """หน้าแสดงรายละเอียดคำสั่งซื้อและประวัติการชำระเงิน"""
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'order_detail.html', {'order': order})


# ================= ฟังก์ชันตรวจสอบสิทธิ์ (Admin Only) =================
def is_admin(user):
    return user.is_staff

# =============================================================

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def index(request):
    query = request.GET.get('q', '')
    employees = Employee.objects.all().order_by('-id')
    
    if query:
        dept_code = None
        q_lower = query.strip().lower()
        
        if 'ไอที' in q_lower or 'it' in q_lower:
            dept_code = 'IT'
        elif 'บุคคล' in q_lower or 'hr' in q_lower:
            dept_code = 'HR'
        elif 'บัญชี' in q_lower or 'acc' in q_lower:
            dept_code = 'ACC'
        elif 'การตลาด' in q_lower or 'mkt' in q_lower:
            dept_code = 'MKT'
        elif 'ขาย' in q_lower or 'sales' in q_lower:
            dept_code = 'SALES'
        elif 'จัดซื้อ' in q_lower or 'purchase' in q_lower:
            dept_code = 'PURCHASE'
        elif 'บริการ' in q_lower or 'customer' in q_lower or 'cs' in q_lower:
            dept_code = 'CS'
        elif 'บริหาร' in q_lower or 'mgmt' in q_lower:
            dept_code = 'MGMT'

        search_filter = (
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(position__icontains=query)
        )
        
        if dept_code:
            search_filter |= Q(department=dept_code)
        else:
            search_filter |= Q(department__icontains=query)

        employees = employees.filter(search_filter)

    # --- เพิ่มระบบแบ่งหน้า (Paginator) แสดงหน้าละ 6 คน ---
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
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
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


# ================= ฟังก์ชันระบบแอดมิน (Admin Only) =================

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def attendance_view(request):
    attendances = Attendance.objects.all().order_by('-date')
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        action = request.POST.get('action')
        employee = get_object_or_404(Employee, id=emp_id)
        today = date.today()
        now = datetime.now().time()
        
        att, created = Attendance.objects.get_or_create(employee=employee, date=today)
        if action == 'check_in':
            att.check_in = now
        elif action == 'check_out':
            att.check_out = now
        att.save()
        return redirect('attendance')

    employees = Employee.objects.all()
    return render(request, 'attendance.html', {'attendances': attendances, 'employees': employees})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def approval_view(request):
    requests = EmployeeRequest.objects.all().order_by('-created_at')
    return render(request, 'approval.html', {'requests': requests})

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def update_request_status(request, req_id, status):
    req_item = get_object_or_404(EmployeeRequest, id=req_id)
    if status in ['approved', 'rejected']:
        req_item.status = status
        req_item.save()
    return redirect('approval')

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


# ================= ฟังก์ชันระบบพนักงาน (ESS - พนักงานทุกคนเข้าได้) =================

@login_required
def ess_dashboard(request):
    if not Employee.objects.filter(Q(first_name=request.user.username) | Q(last_name=request.user.username)).exists():
        try:
            Employee.objects.create(
                first_name=request.user.username,
                last_name='',
                position='พนักงานทั่วไป',
                department='IT',
                birth_date=date(2000, 1, 1),
                hire_date=date.today(),
                salary=0.00
            )
        except Exception as e:
            print("Auto create employee error:", e)

    employees = Employee.objects.all().order_by('first_name')
    recent_requests = EmployeeRequest.objects.all().order_by('-created_at')[:10]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        emp_id = request.POST.get('employee_id')
        
        if not emp_id:
            messages.error(request, 'กรุณาเลือกชื่อพนักงานก่อนทำรายการ')
            return redirect('ess_dashboard')
            
        emp = get_object_or_404(Employee, id=emp_id)
        
        if action in ['check_in', 'check_out']:
            today = date.today()
            now = datetime.now().time()
            att, created = Attendance.objects.get_or_create(employee=emp, date=today)
            
            if action == 'check_in':
                att.check_in = now
                messages.success(request, f'บันทึกเวลาเข้างาน {now.strftime("%H:%M")} น. สำเร็จ')
            elif action == 'check_out':
                att.check_out = now
                messages.success(request, f'บันทึกเวลาออกงาน {now.strftime("%H:%M")} น. สำเร็จ')
            att.save()
            
        elif action == 'submit_request':
            req_type = request.POST.get('request_type')
            title = request.POST.get('title')
            amount = request.POST.get('amount') or 0
            attachment = request.FILES.get('attachment')
            
            EmployeeRequest.objects.create(
                employee=emp,
                request_type=req_type,
                title=title,
                amount=amount,
                attachment=attachment
            )
            messages.success(request, 'ส่งคำขอสำเร็จ ระบบส่งเรื่องให้ HR อนุมัติแล้ว')
            
        return redirect('ess_dashboard')

    return render(request, 'ess_dashboard.html', {
        'employees': employees, 
        'recent_requests': recent_requests
    })


# ================= ฟังก์ชันแสดงหน้า API =================
def api_page(request):
    return render(request, 'api.html')


# ================= ฟังก์ชันแสดงหน้าแดชบอร์ดใหม่ (Dashboard View) =================
@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def dashboard_view(request):
    total_employees = Employee.objects.count()
    travel_histories = TravelCalculationHistory.objects.all().order_by('-calculated_at')[:10]
    
    context = {
        'total_employees': total_employees,
        'travel_histories': travel_histories,
    }
    return render(request, 'dashboard.html', context)


# ================= ฟังก์ชันสำหรับสร้างไฟล์รายงาน (เพิ่มใหม่) =================
@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def export_sso_report(request):
    return HttpResponse("ทดสอบระบบ: กำลังสร้างไฟล์รายงาน สปส. 1-10")

@login_required
@user_passes_test(is_admin, login_url='ess_dashboard')
def export_pnd1_report(request):
    return HttpResponse("ทดสอบระบบ: กำลังสร้างไฟล์รายงาน ภ.ง.ด.1")

@login_required
def employee_payslip(request, pk):
    """หน้าแสดงสลิปเงินเดือนรายบุคคล"""
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


# ================= ฟังก์ชัน และ API คำนวณเบี้ยเลี้ยงเดินทาง =================

def calculate_distance(lat1, lon1, lat2, lon2):
    """ฟังก์ชันคำนวณระยะทาง (กิโลเมตร) ระหว่างพิกัด 2 จุด ด้วย Haversine Formula"""
    R = 6371.0 # รัศมีของโลก (กิโลเมตร)

    # แปลงองศาเป็นเรเดียน
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 2) # คืนค่าระยะทางเป็น กิโลเมตร (ทศนิยม 2 ตำแหน่ง)


class TravelAllowanceAPI(APIView):
    def post(self, request):
        try:
            # 1. รับพิกัดบ้านพนักงานที่ส่งมาจากหน้าเว็บ
            emp_lat = request.data.get('latitude')
            emp_lon = request.data.get('longitude')
            
            if not emp_lat or not emp_lon:
                return Response({"error": "กรุณาส่งพิกัด Latitude และ Longitude ของพนักงาน"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. กำหนดพิกัดของ "บริษัท" (แก้ตัวเลขตรงนี้ให้เป็นพิกัดจริงของบริษัทคุณ)
            COMPANY_LAT = 13.7563 # ตัวอย่าง: พิกัดกรุงเทพ
            COMPANY_LON = 100.5018

            # 3. คำนวณระยะทาง (กิโลเมตร)
            distance_km = calculate_distance(emp_lat, emp_lon, COMPANY_LAT, COMPANY_LON)

            # 4. คำนวณเงินอุดหนุน
            allowance_rate = 5 
            total_allowance = round(distance_km * allowance_rate, 2)

            # --- เพิ่มส่วนบันทึกประวัติการคำนวณลงใน Database (TravelCalculationHistory) ---
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