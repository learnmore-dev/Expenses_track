
# # from django.db import models

# # ASSET_TYPES = [
# #     ('Mobile', 'Mobile'),
# #     ('Laptop', 'Laptop'),
# #     ('Fan', 'Fan'),
# #     ('Desktop', 'Desktop'),
# # ]

# # class Asset(models.Model):
# #     serial_no = models.CharField(max_length=100, unique=True)
# #     name = models.CharField(max_length=200)
# #     branch_name = models.CharField(max_length=200)
# #     purchase_date = models.DateField()
# #     asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
# #     image = models.ImageField(upload_to='assets/', blank=True, null=True)
# #     comment = models.TextField(blank=True, null=True)
# #     active = models.BooleanField(default=True)

# #     def __str__(self):
# #         return f"{self.asset_type} - {self.serial_no}"


# from django.db import models

# ASSET_TYPES = [
#     ('Mobile', 'Mobile'),
#     ('Laptop', 'Laptop'),
#     ('Fan', 'Fan'),
#     ('Desktop', 'Desktop'),
# ]

# class Asset(models.Model):
#     serial_no = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=200)
#     branch_name = models.CharField(max_length=200)
#     purchase_date = models.DateField()
#     asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
#     image = models.ImageField(upload_to='assets/', blank=True, null=True)
#     comment = models.TextField(blank=True, null=True)
#     active = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.asset_type} - {self.serial_no}"

# # Placements section models
# class Company(models.Model):
#     name = models.CharField(max_length=100, unique=True)

#     def __str__(self):
#         return self.name

# class Student(models.Model):
#     name = models.CharField(max_length=200)
#     email = models.EmailField()
#     company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='students')
#     # Add other relevant fields from your Excel file as needed, for example:
#     roll_no = models.CharField(max_length=50, blank=True, null=True)
#     branch = models.CharField(max_length=200, blank=True, null=True)
#     placement_date = models.DateField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.name} ({self.company.name})"
from django.db import models
from django.contrib.auth.models import User

class CustomRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=100, default='Intern')
    custom_role = models.ForeignKey(CustomRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

ASSET_TYPES = [
    ('Mobile', 'Mobile'),
    ('Laptop', 'Laptop'),
    ('Fan', 'Fan'),
    ('Desktop', 'Desktop'),
]

class Asset(models.Model):
    serial_no = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200)
    purchase_date = models.DateField()
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
    image = models.ImageField(upload_to='assets/', blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')

    def __str__(self):
        return f"{self.asset_type} - {self.serial_no}"

class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    id = models.AutoField(primary_key=True)
    shortlisted_candidate_name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    email_id = models.EmailField()
    highest_qualification = models.CharField(max_length=200, blank=True, null=True)
    graduating_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    pass_out_year = models.IntegerField(blank=True, null=True)
    course_undergone_in_learnmore_technologies = models.CharField(max_length=200, blank=True, null=True)
    attended_interview = models.BooleanField(default=False)
    first_round = models.BooleanField(default=False)
    second_round = models.BooleanField(default=False)
    final_round = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='students',
        blank=True,
        null=True,       # Allow NULL in database
    )

    def __str__(self):
        company_name = self.company.name if self.company else "<No Company>"
        return f"{self.shortlisted_candidate_name} ({company_name})"




class Expense(models.Model):
    REIMBURSED_CHOICES = [
        ('YES', 'Yes'),
        ('NO', 'No'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    name = models.CharField(max_length=100)
    item = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=50)
    reimbursed = models.CharField(
        max_length=3,
        choices=REIMBURSED_CHOICES,
        default='NO',
        verbose_name='Reimbursed (Paid back to employee)'
    )
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING',
        verbose_name='Approval Status'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')

    def __str__(self):
        return f"{self.name} - {self.item} ({self.get_approval_status_display()})"


class PortalLink(models.Model):
    title = models.CharField(max_length=150)
    url = models.URLField()
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title


class CompanyEvent(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='events/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

