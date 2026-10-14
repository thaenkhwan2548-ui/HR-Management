from rest_framework import serializers
from .models import Employee, Attendance, EmployeeRequest, Payroll

class EmployeeSerializer(serializers.ModelSerializer):
    # อ่านข้อความภาษาไทยของ choices (ตัวเลือก)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bank_name_display = serializers.CharField(source='get_bank_name_display', read_only=True)
    
    # เพิ่ม Validation กำหนดให้เงินเดือน (salary) ห้ามมีค่าติดลบ (min_value=0)
    salary = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0
    )

    class Meta:
        model = Employee
        # รวมฟิลด์ที่ประกาศไว้ด้านบนเข้าใน fields ให้ครบ
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'position', 
            'department', 
            'department_display',
            'status_display',
            'bank_name_display',
            'salary'
        ]

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class EmployeeRequestSerializer(serializers.ModelSerializer):
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmployeeRequest
        fields = '__all__'

class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'