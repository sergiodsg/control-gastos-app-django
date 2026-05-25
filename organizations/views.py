from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Organization, OrganizationAccess, Transaction, Category, Account, Project, Valuation
from .forms import TransactionForm, CategoryForm, AccountForm, ProjectForm, ValuationForm
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import urllib.request
import json
from django.db import models
from django.core.paginator import Paginator
from decimal import Decimal
from django.core.cache import cache

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@login_required
def dashboard(request):
    accesses = OrganizationAccess.objects.filter(user=request.user)
    organizations = [access.organization for access in accesses]
    return render(request, 'organizations/dashboard.html', {
        'organizations': organizations,
        'hide_sidebar': True
    })

@login_required
def seleccionar_organizacion(request, org_id):
    get_object_or_404(OrganizationAccess, user=request.user, organization_id=org_id)
    org = get_object_or_404(Organization, id=org_id)
    request.session['org_id'] = org.id
    request.session['org_name'] = org.name
    return redirect('home_organizacion')

def get_filtered_totals_both(org_id, filter_type):
    now = timezone.now()
    transactions = Transaction.objects.filter(organization_id=org_id)
    
    if filter_type == 'day':
        start_date = now - timedelta(days=1)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == 'week':
        start_date = now - timedelta(weeks=1)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == '15days':
        start_date = now - timedelta(days=15)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == 'month':
        start_date = now - timedelta(days=30)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == '3months':
        start_date = now - timedelta(days=90)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == '6months':
        start_date = now - timedelta(days=180)
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == 'year':
        start_date = now - timedelta(days=365)
        transactions = transactions.filter(date__gte=start_date)

    res = transactions.aggregate(
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0))
    )
    
    return {
        'income_usd': res['income_usd'] or 0,
        'expense_usd': abs(res['expense_usd'] or 0),
        'income_bs': res['income_bs'] or 0,
        'expense_bs': abs(res['expense_bs'] or 0),
    }

def fetch_api_rate(url):
    cache_key = f'rate_api_{url}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            cache.set(cache_key, data, 3600)  # Cache por 1 hora
            return data
    except Exception:
        return None

def get_bcv_rate():
    rate = cache.get('bcv_rate_val')
    if rate:
        return rate
        
    dolares_data = fetch_api_rate('https://ve.dolarapi.com/v1/dolares')
    if dolares_data:
        for item in dolares_data:
            if item.get('fuente', '').lower() == 'oficial':
                val = item.get('promedio', 1)
                cache.set('bcv_rate_val', val, 3600)
                return val
    return 1

@login_required
def home_organizacion(request):

    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    totals = Transaction.objects.filter(organization_id=org_id).aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs')
    )
    
    income_filter = request.GET.get('income_filter', 'all')
    expense_filter = request.GET.get('expense_filter', 'all')
    
    # Si los filtros son iguales, evitar doble consulta
    inc_totals = get_filtered_totals_both(org_id, income_filter)
    if income_filter == expense_filter:
        exp_totals = inc_totals
    else:
        exp_totals = get_filtered_totals_both(org_id, expense_filter)
    
    # Cache para listas completas de tasas
    dolares_data = fetch_api_rate('https://ve.dolarapi.com/v1/dolares')
    euros_data = fetch_api_rate('https://ve.dolarapi.com/v1/euros')
    
    rates = {
        'usd_bcv': None,
        'usd_paralelo': None,
        'eur_bcv': None,
        'eur_paralelo': None,
    }
    
    def find_rate(data, fuente_slug):
        if not isinstance(data, list): return None
        for item in data:
            if item.get('fuente', '').lower() == fuente_slug:
                return item
        return None

    if dolares_data:
        rates['usd_bcv'] = find_rate(dolares_data, 'oficial')
        rates['usd_paralelo'] = find_rate(dolares_data, 'paralelo')
    
    if euros_data:
        rates['eur_bcv'] = find_rate(euros_data, 'oficial')
        rates['eur_paralelo'] = find_rate(euros_data, 'paralelo')
    
    recent_transactions = Transaction.objects.filter(organization_id=org_id).order_by('-date', '-id')[:10]
    
    context = {
        'balance_usd': totals['balance_usd'] or 0,
        'balance_bs': totals['balance_bs'] or 0,
        'income_usd': inc_totals['income_usd'],
        'income_bs': inc_totals['income_bs'],
        'expense_usd': exp_totals['expense_usd'],
        'expense_bs': exp_totals['expense_bs'],
        'income_filter': income_filter,
        'expense_filter': expense_filter,
        'rates': rates,
        'recent_transactions': recent_transactions,
        'now_ve': timezone.now(),
        'filter_options': [
            ('day', 'Último día'),
            ('week', 'Última semana'),
            ('15days', 'Últimos 15 días'),
            ('month', 'Último mes'),
            ('3months', 'Últimos 3 meses'),
            ('6months', 'Últimos 6 meses'),
            ('year', 'Último año'),
            ('all', 'Desde el principio'),
        ]
    }
    
    return render(request, 'organizations/home.html', context)

@login_required
def configuracion(request):
    if not request.session.get('org_id'):
        return redirect('dashboard')
    return render(request, 'organizations/configuracion.html')

@login_required
def salir_organizacion(request):
    if 'org_id' in request.session: del request.session['org_id']
    if 'org_name' in request.session: del request.session['org_name']
    return redirect('dashboard')

@login_required
def crear_organizacion(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            org = Organization.objects.create(name=nombre)
            OrganizationAccess.objects.create(user=request.user, organization=org)
            messages.success(request, f"Organización '{nombre}' creada con éxito.")
            return redirect('dashboard')
        else:
            messages.error(request, "El nombre de la organización es obligatorio.")
    return render(request, 'organizations/crear.html', {'hide_sidebar': True})

# --- Transacciones ---

from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse

@login_required
def lista_transacciones(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    
    # --- Lógica de Filtrado ---
    filter_type = request.GET.get('filter_type', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')

    # Sanitizar valores 'None' que pueden venir de la URL
    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if category_id == 'None' or category_id == '': category_id = None
    
    transactions_list = Transaction.objects.filter(organization=org)
    
    if category_id:
        transactions_list = transactions_list.filter(category_id=category_id)
    
    today = timezone.localdate()
    
    if filter_type != 'all' and filter_type != 'custom':
        if filter_type == 'day':
            start_date = today
        elif filter_type == 'week':
            start_date = today - timedelta(days=7)
        elif filter_type == '15days':
            start_date = today - timedelta(days=15)
        elif filter_type == 'month':
            start_date = today - timedelta(days=30)
        elif filter_type == 'quarter':
            start_date = today - timedelta(days=90)
        elif filter_type == '6months':
            start_date = today - timedelta(days=180)
        elif filter_type == 'year':
            start_date = today - timedelta(days=365)
        transactions_list = transactions_list.filter(date__gte=start_date)
    elif filter_type == 'custom' and date_from and date_to:
        transactions_list = transactions_list.filter(date__range=[date_from, date_to])
        
    transactions_list = transactions_list.order_by('-date', '-id')
    
    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    form = TransactionForm(organization=org)

    # Mapeo de proyectos a valuaciones para filtrado dinámico en JS
    projects_data = {}
    projects = Project.objects.filter(organization=org)
    for p in projects:
        projects_data[p.id] = list(Valuation.objects.filter(project=p).values('id', 'name', 'amount_usd'))

    bcv_rate = get_bcv_rate()
    categories = Category.objects.filter(organization=org)

    return render(request, 'organizations/transacciones.html', {
        'page_obj': page_obj,
        'form': form,
        'bcv_rate': bcv_rate,
        'categories': categories,
        'selected_category': category_id,
        'projects_data': json.dumps(projects_data, cls=DecimalEncoder),
        'filter_type': filter_type,
        'date_from': date_from,
        'date_to': date_to,
        'filter_options': [
            ('day', 'Último día'),
            ('week', 'Última semana'),
            ('15days', 'Últimos 15 días'),
            ('month', 'Último mes'),
            ('quarter', 'Trimestre'),
            ('6months', '6 meses'),
            ('year', 'Último año'),
            ('custom', 'Rango personalizado'),
            ('all', 'Todas'),
        ]
    })

@login_required
def exportar_pdf_transacciones(request):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    
    filter_type = request.GET.get('filter_type', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')

    # Sanitizar valores 'None' que pueden venir de la URL
    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if category_id == 'None' or category_id == '': category_id = None
    
    transactions = Transaction.objects.filter(organization=org)
    
    if category_id:
        transactions = transactions.filter(category_id=category_id)
    
    today = timezone.localdate()
    now = timezone.now()
    filter_label = "Todas"
    
    if category_id:
        category = Category.objects.filter(id=category_id).first()
        if category:
            filter_label += f" | Categoría: {category.name}"
    
    if filter_type != 'all' and filter_type != 'custom':
        if filter_type == 'day':
            start_date = today
            filter_label = "Hoy"
        elif filter_type == 'week':
            start_date = today - timedelta(days=7)
            filter_label = "Última semana"
        elif filter_type == '15days':
            start_date = today - timedelta(days=15)
            filter_label = "Últimos 15 días"
        elif filter_type == 'month':
            start_date = today - timedelta(days=30)
            filter_label = "Último mes"
        elif filter_type == 'quarter':
            start_date = today - timedelta(days=90)
            filter_label = "Trimestre"
        elif filter_type == '6months':
            start_date = today - timedelta(days=180)
            filter_label = "Últimos 6 meses"
        elif filter_type == 'year':
            start_date = today - timedelta(days=365)
            filter_label = "Último año"
        transactions = transactions.filter(date__gte=start_date)
    elif filter_type == 'custom' and date_from and date_to:
        transactions = transactions.filter(date__range=[date_from, date_to])
        filter_label = f"Rango: {date_from} a {date_to}"
        
    transactions = transactions.order_by('date', 'id')
    
    # Calcular totales del reporte
    report_totals = transactions.aggregate(
        total_usd=Sum('amount_usd'),
        total_bs=Sum('amount_bs')
    )
    
    template = get_template('organizations/reportes/transacciones_pdf.html')
    context = {
        'transactions': transactions,
        'org': org,
        'filter_label': filter_label,
        'now': now,
        'report_totals': {
            'usd': report_totals['total_usd'] or 0,
            'bs': report_totals['total_bs'] or 0,
        }
    }
    
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"balance_general_{org.name}_{now.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error al generar PDF", status=500)


@login_required
def guardar_transaccion(request, trans_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if trans_id:
        instance = get_object_or_404(Transaction, id=trans_id, organization=org)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=instance, organization=org)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.organization = org
            transaction.save()
            messages.success(request, "Transacción guardada correctamente.")
        else:
            messages.error(request, "Error al guardar la transacción. Verifique los datos.")
    
    return redirect('lista_transacciones')

@login_required
def eliminar_transaccion(request, trans_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    transaction = get_object_or_404(Transaction, id=trans_id, organization=org)
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, "Transacción eliminada.")
    
    return redirect('lista_transacciones')

@login_required
def detalle_transaccion(request, trans_id):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    transaction = get_object_or_404(Transaction, id=trans_id, organization=org)
    return render(request, 'organizations/partials/detalle_transaccion.html', {'transaction': transaction})

# --- Categorías ---

@login_required
def lista_categorias(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    categories = Category.objects.filter(organization=org).order_by('name')
    form = CategoryForm()
    
    return render(request, 'organizations/categorias.html', {
        'categories': categories,
        'form': form,
    })

@login_required
def guardar_categoria(request, cat_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if cat_id:
        instance = get_object_or_404(Category, id=cat_id, organization=org)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=instance)
        if form.is_valid():
            category = form.save(commit=False)
            category.organization = org
            category.save()
            messages.success(request, "Categoría guardada correctamente.")
        else:
            messages.error(request, "Error al guardar la categoría.")
            
    return redirect('lista_categorias')

@login_required
def eliminar_categoria(request, cat_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    category = get_object_or_404(Category, id=cat_id, organization=org)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Categoría eliminada.")
    
    return redirect('lista_categorias')

# --- Cuentas ---

@login_required
def lista_cuentas(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    accounts = Account.objects.filter(organization=org).annotate(
        balance_usd=Sum('transactions__amount_usd'),
        balance_bs=Sum('transactions__amount_bs')
    )
    
    form = AccountForm()

    bcv_rate = get_bcv_rate()

    return render(request, 'organizations/cuentas.html', {

        'accounts': accounts,
        'form': form,
        'bcv_rate': bcv_rate,
    })

@login_required
def guardar_cuenta(request, acc_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if acc_id:
        instance = get_object_or_404(Account, id=acc_id, organization=org)
    
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=instance)
        if form.is_valid():
            account = form.save(commit=False)
            account.organization = org
            account.save()
            
            if not instance:
                usd = form.cleaned_data.get('initial_amount_usd')
                bs = form.cleaned_data.get('initial_amount_bs')
                rate = form.cleaned_data.get('daily_rate') or 1
                
                if usd or bs:
                    Transaction.objects.create(
                        organization=org,
                        account=account,
                        date=timezone.now().date(),
                        description=f"Saldo inicial: {account.name}",
                        amount_usd=usd or 0,
                        amount_bs=bs or 0,
                        daily_rate=rate,
                        status='completado'
                    )
            messages.success(request, "Cuenta guardada correctamente.")
        else:
            messages.error(request, "Error al guardar la cuenta.")
            
    return redirect('lista_cuentas')

@login_required
def eliminar_cuenta(request, acc_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    account = get_object_or_404(Account, id=acc_id, organization=org)
    
    if request.method == 'POST':
        account.delete()
        messages.success(request, "Cuenta eliminada.")
    
    return redirect('lista_cuentas')

@login_required
def detalle_cuenta(request, acc_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    account = get_object_or_404(Account, id=acc_id, organization=org)
    
    transactions_list = Transaction.objects.filter(account=account).order_by('-date', '-id')
    
    totals = transactions_list.aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs'),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0))
    )
    
    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'organizations/detalle_cuenta.html', {
        'account': account,
        'page_obj': page_obj,
        'totals': {
            'balance_usd': totals['balance_usd'] or 0,
            'balance_bs': totals['balance_bs'] or 0,
            'income_usd': totals['income_usd'] or 0,
            'expense_usd': abs(totals['expense_usd'] or 0),
            'income_bs': totals['income_bs'] or 0,
            'expense_bs': abs(totals['expense_bs'] or 0),
        }
    })

# --- Proyectos ---

@login_required
def lista_proyectos(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    projects = Project.objects.filter(organization=org).annotate(
        balance_usd=Sum('transactions__amount_usd'),
        balance_bs=Sum('transactions__amount_bs')
    )

    form = ProjectForm()

    return render(request, 'organizations/proyectos.html', {
        'projects': projects,
        'form': form,
    })

@login_required
def guardar_proyecto(request, proj_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if proj_id:
        instance = get_object_or_404(Project, id=proj_id, organization=org)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=instance)
        if form.is_valid():
            project = form.save(commit=False)
            project.organization = org
            project.save()
            messages.success(request, "Proyecto guardado correctamente.")
        else:
            messages.error(request, "Error al guardar el proyecto.")

    return redirect('lista_proyectos')

@login_required
def eliminar_proyecto(request, proj_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    project = get_object_or_404(Project, id=proj_id, organization=org)

    if request.method == 'POST':
        project.delete()
        messages.success(request, "Proyecto eliminado.")

    return redirect('lista_proyectos')

@login_required
def detalle_proyecto(request, proj_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    project = get_object_or_404(Project, id=proj_id, organization=org)

    # Anotar valuaciones con el monto cubierto por transacciones de crédito
    # Consideramos "crédito" como transacciones con monto positivo (ingresos)
    valuations = list(Valuation.objects.filter(project=project).annotate(
        covered_usd=Sum('transactions__amount_usd', filter=models.Q(transactions__amount_usd__gt=0)),
        covered_bs=Sum('transactions__amount_bs', filter=models.Q(transactions__amount_bs__gt=0))
    ))

    # Calcular porcentajes
    for val in valuations:
        val.progress = 0
        if val.amount_usd > 0:
            covered = val.covered_usd or 0
            val.progress = min(round((covered / val.amount_usd) * 100, 2), 100)

    transactions_list = Transaction.objects.filter(project=project).order_by('-date', '-id')
    
    totals = transactions_list.aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs'),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0))
    )

    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    val_form = ValuationForm()
    bcv_rate = get_bcv_rate()

    return render(request, 'organizations/detalle_proyecto.html', {
        'project': project,
        'valuations': valuations,
        'page_obj': page_obj,
        'val_form': val_form,
        'bcv_rate': bcv_rate,
        'totals': {
            'balance_usd': totals['balance_usd'] or 0,
            'balance_bs': totals['balance_bs'] or 0,
            'income_usd': totals['income_usd'] or 0,
            'expense_usd': abs(totals['expense_usd'] or 0),
        }
    })

# --- Valuaciones ---

@login_required
def guardar_valuacion(request, proj_id, val_id=None):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    project = get_object_or_404(Project, id=proj_id, organization=org)
    
    instance = None
    if val_id:
        instance = get_object_or_404(Valuation, id=val_id, project=project)

    if request.method == 'POST':
        form = ValuationForm(request.POST, instance=instance)
        if form.is_valid():
            valuation = form.save(commit=False)
            valuation.project = project
            valuation.save()
            messages.success(request, "Valuación guardada correctamente.")
        else:
            messages.error(request, "Error al guardar la valuación.")

    return redirect('detalle_proyecto', proj_id=project.id)

@login_required
def eliminar_valuacion(request, val_id):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    valuation = get_object_or_404(Valuation, id=val_id, project__organization=org)
    proj_id = valuation.project.id

    if request.method == 'POST':
        valuation.delete()
        messages.success(request, "Valuación eliminada.")

    return redirect('detalle_proyecto', proj_id=proj_id)
