from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        # เอา exclude ออก เพื่อให้ฟิลด์ position แสดงผลในฟอร์มปกติ
        widgets = {
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            # กำหนดให้ฟิลด์ position แสดงเป็นช่องเลือก (Select Dropdown)
            'position': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น 01454789632'}),
            'bank_name': forms.Select(attrs={'class': 'form-select'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น 111-111-1111'}),
            'hire_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean_salary(self):
        salary = self.cleaned_data.get('salary')
        if salary is not None and salary < 0:
            raise forms.ValidationError("เงินเดือนต้องไม่ติดลบ")
        return salary

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class CustomRegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "ชื่อผู้ใช้"
        self.fields['username'].help_text = "ระบุชื่อผู้ใช้ (ภาษาอังกฤษ ตัวเลข และ @/./+/-/_ เท่านั้น)"
        
        pass_fields = [f for f in self.fields if f != 'username']
        if len(pass_fields) >= 2:
            self.fields[pass_fields[0]].label = "รหัสผ่าน"
            self.fields[pass_fields[0]].help_text = "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร, ไม่เป็นตัวเลขทั้งหมด และไม่ใช้รหัสที่เดาง่าย"
            
            self.fields[pass_fields[1]].label = "ยืนยันรหัสผ่าน"
            self.fields[pass_fields[1]].help_text = "กรอกรหัสผ่านอีกครั้งเพื่อยืนยันความถูกต้อง"