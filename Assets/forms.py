
from django import forms
from .models import Asset, Student
from .models import Expense


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['assigned_to', 'serial_no', 'name', 'branch_name', 'purchase_date', 'image', 'comment', 'active']
        labels = {
            'assigned_to': 'Assign Employee / User',
            'serial_no': 'Serial Number',
            'name': 'Asset Name',
            'branch_name': 'Branch Name',
            'purchase_date': 'Purchase Date',
        }
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-control-lmt'}),
            'serial_no': forms.TextInput(attrs={'placeholder': 'Serial Number', 'class': 'form-control-lmt'}),
            'name': forms.TextInput(attrs={'placeholder': 'Asset Name', 'class': 'form-control-lmt'}),
            'branch_name': forms.TextInput(attrs={'placeholder': 'Branch Name', 'class': 'form-control-lmt'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control-lmt'}),
            'image': forms.FileInput(attrs={'class': 'form-control-lmt'}),
            'comment': forms.Textarea(attrs={'placeholder': 'Comment / Description...', 'class': 'form-control-lmt', 'rows': 3}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExcelUploadForm(forms.Form):
    file = forms.FileField(label="Upload Excel File")


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'shortlisted_candidate_name',
            'contact_number',
            'email_id',
            'highest_qualification',
            'graduating_percentage',
            'pass_out_year',
            'course_undergone_in_learnmore_technologies',
            'attended_interview',
            'first_round',
            'second_round',
            'final_round',
            'company',
        ]
        widgets = {
            'shortlisted_candidate_name': forms.TextInput(attrs={'placeholder': 'Candidate Name', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'placeholder': 'Contact Number', 'class': 'form-control'}),
            'email_id': forms.EmailInput(attrs={'placeholder': 'Email ID', 'class': 'form-control'}),
            'highest_qualification': forms.TextInput(attrs={'placeholder': 'Highest Qualification', 'class': 'form-control'}),
            'graduating_percentage': forms.NumberInput(attrs={'placeholder': 'Graduating Percentage', 'class': 'form-control', 'step': '0.01'}),
            'pass_out_year': forms.NumberInput(attrs={'placeholder': 'Pass Out Year', 'class': 'form-control'}),
            'course_undergone_in_learnmore_technologies': forms.TextInput(attrs={'placeholder': 'Course Undergone', 'class': 'form-control'}),
            'attended_interview': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_round': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'second_round': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'final_round': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
        }

from django.contrib.auth.models import User

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['name', 'item', 'date', 'time', 'amount', 'payment_mode', 'reimbursed']
        labels = {
            'name': 'Employee Name / Account',
            'item': 'Item Purchased / Description',
            'payment_mode': 'Payment Method (UPI/Cash/Card)',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control-lmt'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control-lmt'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'class': 'form-control-lmt', 'step': '0.01'}),
            'payment_mode': forms.TextInput(attrs={'placeholder': 'e.g. GPay, PhonePe, Cash, HDFC Card', 'class': 'form-control-lmt'}),
            'item': forms.TextInput(attrs={'placeholder': 'e.g. Office Stationary, Tea/Coffee, Mouse', 'class': 'form-control-lmt'}),
            'reimbursed': forms.Select(attrs={'class': 'form-control-lmt'}),
        }

    def __init__(self, *args, initial_user=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        
        if is_admin:
            users = User.objects.all().order_by('username')
            choices = [(u.username, f"{u.username} ({u.profile.role if hasattr(u, 'profile') else 'User'})") for u in users]
            choices.insert(0, ('', '--- Select Employee ---'))
            initial_val = kwargs.get('initial', {}).get('name') or (initial_user.username if initial_user else '')
            self.fields['name'] = forms.ChoiceField(
                choices=choices,
                widget=forms.Select(attrs={'class': 'form-control-lmt'}),
                label='Employee Name / Account',
                initial=initial_val,
                required=True
            )
        else:
            current_username = initial_user.username if initial_user else ''
            role_label = initial_user.profile.role if (initial_user and hasattr(initial_user, 'profile')) else 'User'
            choices = [(current_username, f"{current_username} ({role_label})")]
            self.fields['name'] = forms.ChoiceField(
                choices=choices,
                widget=forms.Select(attrs={'class': 'form-control-lmt'}),
                label='Employee Name / Account',
                initial=current_username,
                required=True
            )


        

class FacultyLoginForm(forms.Form):
    pin_code = forms.CharField(
        label="Enter 4-digit PIN",
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={'placeholder': '4-digit code'}),
    )