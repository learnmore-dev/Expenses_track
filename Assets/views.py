from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from functools import wraps
from django.contrib.auth.models import User
from .forms import AssetForm, ExcelUploadForm, ExpenseForm, FacultyLoginForm, StudentForm
from .models import Asset, Company, Student, Expense, PortalLink, CompanyEvent, UserProfile, CustomRole, CallRecording
import pandas as pd
import os
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.views.decorators.csrf import csrf_exempt



EXCEL_FILE_PATH = r"C:\Users\abhis\Downloads\Learnmore placemnet Student Data.xlsx"

# Decorator to ensure faculty access
def faculty_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_faculty'):
            messages.error(request, "You need faculty access to view this page.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def index(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        return redirect('login')


def register(request):
    messages.info(request, "Public self-registration is disabled. Employee accounts are created directly by the Admin.")
    return redirect('login')


@login_required
def home(request):
    events = CompanyEvent.objects.all().order_by('-created_at')
    portals = PortalLink.objects.all().order_by('id')
    return render(request, 'Assets/home.html', {
        'events': events,
        'portals': portals,
    })


@login_required
def faculty_login(request):
    if request.method == 'POST':
        form = FacultyLoginForm(request.POST)
        if form.is_valid():
            pin = form.cleaned_data['pin_code']
            if pin == getattr(settings, "FACULTY_PIN", "1234"):
                request.session['is_faculty'] = True
                messages.success(request, "Admin access granted! Full Add & Edit permissions unlocked.")
                return redirect('home')
            else:
                messages.error(request, "Invalid code. Access denied.")
    else:
        form = FacultyLoginForm()
    return render(request, 'Assets/faculty_login.html', {'form': form})


@login_required
@faculty_required
def add_asset(request, asset_type):
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.asset_type = asset_type
            asset.save()
            form.save_m2m()
            return redirect('registered_assets')
    else:
        form = AssetForm()
    return render(request, 'Assets/add_asset.html', {'form': form, 'asset_type': asset_type})


@login_required
def registered_assets(request):
    user_role = request.user.profile.role.lower() if (hasattr(request.user, 'profile') and request.user.profile.role) else ''
    is_admin = request.user.is_superuser or (user_role == 'admin')
    if is_admin:
        assets = Asset.objects.all().order_by('-id')
    else:
        assets = Asset.objects.filter(assigned_to=request.user).order_by('-id')
    return render(request, 'Assets/registered_assets.html', {'assets': assets, 'is_admin': is_admin})


@login_required
@faculty_required
def edit_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES, instance=asset)
        if form.is_valid():
            form.save()
            return redirect('registered_assets')
    else:
        form = AssetForm(instance=asset)
    return render(request, 'Assets/add_asset.html', {'form': form, 'asset_type': asset.asset_type})


@login_required
@faculty_required
def delete_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        asset.delete()
        return redirect('registered_assets')
    return render(request, 'Assets/delete_confirm.html', {'asset': asset})


@login_required
def placements(request):
    db_companies = list(Company.objects.values_list('name', flat=True))
    
    excel_companies = []
    excel_students = []
    if os.path.exists(EXCEL_FILE_PATH):
        try:
            df = pd.read_excel(EXCEL_FILE_PATH)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            df.rename(columns={'highest_qualificati_on': 'highest_qualification'}, inplace=True)
            df['company'] = df['company'].astype(str).str.strip().str.upper()
            df = df.fillna('')
            if 'id' not in df.columns:
                df['id'] = df.index + 1
            excel_companies = list(df['company'].unique())
            excel_students = df.to_dict(orient='records')
        except Exception:
            pass

    all_company_names = sorted(list(set(db_companies + excel_companies)))
    companies = ['ALL'] + [c for c in all_company_names if c]

    search_query = request.GET.get('search', '').strip()
    selected_company = request.GET.get('company')

    # Group DB Students by email_id & name
    all_db_students = Student.objects.all().select_related('company')

    # Extract unique candidates
    grouped_candidates = {}
    for st in all_db_students:
        key = (st.email_id.lower().strip(), st.shortlisted_candidate_name.lower().strip())
        if key not in grouped_candidates:
            grouped_candidates[key] = {
                'primary_id': st.id,
                'name': st.shortlisted_candidate_name,
                'email': st.email_id,
                'contact': st.contact_number,
                'records': [],
            }
        grouped_candidates[key]['records'].append(st)

    # Process grouped summaries
    students_summary = []
    for key, cand in grouped_candidates.items():
        records = cand['records']
        company_names = [r.company.name for r in records if r.company]
        
        # Filter by selected company if specified
        if selected_company and selected_company != 'ALL':
            if not any(c.upper() == selected_company.upper() for c in company_names):
                continue

        # Filter by search query
        if search_query:
            if search_query.lower() not in cand['name'].lower() and search_query.lower() not in cand['email'].lower():
                continue

        total_interviews = sum(1 for r in records if r.attended_interview)
        placed_records = [r for r in records if r.final_round]
        placed_companies = [r.company.name for r in placed_records if r.company]
        
        if placed_companies:
            final_status = f"Placed at {', '.join(placed_companies)}"
        elif any(r.first_round or r.second_round or r.attended_interview for r in records):
            final_status = "Interviewing"
        else:
            final_status = "Registered"

        students_summary.append({
            'id': cand['primary_id'],
            'name': cand['name'],
            'email': cand['email'],
            'contact': cand['contact'],
            'all_companies': company_names,
            'placed_companies': placed_companies,
            'total_interviews': total_interviews,
            'total_companies_placed': len(placed_companies),
            'final_status': final_status,
            'is_db': True,
        })

    # Add Excel records if any
    if excel_students:
        for rec in excel_students:
            s_name = str(rec.get('shortlisted_candidate_name', '')).strip()
            if not s_name:
                continue
            if search_query and search_query.lower() not in s_name.lower():
                continue
            c_name = str(rec.get('company', '')).strip().upper()
            if selected_company and selected_company != 'ALL' and selected_company.upper() != c_name:
                continue
            is_placed = bool(rec.get('final_round', False))
            status = f"Placed at {c_name}" if is_placed else "Registered"
            students_summary.append({
                'id': rec.get('id', 0),
                'name': s_name,
                'email': str(rec.get('email_id', '')),
                'contact': str(rec.get('contact_number', '')),
                'all_companies': [c_name] if c_name else [],
                'placed_companies': [c_name] if is_placed and c_name else [],
                'total_interviews': 1 if rec.get('attended_interview') else 0,
                'total_companies_placed': 1 if is_placed else 0,
                'final_status': status,
                'is_db': False,
            })

    context = {
        'companies': companies,
        'students': students_summary,
        'selected_company': selected_company,
        'search_query': search_query,
    }
    return render(request, 'Assets/all_placements.html', context)


@login_required
@faculty_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Candidate interview record successfully saved to Placement Directory!")
            return redirect('placements')
    else:
        form = StudentForm()

    existing_candidates = list(Student.objects.values('shortlisted_candidate_name', 'email_id', 'contact_number', 'highest_qualification', 'course_undergone_in_learnmore_technologies', 'pass_out_year', 'graduating_percentage').distinct())
    
    return render(request, 'Assets/add_student.html', {
        'form': form,
        'existing_candidates': existing_candidates,
    })


@login_required
@faculty_required
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Candidate '{student.shortlisted_candidate_name}' updated successfully!")
            return redirect('placements')
    else:
        form = StudentForm(instance=student)
    return render(request, 'Assets/add_student.html', {'form': form, 'is_edit': True, 'student': student})


@login_required
@faculty_required
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.shortlisted_candidate_name or f"Candidate #{student.id}"
        student.delete()
        messages.success(request, f"Candidate '{name}' removed from Placement Directory.")
        return redirect('placements')
    return render(request, 'Assets/delete_student_confirm.html', {'student': student})


@login_required
@faculty_required
def manage_companies(request):
    if request.method == 'POST':
        company_name = request.POST.get('name', '').strip().upper()
        if company_name:
            company, created = Company.objects.get_or_create(name=company_name)
            if created:
                messages.success(request, f"Company '{company_name}' successfully added to directory!")
            else:
                messages.error(request, f"Company '{company_name}' already exists.")
            return redirect('manage_companies')

    companies = Company.objects.all().order_by('name')
    return render(request, 'Assets/manage_companies.html', {'companies': companies})


@login_required
@faculty_required
def delete_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        c_name = company.name
        company.delete()
        messages.success(request, f"Company '{c_name}' removed from directory.")
        return redirect('manage_companies')
    return redirect('manage_companies')


@login_required
@faculty_required
def manage_portals(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        url = request.POST.get('url', '').strip()
        description = request.POST.get('description', '').strip()

        if title and url:
            PortalLink.objects.create(title=title, url=url, description=description)
            messages.success(request, f"Portal link '{title}' added successfully!")
            return redirect('manage_portals')

    portals = PortalLink.objects.all().order_by('id')
    return render(request, 'Assets/manage_portals.html', {'portals': portals})


@login_required
@faculty_required
def delete_portal(request, pk):
    portal = get_object_or_404(PortalLink, pk=pk)
    if request.method == 'POST':
        t_name = portal.title
        portal.delete()
        messages.success(request, f"Portal '{t_name}' removed.")
        return redirect('manage_portals')
    return redirect('manage_portals')


@login_required
@faculty_required
def manage_events(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')

        if title:
            CompanyEvent.objects.create(
                title=title,
                description=description,
                image=image
            )
            messages.success(request, f"Company Event '{title}' successfully published!")
            return redirect('manage_events')

    events = CompanyEvent.objects.all().order_by('-created_at')
    return render(request, 'Assets/manage_events.html', {'events': events})


@login_required
@faculty_required
def delete_event(request, pk):
    event = get_object_or_404(CompanyEvent, pk=pk)
    if request.method == 'POST':
        e_title = event.title
        event.delete()
        messages.success(request, f"Event '{e_title}' removed.")
        return redirect('manage_events')
    return redirect('manage_events')


@login_required
def student_events(request):
    events = CompanyEvent.objects.all().order_by('-created_at')
    return render(request, 'Assets/student_events.html', {'events': events})


@login_required
def placement_detail(request, student_id):
    # Check DB first
    db_student = Student.objects.filter(id=student_id).first()
    if db_student:
        all_records = Student.objects.filter(email_id__iexact=db_student.email_id).select_related('company')
        placed_companies = [r.company.name for r in all_records if r.final_round and r.company]
        total_interviews = sum(1 for r in all_records if r.attended_interview)

        context = {
            'student_records': all_records,
            'student_name': db_student.shortlisted_candidate_name,
            'email_id': db_student.email_id,
            'contact_number': db_student.contact_number,
            'student_id': db_student.id,
            'total_interviews': total_interviews,
            'placed_companies': placed_companies,
            'is_db': True,
        }
        return render(request, 'Assets/placement_detail.html', context)

    # Fallback to Excel if present
    if os.path.exists(EXCEL_FILE_PATH):
        try:
            df = pd.read_excel(EXCEL_FILE_PATH)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            df.rename(columns={'highest_qualificati_on': 'highest_qualification'}, inplace=True)
            df['company'] = df['company'].astype(str).str.strip().str.upper()
            df = df.fillna('')
            if 'id' not in df.columns:
                df['id'] = df.index + 1

            student_record = df[df['id'] == int(student_id)]
            if not student_record.empty:
                student = student_record.iloc[0]
                email = student['email_id']
                contact = student['contact_number']
                all_records = df[(df['email_id'] == email) & (df['contact_number'] == contact)]
                context = {
                    'student_records': all_records.to_dict(orient='records'),
                    'student_name': student['shortlisted_candidate_name'],
                    'email_id': email,
                    'contact_number': contact,
                    'is_db': False,
                }
                return render(request, 'Assets/placement_detail.html', context)
        except Exception:
            pass

    return HttpResponse("Candidate record not found", status=404)


@login_required
@faculty_required
def upload_students(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            df = pd.read_excel(request.FILES['file'])
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            for _, row in df.iterrows():
                company_name = row.get('company', '').strip()
                company, _ = Company.objects.get_or_create(name=company_name)
                Student.objects.create(
                    shortlisted_candidate_name=row.get('shortlisted_candidate_name', ''),
                    contact_number=row.get('contact_number', ''),
                    email_id=row.get('email_id', ''),
                    highest_qualification=row.get('highest_qualification', ''),
                    graduating_percentage=row.get('graduating_percentage', None),
                    pass_out_year=row.get('pass_out_year', None),
                    course_undergone_in_learnmore_technologies=row.get('course_undergone_in_learnmore_technologies', ''),
                    attended_interview=row.get('attended_interview', False),
                    first_round=row.get('first_round', False),
                    second_round=row.get('second_round', False),
                    final_round=row.get('final_round', False),
                    company=company,
                )
            return redirect('placements')
    else:
        form = ExcelUploadForm()
    return render(request, 'Assets/upload.html', {'form': form})


@login_required
@faculty_required
def download_students(request):
    company_name = request.GET.get('company')
    if not company_name:
        return redirect('placements')

    company_name = company_name.upper()
    students = Student.objects.filter(company__name__iexact=company_name)
    if students.exists():
        df = pd.DataFrame(list(students.values(
            'shortlisted_candidate_name', 'contact_number', 'email_id',
            'highest_qualification', 'graduating_percentage', 'pass_out_year',
            'course_undergone_in_learnmore_technologies', 'attended_interview',
            'first_round', 'second_round', 'final_round', 'company__name'
        )))
        df.rename(columns={'company__name': 'company'}, inplace=True)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename={company_name}_students.xlsx'
        df.to_excel(response, index=False)
        return response

    return redirect('placements')


@login_required
def it_courses(request):
    return render(request, 'it_courses.html')


@login_required
def business(request):
    return render(request, 'business.html')


@login_required
def management(request):
    return render(request, 'management.html')


@login_required
def personal(request):
    return render(request, 'personal.html')


@login_required
def teaching(request):
    return render(request, 'teaching.html')


@login_required
def expense_tracker(request):
    user_role = request.user.profile.role.lower() if (hasattr(request.user, 'profile') and request.user.profile.role) else ''
    is_admin = request.user.is_superuser or (user_role == 'admin')
    success = False
    if request.method == 'POST':
        form = ExpenseForm(request.POST, initial_user=request.user, is_admin=is_admin)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.name = form.cleaned_data['name']
            target_u = User.objects.filter(username__iexact=exp.name).first()
            exp.created_by = target_u or request.user
            if is_admin:
                exp.approval_status = 'APPROVED'
            else:
                exp.approval_status = 'PENDING'
            exp.save()
            success = True
            form = ExpenseForm(initial={'name': request.user.username}, initial_user=request.user, is_admin=is_admin)
    else:
        form = ExpenseForm(initial={'name': request.user.username}, initial_user=request.user, is_admin=is_admin)

    return render(request, 'Assets/expense_tracker.html', {
        'form': form,
        'success': success,
    })


@login_required
@faculty_required
def approve_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.approval_status = 'APPROVED'
        expense.save()
        messages.success(request, f"Expense '{expense.item}' for ₹{expense.amount} has been APPROVED.")
    return redirect('expense_registered')


@login_required
@faculty_required
def reject_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.approval_status = 'REJECTED'
        expense.save()
        messages.warning(request, f"Expense '{expense.item}' for ₹{expense.amount} has been REJECTED.")
    return redirect('expense_registered')


@login_required
def expense_registered(request):
    user_role = request.user.profile.role.lower() if (hasattr(request.user, 'profile') and request.user.profile.role) else ''
    is_admin = request.user.is_superuser or (user_role == 'admin')
    if is_admin:
        expenses = Expense.objects.all().order_by('-date', '-time')
    else:
        expenses = Expense.objects.filter(created_by=request.user).order_by('-date', '-time')
    return render(request, 'Assets/expense_registered.html', {'expenses': expenses, 'is_admin': is_admin})


@login_required
@faculty_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_registered')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'Assets/expense_update.html', {'form': form, 'expense': expense})


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'



@login_required
def faculty_login(request):
    if request.method == 'POST':
        form = FacultyLoginForm(request.POST)
        if form.is_valid():
            pin = form.cleaned_data['pin_code']
            if pin == getattr(settings, "FACULTY_PIN", "1234"):
                request.session['is_faculty'] = True
                if is_ajax(request):
                    return JsonResponse({'success': True})
                messages.success(request, "Faculty access granted")
                return redirect('home')
            else:
                if is_ajax(request):
                    return JsonResponse({'success': False, 'error': 'Invalid PIN'}, status=400)
                messages.error(request, "Invalid PIN")
    else:
        form = FacultyLoginForm()
    if is_ajax(request):
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    return render(request, 'Assets/faculty_login.html', {'form': form})




@login_required
def home(request):
    form = FacultyLoginForm()
    return render(request, 'Assets/home.html', {'form': form})




# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.decorators import login_required
# from django.http import HttpResponse
# from .forms import AssetForm, ExcelUploadForm
# from .models import Asset, Company, Student
# import pandas as pd
# import os

# EXCEL_PATH = r"C:\Users\abhis\Downloads\Learnmore placemnet Student Data.xlsx"

# @login_required
# def index(request):
#     if request.user.is_authenticated:
#         return redirect('home')
#     else:
#         return redirect('login')


# def register(request):
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect('login')
#     else:
#         form = UserCreationForm()
#     return render(request, 'Assets/register.html', {'form': form})


# @login_required
# def home(request):
#     return render(request, 'Assets/home.html')


# @login_required
# def add_asset(request, asset_type):
#     if request.method == 'POST':
#         form = AssetForm(request.POST, request.FILES)
#         if form.is_valid():
#             asset = form.save(commit=False)
#             asset.asset_type = asset_type
#             asset.save()
#             return redirect('registered_assets')
#     else:
#         form = AssetForm()
#     return render(request, 'Assets/add_asset.html', {'form': form, 'asset_type': asset_type})


# @login_required
# def registered_assets(request):
#     assets = Asset.objects.all()
#     return render(request, 'Assets/registered_assets.html', {'assets': assets})


# @login_required
# def edit_asset(request, pk):
#     asset = get_object_or_404(Asset, pk=pk)
#     if request.method == 'POST':
#         form = AssetForm(request.POST, request.FILES, instance=asset)
#         if form.is_valid():
#             form.save()
#             return redirect('registered_assets')
#     else:
#         form = AssetForm(instance=asset)
#     return render(request, 'Assets/add_asset.html', {'form': form, 'asset_type': asset.asset_type})


# @login_required
# def delete_asset(request, pk):
#     asset = get_object_or_404(Asset, pk=pk)
#     if request.method == 'POST':
#         asset.delete()
#         return redirect('registered_assets')
#     return render(request, 'Assets/delete_confirm.html', {'asset': asset})


# @login_required
# def placements(request):
#     selected_company = request.GET.get('company', 'DITOZ SOLUTIONS PVT LTD')
#     companies, students = [], []

#     if os.path.exists(EXCEL_PATH):
#         try:
#             df = pd.read_excel(EXCEL_PATH, engine='openpyxl', header=1)
#             df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

#             # Normalize company values and get the list for dropdown/filtering
#             if 'company' in df.columns:
#                 df['company'] = df['company'].astype(str).str.strip().str.upper()
#                 companies = df['company'].dropna().unique().tolist()
#             elif 'company_name' in df.columns:
#                 df['company_name'] = df['company_name'].astype(str).str.strip().str.upper()
#                 df['company'] = df['company_name']
#                 companies = df['company_name'].dropna().unique().tolist()
#             else:
#                 df['company'] = ''

#             companies = [str(c) for c in companies]

#             filter_company = selected_company.strip().upper()
#             filtered_df = df[df['company'] == filter_company]

#             columns = [
#                 'shortlisted_candidate_name',
#                 'contact_number',
#                 'email_id',
#                 'highest_alification',           # Keep typo as per Excel
#                 'graduation_percentacge',        # Keep typo as per Excel
#                 'passes_out_year',
#                 'course_undergone_in_learnmore_technologies',
#                 'attended_interview',
#                 'first_round',
#                 'second_round',
#                 'final_round',
#                 'company'  # Include company column for display
#             ]

#             existing_columns = [col for col in columns if col in filtered_df.columns]
#             students = filtered_df[existing_columns].to_dict(orient='records')

#         except Exception as e:
#             print(f"Error reading/filtering Excel file: {e}")

#     return render(request, 'Assets/all_placements.html', {
#         'students': students,
#         'selected_company': selected_company,
#         'companies': companies,
#     })


# @login_required
# def upload_students(request):
#     if request.method == 'POST':
#         form = ExcelUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             df = pd.read_excel(request.FILES['file'], engine='openpyxl', header=1)
#             df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
#             for _, row in df.iterrows():
#                 company_name = row.get('company') or row.get('company_name') or ''
#                 company_obj, _ = Company.objects.get_or_create(name=company_name)
#                 Student.objects.create(
#                     shortlisted_candidate_name=row.get('shortlisted_candidate_name', ''),
#                     contact_number=row.get('contact_number', ''),
#                     email_id=row.get('email_id', ''),
#                     highest_qualification=row.get('highest_alification', ''),
#                     graduating_percentage=row.get('graduation_percentacge'),
#                     pass_out_year=row.get('passes_out_year'),
#                     course_undergone_in_learnmore_technologies=row.get('course_undergone_in_learnmore_technologies', ''),
#                     attended_interview=row.get('attended_interview', False),
#                     first_round=row.get('first_round', False),
#                     second_round=row.get('second_round', False),
#                     final_round=row.get('final_round', False),
#                     company=company_obj
#                 )
#             return redirect('assets:placements')
#     else:
#         form = ExcelUploadForm()
#     return render(request, 'Assets/upload.html', {'form': form})


# @login_required
# def download_students(request):
#     company_name = request.GET.get('company', 'DITOZ SOLUTIONS PVT LTD')
#     if not os.path.exists(EXCEL_PATH):
#         return redirect('assets:placements')
#     try:
#         df = pd.read_excel(EXCEL_PATH, engine='openpyxl', header=1)
#         df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
#         df['company'] = df['company'].astype(str).str.strip().str.upper()
#         company_filter = company_name.strip().upper()
#         company_df = df[df['company'] == company_filter] if 'company' in df.columns else df
#     except Exception as e:
#         print(f"Error downloading Excel: {e}")
#         return redirect('assets:placements')

#     response = HttpResponse(
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = f'attachment; filename="{company_name}_students.xlsx"'
#     company_df.to_excel(response, index=False)
#     return response


# @login_required
# def update_student_excel(request, student_id):
#     if request.method == 'POST':
#         try:
#             df = pd.read_excel(EXCEL_PATH, engine='openpyxl', header=1)
#             df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
#             if 'id' in df.columns:
#                 idx = df[df['id'] == student_id].index[0]
#                 for field in request.POST:
#                     if field in df.columns:
#                         df.at[idx, field] = request.POST[field]
#                 df.to_excel(EXCEL_PATH, index=False)
#         except Exception as e:
#             print(f"Error updating Excel file: {e}")
#         return redirect('assets:placements')
#     else:
#         pass


@faculty_required
def admin_dashboard(request):
    total_students = Student.objects.count()
    total_companies = Company.objects.count()
    total_assets = Asset.objects.count()
    total_expenses = Expense.objects.count()
    total_expense_amount = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    pending_expenses_count = Expense.objects.filter(approval_status='PENDING').count()
    total_events = CompanyEvent.objects.count()
    total_portals = PortalLink.objects.count()
    
    recent_students = Student.objects.all().order_by('-id')[:5]
    recent_events = CompanyEvent.objects.all().order_by('-created_at')[:5]
    recent_expenses = Expense.objects.all().order_by('-id')[:5]

    return render(request, 'Assets/admin_dashboard.html', {
        'total_students': total_students,
        'total_companies': total_companies,
        'total_assets': total_assets,
        'total_expenses': total_expenses,
        'total_expense_amount': total_expense_amount,
        'pending_expenses_count': pending_expenses_count,
        'total_events': total_events,
        'total_portals': total_portals,
        'recent_students': recent_students,
        'recent_events': recent_events,
        'recent_expenses': recent_expenses,
    })


@login_required
@faculty_required
def manage_users(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role', '').strip()
        new_dept = request.POST.get('department', '').strip()
        new_emp_id = request.POST.get('employee_id', '').strip()

        if user_id and new_role:
            u = get_object_or_404(User, id=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=u)
            profile.role = new_role
            if new_dept:
                profile.department = new_dept
            if new_emp_id:
                profile.employee_id = new_emp_id
            profile.save()
            messages.success(request, f"User '{u.username}' role updated to {profile.role}")
            return redirect('manage_users')

    users = User.objects.all().order_by('-id')
    roles = CustomRole.objects.all().order_by('name')
    for u in users:
        if not hasattr(u, 'profile'):
            role = 'Admin' if (u.is_superuser or u.username == 'admin') else 'Intern'
            UserProfile.objects.create(user=u, role=role)

    return render(request, 'Assets/manage_users.html', {'users': users, 'roles': roles})


@login_required
@faculty_required
def create_user_account(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'Intern').strip()
        department = request.POST.get('department', '').strip()
        employee_id = request.POST.get('employee_id', '').strip()

        if username and password:
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' is already taken.")
            else:
                user = User.objects.create_user(username=username, password=password)
                UserProfile.objects.create(
                    user=user,
                    role=role,
                    department=department,
                    employee_id=employee_id
                )
                messages.success(request, f"Employee Account '{username}' ({role}) created successfully!")
                return redirect('manage_users')
        else:
            messages.error(request, "Username and Password are required.")

    roles = CustomRole.objects.all().order_by('name')
    return render(request, 'Assets/create_user.html', {'roles': roles})


@login_required
@faculty_required
def delete_user_account(request, pk):
    u = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        u_name = u.username
        if u.is_superuser or u.username == 'admin':
            messages.error(request, "Primary Admin account cannot be deleted.")
        else:
            u.delete()
            messages.success(request, f"User account '{u_name}' deleted.")
        return redirect('manage_users')
    return redirect('manage_users')


@login_required
@faculty_required
def manage_roles(request):
    if request.method == 'POST':
        role_name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if role_name:
            cr, created = CustomRole.objects.get_or_create(name=role_name)
            if created:
                cr.description = description
                cr.save()
                messages.success(request, f"New Role '{role_name}' created successfully!")
            else:
                messages.error(request, f"Role '{role_name}' already exists.")
            return redirect('manage_roles')

    roles = CustomRole.objects.all().order_by('name')
    return render(request, 'Assets/manage_roles.html', {'roles': roles})


@login_required
@faculty_required
def delete_role(request, pk):
    role = get_object_or_404(CustomRole, pk=pk)
    if request.method == 'POST':
        r_name = role.name
        role.delete()
        messages.success(request, f"Role '{r_name}' removed.")
        return redirect('manage_roles')
    return redirect('manage_roles')


@csrf_exempt
def upload_call_recording_api(request):
    """
    REST API endpoint for Android Call Recorder App.
    Accepts POST request with multipart/form-data:
    - telecaller_username / telecaller
    - phone_number
    - candidate_name (optional)
    - call_type (OUTGOING / INCOMING / MISSED)
    - duration_seconds / duration
    - audio_file (.m4a / .mp3 / .wav)
    - notes (optional)
    """
    if request.method == 'POST':
        telecaller_username = request.POST.get('telecaller_username') or request.POST.get('telecaller') or 'Mobile Telecaller'
        phone_number = request.POST.get('phone_number') or request.POST.get('phone') or 'Unknown'
        candidate_name = request.POST.get('candidate_name') or request.POST.get('candidate') or ''
        call_type = (request.POST.get('call_type') or 'OUTGOING').upper()
        
        try:
            duration_seconds = int(request.POST.get('duration_seconds') or request.POST.get('duration') or 0)
        except ValueError:
            duration_seconds = 0
            
        notes = request.POST.get('notes', '')
        audio_file = request.FILES.get('audio_file') or request.FILES.get('file')

        if not audio_file:
            return JsonResponse({'status': 'error', 'message': 'No audio file uploaded'}, status=400)

        # Resolve telecaller user if exists
        telecaller_user = User.objects.filter(username__iexact=telecaller_username).first()

        # Try to resolve candidate name if missing
        if not candidate_name and phone_number:
            clean_num = phone_number.replace(' ', '').replace('-', '').replace('+91', '')
            stu = Student.objects.filter(contact_number__icontains=clean_num).first()
            if stu:
                candidate_name = stu.shortlisted_candidate_name

        recording = CallRecording.objects.create(
            telecaller=telecaller_user,
            telecaller_name=telecaller_username,
            candidate_name=candidate_name or 'Candidate',
            phone_number=phone_number,
            call_type=call_type if call_type in ['OUTGOING', 'INCOMING', 'MISSED'] else 'OUTGOING',
            duration_seconds=duration_seconds,
            audio_file=audio_file,
            notes=notes
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Call recording uploaded successfully',
            'recording_id': recording.id,
            'file_url': recording.audio_file.url
        })
    
    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)


@login_required
def call_recordings_hub(request):
    user_role = request.user.profile.role.lower() if (hasattr(request.user, 'profile') and request.user.profile.role) else ''
    is_admin = request.user.is_superuser or request.session.get('is_faculty') or (user_role == 'admin')
    
    # Non-admin users see only their own recordings
    if is_admin:
        recordings_qs = CallRecording.objects.all().order_by('-id')
    else:
        recordings_qs = CallRecording.objects.filter(telecaller=request.user).order_by('-id')

    # Search & Filter
    search_q = request.GET.get('q', '').strip()
    telecaller_filter = request.GET.get('telecaller', '').strip()

    if search_q:
        recordings_qs = recordings_qs.filter(
            Q(phone_number__icontains=search_q) |
            Q(candidate_name__icontains=search_q) |
            Q(telecaller_name__icontains=search_q)
        )
    
    if telecaller_filter:
        recordings_qs = recordings_qs.filter(telecaller_name__iexact=telecaller_filter)

    # Statistics
    total_recordings = recordings_qs.count()
    total_seconds = recordings_qs.aggregate(total=Sum('duration_seconds'))['total'] or 0
    total_minutes = round(total_seconds / 60, 1)
    
    # Active telecallers list for filter dropdown
    active_telecallers = CallRecording.objects.values_list('telecaller_name', flat=True).distinct()

    return render(request, 'Assets/call_recordings.html', {
        'recordings': recordings_qs,
        'total_recordings': total_recordings,
        'total_minutes': total_minutes,
        'active_telecallers': active_telecallers,
        'is_admin': is_admin,
        'search_q': search_q,
        'telecaller_filter': telecaller_filter,
    })


@login_required
def delete_call_recording(request, pk):
    recording = get_object_or_404(CallRecording, pk=pk)
    if request.method == 'POST':
        if recording.audio_file and os.path.exists(recording.audio_file.path):
            try:
                os.remove(recording.audio_file.path)
            except OSError:
                pass
        recording.delete()
        messages.success(request, "Call recording entry deleted successfully.")
    return redirect('call_recordings_hub')
