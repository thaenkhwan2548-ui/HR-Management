from django.db import models

TITLE_CHOICES = [
    ('นาย', 'นาย'),
    ('นาง', 'นาง'),
    ('นางสาว', 'นางสาว'),
]

GENDER_CHOICES = [
    ('M', 'ชาย'),
    ('F', 'หญิง'),
    ('O', 'อื่นๆ'),
]

DEPT_CHOICES = [
    ('IT', 'ไอที'),
    ('HR', 'บุคคล'),
    ('ACC', 'บัญชี'),
    ('MKT', 'การตลาด'),
    ('SALES', 'ฝ่ายขาย'),
    ('PURCHASE', 'จัดซื้อ'),
    ('CS', 'บริการลูกค้า'),
    ('MGMT', 'บริหาร'),
]

POSITION_CHOICES = [
    ('โปรแกรมเมอร์', 'โปรแกรมเมอร์ (Software Engineer)'),
    ('เจ้าหน้าที่บุคคล', 'เจ้าหน้าที่บุคคล (HR Officer)'),
    ('นักบัญชี', 'นักบัญชี (Accountant)'),
    ('เจ้าหน้าที่การตลาด', 'เจ้าหน้าที่การตลาด (Marketing Specialist)'),
    ('เจ้าหน้าที่ฝ่ายขาย', 'เจ้าหน้าที่ฝ่ายขาย (Sales Executive)'),
    ('ผู้จัดการโครงการ', 'ผู้จัดการโครงการ (Project Manager)'),
    ('เจ้าหน้าที่ธุรการ', 'เจ้าหน้าที่ธุรการ (Admin Officer)'),
    ('พนักงานทั่วไป', 'พนักงานทั่วไป'),
]

STATUS_CHOICES = [
    ('active', 'ประจำ (Permanent)'),
    ('probation', 'ทดลองงาน (Probation)'),
    ('resigned', 'ลาออก (Resigned)'),
]

BANK_CHOICES = [
    ('kbank', 'ธนาคารกสิกรไทย (KBANK)'),
    ('scb', 'ธนาคารไทยพาณิชย์ (SCB)'),
    ('bbl', 'ธนาคารกรุงเทพ (BBL)'),
    ('ktb', 'ธนาคารกรุงไทย (KTB)'),
    ('krungsri', 'ธนาคารกรุงศรีอยุธยา (BAY)'),
    ('ttb', 'ธนาคารทหารไทยธนชาต (TTB)'),
    ('other', 'อื่นๆ'),
]


class Employee(models.Model):
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, default='นาย', verbose_name="คำนำหน้าชื่อ")
    first_name = models.CharField(max_length=100, verbose_name="ชื่อ")
    last_name = models.CharField(max_length=100, verbose_name="นามสกุล")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="เพศ")
    birth_date = models.DateField(verbose_name="วัน-เดือน-ปี เกิด (YYYY-MM-DD)")
    salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="เงินเดือน")
    department = models.CharField(max_length=20, choices=DEPT_CHOICES, verbose_name="แผนก")
    position = models.CharField(max_length=100, choices=POSITION_CHOICES, default='พนักงานทั่วไป', verbose_name="ตำแหน่ง")
    hire_date = models.DateField(null=True, blank=True, verbose_name="วันที่เริ่มทำงาน")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="สถานะพนักงาน")
    phone_number = models.CharField(max_length=15, null=True, blank=True, verbose_name="เบอร์โทรศัพท์")
    address = models.TextField(null=True, blank=True, verbose_name="ที่อยู่ปัจจุบัน")
    
    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES, null=True, blank=True, verbose_name="ชื่อธนาคาร")
    bank_account = models.CharField(max_length=50, null=True, blank=True, verbose_name="เลขบัญชีธนาคาร")
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True, verbose_name="รูปภาพประจำตัว")
    
    def __str__(self):
        return f"{self.title}{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.title}{self.first_name} {self.last_name}"


class TravelCalculationHistory(models.Model):
    employee_name = models.CharField(max_length=150, verbose_name="ชื่อพนักงาน")
    distance = models.FloatField(verbose_name="ระยะทาง (กม.)")
    allowance = models.FloatField(verbose_name="เงินอุดหนุนค่าเดินทาง")
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name="เวลาที่คำนวณ")

    def __str__(self):
        return f"{self.employee_name} ({self.distance} กม.)"


# ================= 1. ระบบบันทึกเวลาทำงาน =================
class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances', verbose_name="พนักงาน")
    date = models.DateField(auto_now_add=True, verbose_name="วันที่")
    check_in = models.TimeField(null=True, blank=True, verbose_name="เวลาเข้างาน")
    check_out = models.TimeField(null=True, blank=True, verbose_name="เวลาออกงาน")
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, verbose_name="ชั่วโมง OT")

    def __str__(self):
        return f"{self.employee} - {self.date}"


# ================= 2. ระบบอนุมัติคำขอ (ลา / OT / เบิกเงิน) =================
class EmployeeRequest(models.Model):
    REQUEST_TYPES = [
        ('leave', 'ขอลาหยุด'),
        ('ot', 'ขอทำงานล่วงเวลา (OT)'),
        ('expense', 'ขอเบิกค่าใช้จ่าย'),
    ]
    STATUS_CHOICES = [
        ('pending', 'รออนุมัติ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ไม่อนุมัติ'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='requests', verbose_name="พนักงาน")
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name="ประเภทคำขอ")
    title = models.CharField(max_length=200, verbose_name="หัวข้อ / รายละเอียด")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="จำนวนเงิน หรือ จำนวนชั่วโมง")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="สถานะ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่ส่งคำขอ")
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True, verbose_name="ไฟล์แนบ")

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.employee}"


# ================= 3. ระบบคำนวณเงินเดือน (Payroll) =================
class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls', verbose_name="พนักงาน")
    month = models.IntegerField(verbose_name="เดือน")
    year = models.IntegerField(verbose_name="ปี")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="เงินเดือนพื้นฐาน")
    ot_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="ค่า OT")
    social_security = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="หักประกันสังคม (5%)")
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="หักภาษี ณ ที่จ่าย")
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="เงินเดือนสุทธิ")

    def __str__(self):
        return f"เงินเดือน {self.employee} ({self.month}/{self.year})"