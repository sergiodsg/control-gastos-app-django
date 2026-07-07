from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, OuterRef, Subquery, Value, F, Q
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import timedelta
import json
from decimal import Decimal

from .models import Organization, OrganizationAccess, Transaction, Category, Account, Project, Valuation, CostCenter
from accounts.models import Profile
from accounts.decorators import viewer_restricted
from .amounts import create_initial_balance_transaction
from .forms import TransactionForm, CategoryForm, AccountForm, ProjectForm, ValuationForm
from CashFlow.debug import debug_event, first_form_error
from BCV.services.bcv_scrapper import as_dashboard_rates, get_rate_for_date


def get_chart_data(transactions_qs, mode='bcv', json_format=True):
    # 1. Desglose de Gastos por Categoría
    if mode == 'real':
        category_spending = transactions_qs.filter(real_dollars__lt=0).values('categories__name', 'categories__color').annotate(
            total=Sum('real_dollars')
        ).order_by('total')
    else:
        category_spending = transactions_qs.filter(amount_usd__lt=0).values('categories__name', 'categories__color').annotate(
            total=Sum('amount_usd')
        ).order_by('total')
    
    cat_labels = [item['categories__name'] or 'Sin categoría' for item in category_spending]
    cat_series = [float(abs(item['total'] or 0)) for item in category_spending]
    cat_colors = [item['categories__color'] or '#000000' for item in category_spending]

    # 2. Gastos por Centro de Costo (Porcentajes)
    if mode == 'real':
        cost_center_spending = transactions_qs.filter(real_dollars__lt=0, cost_center__isnull=False).values('cost_center__name').annotate(
            total=Sum('real_dollars')
        ).order_by('total')
    else:
        cost_center_spending = transactions_qs.filter(amount_usd__lt=0, cost_center__isnull=False).values('cost_center__name').annotate(
            total=Sum('amount_usd')
        ).order_by('total')
    
    cc_labels = [item['cost_center__name'] or 'Sin centro de costo' for item in cost_center_spending]
    cc_values = [float(abs(item['total'] or 0)) for item in cost_center_spending]
    total_expense_cc = sum(cc_values)
    cc_percentages = [(v / total_expense_cc * 100) if total_expense_cc > 0 else 0 for v in cc_values]

    # 2. Balance Total (Ingresos vs Gastos)
    if mode == 'real':
        totals_data = transactions_qs.aggregate(
            income=Sum('real_dollars', filter=Q(real_dollars__gt=0)),
            expense=Sum('real_dollars', filter=Q(real_dollars__lt=0)),
            fees=Sum('bank_fee_real_usd')
        )
        total_income = float(totals_data['income'] or 0)
        total_expense = float(abs(totals_data['expense'] or 0)) + float(totals_data['fees'] or 0)
    else:
        totals_data = transactions_qs.aggregate(
            income=Sum('amount_usd', filter=Q(amount_usd__gt=0)),
            expense=Sum('amount_usd', filter=Q(amount_usd__lt=0)),
            fees=Sum('bank_fee_usd')
        )
        total_income = float(totals_data['income'] or 0)
        total_expense = float(abs(totals_data['expense'] or 0)) + float(totals_data['fees'] or 0)

    # 3. Evolución del Saldo
    if mode == 'real':
        evolution_data = transactions_qs.order_by('date').values('date').annotate(
            daily_sum=Sum(F('real_dollars') - F('bank_fee_real_usd'))
        )
    else:
        evolution_data = transactions_qs.order_by('date').values('date').annotate(
            daily_sum=Sum(F('amount_usd') - F('bank_fee_usd'))
        )
    
    evo_labels = []
    evo_series = []
    current_balance = 0
    for item in evolution_data:
        current_balance += float(item['daily_sum'] or 0)
        evo_labels.append(item['date'].strftime('%Y-%m-%d'))
        evo_series.append(round(current_balance, 2))

    if json_format:
        return {
            'cat_labels': json.dumps(cat_labels),
            'cat_series': json.dumps(cat_series),
            'cat_colors': json.dumps(cat_colors),
            'total_income': total_income,
            'total_expense': total_expense,
            'evo_labels': json.dumps(evo_labels),
            'evo_series': json.dumps(evo_series),
            'cc_labels': json.dumps(cc_labels),
            'cc_percentages': json.dumps(cc_percentages),
        }
    else:
        return {
            'cat_labels': cat_labels,
            'cat_series': cat_series,
            'cat_colors': cat_colors,
            'total_income': total_income,
            'total_expense': total_expense,
            'evo_labels': evo_labels,
            'evo_series': evo_series,
            'cc_labels': cc_labels,
            'cc_percentages': cc_percentages,
        }

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
        'hide_sidebar': True,
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
        fees_usd=Sum('bank_fee_usd'),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
        fees_bs=Sum('bank_fee_bs'),
        income_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
        expense_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
        fees_real_usd=Sum('bank_fee_real_usd')
    )

    return {
        'income_usd': res['income_usd'] or 0,
        'expense_usd': abs(res['expense_usd'] or 0) + (res['fees_usd'] or 0),
        'income_bs': res['income_bs'] or 0,
        'expense_bs': abs(res['expense_bs'] or 0) + (res['fees_bs'] or 0),
        'income_real_usd': res['income_real_usd'] or 0,
        'expense_real_usd': abs(res['expense_real_usd'] or 0) + (res['fees_real_usd'] or 0),
    }

def get_bcv_rate(target_date=None):
    try:
        rate_date = target_date or timezone.localdate()
        # Si es para hoy, usar la misma lógica que el dashboard para consistencia total
        if rate_date == timezone.localdate():
            rates = as_dashboard_rates()
            if rates.get('usd_bcv') and rates['usd_bcv'].get('promedio') is not None:
                return float(rates['usd_bcv']['promedio'])
        
        rate = get_rate_for_date(rate_date, currency="USD")
        if rate is not None:
            return float(rate)
    except Exception:
        pass
    return 1.0

@login_required
def home_organizacion(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    view_mode = request.GET.get('view_mode', 'bcv') # 'bcv' or 'real'
    
    totals = Transaction.objects.filter(organization_id=org_id).aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd'))
    )
    
    income_filter = request.GET.get('income_filter', 'all')
    expense_filter = request.GET.get('expense_filter', 'all')
    
    def get_filtered_totals_by_mode(filter_val, mode):
        transactions = Transaction.objects.filter(organization_id=org_id)
        today = timezone.localdate()
        if filter_val != 'all':
            if filter_val == 'day': start_date = today - timedelta(days=1)
            elif filter_val == 'week': start_date = today - timedelta(days=7)
            elif filter_val == '15days': start_date = today - timedelta(days=15)
            elif filter_val == 'month': start_date = today - timedelta(days=30)
            elif filter_val == '3months': start_date = today - timedelta(days=90)
            elif filter_val == '6months': start_date = today - timedelta(days=180)
            elif filter_val == 'year': start_date = today - timedelta(days=365)
            transactions = transactions.filter(date__gte=start_date)

        if mode == 'real':
            res = transactions.aggregate(
                income=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
                expense=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
                fees=Sum('bank_fee_real_usd')
            )
            return {
                'income': res['income'] or 0,
                'expense': abs(res['expense'] or 0) + (res['fees'] or 0)
            }
        else:
            res = transactions.aggregate(
                income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
                expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
                fees_usd=Sum('bank_fee_usd'),
                income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
                expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
                fees_bs=Sum('bank_fee_bs')
            )
            return {
                'income_usd': res['income_usd'] or 0,
                'expense_usd': abs(res['expense_usd'] or 0) + (res['fees_usd'] or 0),
                'income_bs': res['income_bs'] or 0,
                'expense_bs': abs(res['expense_bs'] or 0) + (res['fees_bs'] or 0),
            }

    inc_totals = get_filtered_totals_by_mode(income_filter, view_mode)
    exp_totals = get_filtered_totals_by_mode(expense_filter, view_mode)
    
    try:
        rates = as_dashboard_rates()
    except Exception:
        rates = {
            'usd_bcv': None,
            'usd_paralelo': None,
            'eur_bcv': None,
            'eur_paralelo': None,
        }
    
    sort = request.GET.get('sort', 'desc')
    recent_transactions = Transaction.objects.filter(organization_id=org_id).order_by('-date', '-id')[:10]
    
    # Filtrar chart_data por el modo seleccionado
    base_qs = Transaction.objects.filter(organization_id=org_id)
    if view_mode == 'real':
        chart_qs = base_qs.exclude(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    else:
        chart_qs = base_qs.filter(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
        
    chart_data = get_chart_data(chart_qs, mode=view_mode)
    
    context = {
        'view_mode': view_mode,
        'balance_usd': totals['balance_usd'] or 0,
        'balance_bs': totals['balance_bs'] or 0,
        'balance_real_usd': totals['balance_real_usd'] or 0,
        'income_usd': inc_totals.get('income_usd', 0),
        'income_bs': inc_totals.get('income_bs', 0),
        'income_real_usd': inc_totals.get('income', 0),
        'expense_usd': exp_totals.get('expense_usd', 0),
        'expense_bs': exp_totals.get('expense_bs', 0),
        'expense_real_usd': exp_totals.get('expense', 0),
        'income_filter': income_filter,
        'expense_filter': expense_filter,
        'rates': rates,
        'recent_transactions': recent_transactions,
        'chart_data': chart_data,
        'sort': sort,
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

from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors

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
    category_raw = request.GET.getlist('category')
    category_ids = []
    for val in category_raw:
        if ',' in val:
            category_ids.extend([v.strip() for v in val.split(',') if v.strip()])
        else:
            category_ids.append(val)
    category_ids = [cid for cid in category_ids if cid and cid != 'None' and cid != 'null']
    cost_center_id = request.GET.get('cost_center')
    search_query = request.GET.get('search', '')
    tx_filter = request.GET.get('tx_filter', 'all') # 'all', 'bcv', 'real'
    view_mode = request.GET.get('view_mode', 'bcv') # 'bcv' or 'real'
    status_filter = request.GET.get('status', '') # 'completado', 'pendiente', ''

    # Sincronización: El filtro de transacciones afecta al toggle de balance
    if tx_filter == 'real':
        view_mode = 'real'
    elif tx_filter == 'bcv':
        view_mode = 'bcv'
    # Si es 'all', se mantiene el view_mode que venga en el GET (o el default)

    # Sanitizar valores 'None' que pueden venir de la URL
    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if cost_center_id == 'None' or cost_center_id == '': cost_center_id = None
    
    # Base: TODAS las transacciones para la tabla
    transactions_list = Transaction.objects.filter(organization=org)

    # Filtrar por tipo de transacción (BCV / Real Dollars)
    if tx_filter == 'real':
        transactions_list = transactions_list.exclude(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    elif tx_filter == 'bcv':
        transactions_list = transactions_list.filter(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    
    if search_query:
        transactions_list = transactions_list.filter(
            models.Q(description__icontains=search_query) |
            models.Q(reference_number__icontains=search_query) |
            models.Q(notes__icontains=search_query) |
            models.Q(categories__name__icontains=search_query) |
            models.Q(cost_center__code__icontains=search_query) |
            models.Q(cost_center__name__icontains=search_query) |
            models.Q(account__name__icontains=search_query) |
            models.Q(project__name__icontains=search_query) |
            models.Q(valuation__name__icontains=search_query) |
            models.Q(status__icontains=search_query) |
            models.Q(amount_bs__icontains=search_query) |
            models.Q(amount_usd__icontains=search_query) |
            models.Q(real_dollars__icontains=search_query) |
            models.Q(daily_rate__icontains=search_query)
        )

    if category_ids:
        transactions_list = transactions_list.filter(categories__id__in=category_ids).distinct()

    if cost_center_id:
        transactions_list = transactions_list.filter(cost_center_id=cost_center_id)
    
    # Filtrar por estado (status)
    if status_filter:
        transactions_list = transactions_list.filter(status=status_filter)
    
    today = timezone.localdate()
    
    # Si hay fechas explícitas, ignoramos el filter_type (periodo)
    if date_from or date_to:
        if date_from:
            transactions_list = transactions_list.filter(date__gte=date_from)
        if date_to:
            transactions_list = transactions_list.filter(date__lte=date_to)
    elif filter_type != 'all' and filter_type != 'custom':
        if filter_type == 'day': start_date = today
        elif filter_type == 'week': start_date = today - timedelta(days=7)
        elif filter_type == '15days': start_date = today - timedelta(days=15)
        elif filter_type == 'month': start_date = today - timedelta(days=30)
        elif filter_type == 'quarter': start_date = today - timedelta(days=90)
        elif filter_type == '6months': start_date = today - timedelta(days=180)
        elif filter_type == 'year': start_date = today - timedelta(days=365)
        transactions_list = transactions_list.filter(date__gte=start_date)
    
    sort = request.GET.get('sort', 'desc')
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')

    # --- Calcular totales filtrados basados en view_mode para los KPIs ---
    if view_mode == 'real':
        kpi_qs = transactions_list.exclude(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
        totals = kpi_qs.aggregate(
            balance=Sum(F('real_dollars') - F('bank_fee_real_usd')),
            income=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
            expense=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
            fees=Sum('bank_fee_real_usd')
        )
        res_totals = {
            'balance_real_usd': totals['balance'] or 0,
            'income_real_usd': totals['income'] or 0,
            'expense_real_usd': abs(totals['expense'] or 0) + (totals['fees'] or 0),
        }
    else:
        kpi_qs = transactions_list.filter(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
        totals = kpi_qs.aggregate(
            balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
            balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
            income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
            income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
            expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
            expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
            fees_usd=Sum('bank_fee_usd'),
            fees_bs=Sum('bank_fee_bs')
        )
        res_totals = {
            'balance_usd': totals['balance_usd'] or 0,
            'balance_bs': totals['balance_bs'] or 0,
            'income_usd': totals['income_usd'] or 0,
            'income_bs': totals['income_bs'] or 0,
            'expense_usd': abs(totals['expense_usd'] or 0) + (totals['fees_usd'] or 0),
            'expense_bs': abs(totals['expense_bs'] or 0) + (totals['fees_bs'] or 0),
        }
    
    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    form = TransactionForm(organization=org)

    # Mapeo de proyectos a valuaciones para filtrado dinámico en JS
    projects_data = {}
    projects = Project.objects.filter(organization=org)
    for p in projects:
        projects_data[p.id] = list(Valuation.objects.filter(project=p).values('id', 'name', 'amount_usd'))

    # Mapeo de cuentas a monedas para lógica en JS
    accounts_data = {a.id: a.currency for a in Account.objects.filter(organization=org)}

    bcv_rate = get_bcv_rate()
    categories = Category.objects.filter(organization=org)

    return render(request, 'organizations/transacciones.html', {
        'page_obj': page_obj,
        'form': form,
        'bcv_rate': bcv_rate,
        'categories': categories,
        'cost_centers': CostCenter.objects.filter(organization=org),
        'selected_cost_center': cost_center_id,
        'selected_category': category_ids[0] if category_ids else '',
        'selected_categories': category_ids,
        'projects_data': json.dumps(projects_data, cls=DecimalEncoder),
        'accounts_data': json.dumps(accounts_data),
        'filter_type': filter_type,
        'date_from': date_from,
        'date_to': date_to,
        'search': search_query,
        'sort': sort,
        'view_mode': view_mode,
        'tx_filter': tx_filter,
        'status_filter': status_filter,
        'totals': res_totals,
        'tx_filter_options': [
            ('all', 'Todas las transacciones'),
            ('bcv', 'Transacciones BCV'),
            ('real', 'Transacciones Dólares Reales'),
        ],
        'status_filter_options': [
            ('', 'Todos los estados'),
            ('completado', 'Completado'),
            ('pendiente', 'Pendiente'),
        ],
        'filter_options': [
            ('day', 'Hoy'),
            ('week', 'Esta semana'),
            ('15days', 'Últimos 15 días'),
            ('month', 'Último mes'),
            ('quarter', 'Último trimestre'),
            ('6months', 'Últimos 6 meses'),
            ('year', 'Último año'),
            ('all', 'Todo el tiempo'),
            ('custom', 'Personalizado'),
        ]
    })

@login_required
def _get_report_data(request):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    
    report_type = request.GET.get('report_type', 'bcv') # 'bcv' or 'real'
    filter_type = request.GET.get('filter_type', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_raw = request.GET.getlist('category')
    category_ids = []
    for val in category_raw:
        if ',' in val:
            category_ids.extend([v.strip() for v in val.split(',') if v.strip()])
        else:
            category_ids.append(val)
    category_ids = [cid for cid in category_ids if cid and cid != 'None' and cid != 'null']
    cost_center_id = request.GET.get('cost_center')
    search_query = request.GET.get('search', '')
    account_id = request.GET.get('account')
    tx_filter = request.GET.get('tx_filter', 'all')
    project_id = request.GET.get('project')
    selected_org_id = request.GET.get('organization')
    status_filter = request.GET.get('status', '')

    # Sanitizar valores 'None' que pueden venir de la URL
    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if account_id == 'None' or account_id == '': account_id = None
    if project_id == 'None' or project_id == '': project_id = None
    if selected_org_id == 'None' or selected_org_id == '': selected_org_id = None
    if cost_center_id == 'None' or cost_center_id == '': cost_center_id = None
    
    if project_id:
        # Si filtramos por proyecto, buscamos transacciones de ese proyecto donde la org tenga acceso
        project = get_object_or_404(Project, id=project_id)
        # Verificar acceso
        is_owner = project.organization == org
        is_shared = project.shared_organizations.filter(organization=org).exists()
        if not (is_owner or is_shared):
             return org, Transaction.objects.none(), report_type, {}, "Sin Acceso"
         
        transactions = Transaction.objects.filter(project_id=project_id)
        if selected_org_id:
            transactions = transactions.filter(organization_id=selected_org_id)
    else:
        transactions = Transaction.objects.filter(organization=org)

    if account_id:
        transactions = transactions.filter(account_id=account_id)
    
    # Filtrar por tipo de reporte: BCV o Dólares Reales (Filtro base del PDF)
    if report_type == 'real':
        transactions = transactions.exclude(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    else:
        transactions = transactions.filter(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    
    # Aplicar tx_filter adicional si viene de la URL (para coincidir con la vista web)
    if tx_filter == 'real' and report_type == 'bcv':
        transactions = transactions.none()
    elif tx_filter == 'bcv' and report_type == 'real':
        transactions = transactions.none()

    if category_ids:
        transactions = transactions.filter(categories__id__in=category_ids).distinct()

    if cost_center_id:
        transactions = transactions.filter(cost_center_id=cost_center_id)
    
    # Filtrar por estado (status)
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    if search_query:
        transactions = transactions.filter(
            models.Q(description__icontains=search_query) |
            models.Q(reference_number__icontains=search_query) |
            models.Q(notes__icontains=search_query) |
            models.Q(categories__name__icontains=search_query) |
            models.Q(cost_center__code__icontains=search_query) |
            models.Q(cost_center__name__icontains=search_query) |
            models.Q(account__name__icontains=search_query) |
            models.Q(project__name__icontains=search_query) |
            models.Q(valuation__name__icontains=search_query) |
            models.Q(status__icontains=search_query) |
            models.Q(amount_bs__icontains=search_query) |
            models.Q(amount_usd__icontains=search_query) |
            models.Q(real_dollars__icontains=search_query) |
            models.Q(daily_rate__icontains=search_query)
        )
    
    today = timezone.localdate()
    
    filter_parts = []
    if category_ids:
        categories_qs = Category.objects.filter(id__in=category_ids)
        if categories_qs.exists():
            names = ", ".join([c.name for c in categories_qs])
            filter_parts.append(f"Categorías: {names}")

    if cost_center_id:
        cc_filter = CostCenter.objects.filter(id=cost_center_id).first()
        if cc_filter:
            filter_parts.append(f"Centro de Costo: {cc_filter.code} - {cc_filter.name}")

    if selected_org_id:
        org_filter = Organization.objects.filter(id=selected_org_id).first()
        if org_filter:
            filter_parts.append(f"Organización: {org_filter.name}")
    
    if status_filter:
        status_display = status_filter.capitalize()
        filter_parts.append(f"Estado: {status_display}")
            
    if date_from or date_to:
        if date_from:
            transactions = transactions.filter(date__gte=date_from)
        if date_to:
            transactions = transactions.filter(date__lte=date_to)
        
        if date_from and date_to:
            filter_parts.append(f"Rango: {date_from} a {date_to}")
        elif date_from:
            filter_parts.append(f"Desde: {date_from}")
        else:
            filter_parts.append(f"Hasta: {date_to}")
    elif filter_type != 'all' and filter_type != 'custom':
        labels = {
            'day': "Hoy",
            'week': "Última semana",
            '15days': "Últimos 15 días",
            'month': "Último mes",
            'quarter': "Trimestre",
            '6months': "Últimos 6 meses",
            'year': "Último año",
        }
        if filter_type in labels:
            filter_parts.append(labels[filter_type])
            
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
        transactions = transactions.filter(date__gte=start_date)
        
    filter_label = " | ".join(filter_parts) if filter_parts else "Todas"
        
    transactions = transactions.order_by('date', 'id')
    
    report_totals = transactions.aggregate(
        total_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        total_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        total_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd'))
    )
    
    return org, transactions, report_type, report_totals, filter_label

def exportar_pdf_transacciones(request):
    org, transactions, report_type, report_totals, filter_label = _get_report_data(request)
    now = timezone.now()
    
    # --- Generación de PDF con ReportLab ---
    response = HttpResponse(content_type='application/pdf')
    filename = f"balance_general_{org.name}_{now.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            title=f"Balance General - {org.name}")
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#0d6efd"),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    filter_style = ParagraphStyle(
        'FilterStyle',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=10
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    
    header_cell_style = ParagraphStyle(
        'HeaderCellStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#444444")
    )
    
    # Header
    elements.append(Paragraph("Balance General", title_style))
    elements.append(Paragraph(f"<b>Organización:</b> {org.name}", info_style))
    elements.append(Paragraph(f"<b>Generado el:</b> {now.strftime('%d/%m/%Y %H:%M')}", info_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"<b>Filtro aplicado:</b> {filter_label}", filter_style))
    elements.append(Spacer(1, 0.5*cm))

    # Datos de la tabla
    if report_type == 'real':
        header = [
            Paragraph("Fecha", header_cell_style),
            Paragraph("Descripción", header_cell_style),
            Paragraph("Referencia", header_cell_style),
            Paragraph("Monto (Dólares)", header_cell_style),
            Paragraph("Notas", header_cell_style)
        ]
        data = [header]
        for trans in transactions:
            data.append([
                trans.date.strftime("%d/%m/%Y"),
                Paragraph(trans.description or "", cell_style),
                trans.reference_number or "---",
                f"{trans.real_dollars or 0:,.2f} $",
                Paragraph(trans.notes or "", cell_style)
            ])
        
        if transactions:
            data.append(["", "BALANCE TOTAL:", "", f"{report_totals['total_real_usd'] or 0:,.2f} $", ""])
            
        col_widths = [2.5*cm, 8.5*cm, 3.5*cm, 4.5*cm, 6.0*cm]
    else:
        header = [
            Paragraph("Fecha", header_cell_style),
            Paragraph("Descripción", header_cell_style),
            Paragraph("Referencia", header_cell_style),
            Paragraph("Monto (BS)", header_cell_style),
            Paragraph("Tasa", header_cell_style),
            Paragraph("Monto (USD)", header_cell_style),
            Paragraph("Notas", header_cell_style)
        ]
        data = [header]
        for trans in transactions:
            data.append([
                trans.date.strftime("%d/%m/%Y"),
                Paragraph(trans.description or "", cell_style),
                trans.reference_number or "---",
                f"{trans.amount_bs:,.2f}",
                f"{trans.daily_rate:,.4f}",
                f"{trans.amount_usd:,.2f}",
                Paragraph(trans.notes or "", cell_style)
            ])
            
        if transactions:
            data.append([
                "", "", "BALANCE TOTAL:",
                f"{report_totals['total_bs'] or 0:,.2f} Bs.",
                "",
                f"{report_totals['total_usd'] or 0:,.2f} $",
                ""
            ])
            
        col_widths = [2.2*cm, 5.5*cm, 2.8*cm, 3.2*cm, 2.2*cm, 3.2*cm, 5.5*cm]
    
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'), # Monto BS
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'), # Tasa
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'), # Monto USD
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ])
    
    # Colores condicionales y negritas
    for i, trans in enumerate(transactions):
        idx = i + 1
        if report_type == 'real':
            # Monto USD Real
            if trans.real_dollars < 0:
                table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#198754"))
            table_style.add('FONTNAME', (3, idx), (3, idx), 'Helvetica-Bold')
        else:
            # Monto BS
            if trans.amount_bs < 0:
                table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#198754"))
            table_style.add('FONTNAME', (3, idx), (3, idx), 'Helvetica-Bold')
            
            # Monto USD (BCV)
            if trans.amount_usd < 0:
                table_style.add('TEXTCOLOR', (5, idx), (5, idx), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (5, idx), (5, idx), colors.HexColor("#198754"))
            table_style.add('FONTNAME', (5, idx), (5, idx), 'Helvetica-Bold')

    # Estilo de la última fila (Balance)
    if transactions:
        last_row = len(data) - 1
        table_style.add('BACKGROUND', (0, last_row), (-1, last_row), colors.HexColor("#f1f1f1"))
        table_style.add('FONTNAME', (0, last_row), (-1, last_row), 'Helvetica-Bold')
        table_style.add('ALIGN', (2, last_row), (2, last_row), 'RIGHT')
        
        if report_type == 'real':
            total_real = report_totals['total_real_usd'] or 0
            if total_real < 0:
                table_style.add('TEXTCOLOR', (3, last_row), (3, last_row), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (3, last_row), (3, last_row), colors.HexColor("#198754"))
        else:
            total_bs = report_totals['total_bs'] or 0
            if total_bs < 0:
                table_style.add('TEXTCOLOR', (3, last_row), (3, last_row), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (3, last_row), (3, last_row), colors.HexColor("#198754"))
                
            total_usd = report_totals['total_usd'] or 0
            if total_usd < 0:
                table_style.add('TEXTCOLOR', (5, last_row), (5, last_row), colors.HexColor("#dc3545"))
            else:
                table_style.add('TEXTCOLOR', (5, last_row), (5, last_row), colors.HexColor("#198754"))

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # --- Resumen Gráfico ---
    cd = get_chart_data(transactions, mode=report_type, json_format=False)
    
    if transactions.exists():
        chart_elements = []
        
        # a) Gastos por Categoría (Pie)
        if cd['cat_series']:
            d1 = Drawing(8*cm, 6*cm)
            pc = Pie()
            pc.x = 1.5*cm
            pc.y = 0.5*cm
            pc.width = 4.5*cm
            pc.height = 4.5*cm
            pc.data = cd['cat_series']
            pc.labels = cd['cat_labels']
            pc.sideLabels = 1
            pc.slices.fontSize = 7
            for i, color in enumerate(cd['cat_colors']):
                pc.slices[i].fillColor = colors.HexColor(color)
            d1.add(pc)
            d1.add(String(4*cm, 5.5*cm, "Gastos por Categoría", textAnchor='middle', fontName='Helvetica-Bold', fontSize=10))
            chart_elements.append(d1)
        else:
            chart_elements.append(Paragraph("No hay datos de gastos por categoría", cell_style))

        # b) Ingresos vs Gastos (Bar)
        d2 = Drawing(8*cm, 6*cm)
        bc = VerticalBarChart()
        bc.x = 1*cm
        bc.y = 1*cm
        bc.width = 6*cm
        bc.height = 4*cm
        bc.data = [[cd['total_income']], [cd['total_expense']]]
        bc.categoryAxis.categoryNames = ['Balance']
        bc.bars[0].fillColor = colors.green # Ingresos
        bc.bars[1].fillColor = colors.red   # Gastos
        bc.valueAxis.valueMin = 0
        bc.valueAxis.labels.fontSize = 7
        d2.add(bc)
        # Leyenda simple manual para el gráfico de barras
        d2.add(String(1*cm, 0.2*cm, "Verde: Ingresos", fontSize=7, fillColor=colors.green))
        d2.add(String(4*cm, 0.2*cm, "Rojo: Gastos", fontSize=7, fillColor=colors.red))
        d2.add(String(4*cm, 5.5*cm, "Ingresos vs Gastos", textAnchor='middle', fontName='Helvetica-Bold', fontSize=10))
        chart_elements.append(d2)

        # c) Evolución del Saldo (Line)
        if cd['evo_series']:
            d3 = Drawing(9*cm, 6*cm)
            lc = HorizontalLineChart()
            lc.x = 1*cm
            lc.y = 1.2*cm
            lc.width = 7.5*cm
            lc.height = 3.8*cm
            lc.data = [cd['evo_series']]
            # Limitar etiquetas de fecha si hay demasiadas
            if len(cd['evo_labels']) > 10:
                step = len(cd['evo_labels']) // 10
                lc.categoryAxis.categoryNames = [label if i % step == 0 else '' for i, label in enumerate(cd['evo_labels'])]
            else:
                lc.categoryAxis.categoryNames = cd['evo_labels']
            
            lc.categoryAxis.labels.fontSize = 6
            lc.categoryAxis.labels.angle = 45
            lc.categoryAxis.labels.boxAnchor = 'ne'
            lc.valueAxis.labels.fontSize = 7
            
            # Ajustar rango del eje Y
            all_vals = cd['evo_series'] + [0]
            lc.valueAxis.valueMin = min(all_vals) * 1.1 if min(all_vals) < 0 else 0
            lc.valueAxis.valueMax = max(all_vals) * 1.1 if max(all_vals) > 0 else 10
            
            d3.add(lc)
            d3.add(String(4.5*cm, 5.5*cm, "Evolución del Saldo", textAnchor='middle', fontName='Helvetica-Bold', fontSize=10))
            chart_elements.append(d3)
        else:
            chart_elements.append(Paragraph("No hay datos de evolución", cell_style))

        # Organizar gráficos en una tabla
        charts_table = Table([chart_elements], colWidths=[8.5*cm, 8.5*cm, 9*cm])
        charts_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(charts_table)
        elements.append(Spacer(1, 0.5*cm))

    
    # Footer
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_RIGHT,
        spaceBefore=20
    )
    elements.append(Paragraph("Este documento es un reporte automático generado por Control de Gastos.", footer_style))
    
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


def exportar_xlsx_transacciones(request):
    org, transactions, report_type, report_totals, filter_label = _get_report_data(request)
    now = timezone.now()
    
    filename = f"balance_general_{org.name}_{now.strftime('%Y%m%d')}.xls"
    
    context = {
        'org': org,
        'transactions': transactions,
        'report_type': report_type,
        'report_totals': report_totals,
        'filter_label': filter_label,
        'now': now,
    }
    
    html_content = render_to_string('organizations/reportes/transacciones_excel.html', context)
    
    response = HttpResponse(html_content, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@viewer_restricted
def guardar_transaccion(request, trans_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if trans_id:
        # Si es edición, buscamos la transacción original.
        # Se permite si el usuario tiene acceso a la organización de la transacción
        # O si la transacción pertenece a un proyecto al que la organización actual tiene acceso.
        projects_with_access = Project.objects.filter(
            models.Q(organization=org) | models.Q(shared_organizations__organization=org),
            user_accesses__user=request.user
        )
        
        transactions_with_access = Transaction.objects.filter(
            models.Q(organization=org) | 
            models.Q(organization__user_accesses__user=request.user) |
            models.Q(project__in=projects_with_access)
        ).distinct()
        
        transaction_to_edit = get_object_or_404(transactions_with_access, id=trans_id)
        instance = transaction_to_edit
    
    redirect_to = request.POST.get('next', 'lista_transacciones')
    
    if request.method == 'POST':
        debug_event(
            "transaccion.guardar.intento",
            user_id=request.user.id,
            org_id=org.id,
            trans_id=trans_id,
            is_update=bool(instance),
        )
        # Si viene de un proyecto, necesitamos pasar el proyecto al formulario
        proj_id = request.POST.get('project')
        project_context = None
        if proj_id:
            project_context = get_object_or_404(Project, id=proj_id)
            # Verificar acceso al proyecto
            projects_owned = Project.objects.filter(organization=org)
            projects_shared = Project.objects.filter(shared_organizations__organization=org)
            if not (projects_owned | projects_shared).filter(id=proj_id).exists():
                debug_event(
                    "transaccion.guardar.acceso_denegado",
                    user_id=request.user.id,
                    org_id=org.id,
                    project_id=proj_id,
                )
                messages.error(request, "No tiene acceso a este proyecto.")
                return redirect(redirect_to)

        form = TransactionForm(request.POST, instance=instance, organization=org, project=project_context)
        if form.is_valid():
            transaction = form.save()
            debug_event(
                "transaccion.guardada",
                user_id=request.user.id,
                org_id=org.id,
                transaction_id=transaction.id,
                account_id=transaction.account_id,
                amount_bs=transaction.amount_bs,
                amount_usd=transaction.amount_usd,
                is_update=bool(instance),
            )
            messages.success(request, "Transacción guardada correctamente.")
            
            # Si se especificó una redirección (ej. volver al proyecto)
            if 'next' in request.POST:
                return redirect(request.POST['next'])
        else:
            debug_event(
                "transaccion.guardar.error",
                user_id=request.user.id,
                org_id=org.id,
                trans_id=trans_id,
                errors=form.errors.get_json_data(),
            )
            messages.error(request, f"Error al guardar la transacción: {first_form_error(form)}")
    
    return redirect('lista_transacciones')

@login_required
@viewer_restricted
def eliminar_transaccion(request, trans_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    
    # Verificar acceso: Directo a la org O via proyecto compartido
    projects_with_access = Project.objects.filter(
        models.Q(organization=org) | models.Q(shared_organizations__organization=org),
        user_accesses__user=request.user
    )
    
    transactions_with_access = Transaction.objects.filter(
        models.Q(organization=org) | 
        models.Q(organization__user_accesses__user=request.user) |
        models.Q(project__in=projects_with_access)
    ).distinct()
    
    transaction = get_object_or_404(transactions_with_access, id=trans_id)
    
    redirect_to = request.GET.get('next', 'lista_transacciones')
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, "Transacción eliminada.")
    
    return redirect(redirect_to)

@login_required
def detalle_transaccion(request, trans_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Verificar acceso: Directo a la org O via proyecto compartido
    projects_with_access = Project.objects.filter(
        models.Q(organization=org) | models.Q(shared_organizations__organization=org),
        user_accesses__user=request.user
    )
    
    transactions_with_access = Transaction.objects.filter(
        models.Q(organization=org) | 
        models.Q(organization__user_accesses__user=request.user) |
        models.Q(project__in=projects_with_access)
    ).distinct()
    
    transaction = get_object_or_404(transactions_with_access, id=trans_id)
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
@viewer_restricted
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
@viewer_restricted
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
        balance_usd=Sum(F('transactions__amount_usd') - F('transactions__bank_fee_usd')),
        balance_bs=Sum(F('transactions__amount_bs') - F('transactions__bank_fee_bs')),
        balance_real_usd=Sum(F('transactions__real_dollars') - F('transactions__bank_fee_real_usd'))
    )
    
    form = AccountForm()

    bcv_rate = get_bcv_rate()

    accounts_json = json.dumps([
        {
            'id': acc.id,
            'currency': acc.currency,
            'bank_code': acc.bank_code,
            'bank_name': acc.bank_name,
            'rif': acc.rif,
            'account_number': acc.account_number,
            'holder': acc.holder,
        }
        for acc in accounts
    ])

    return render(request, 'organizations/cuentas.html', {
        'accounts': accounts,
        'accounts_json': accounts_json,
        'form': form,
        'bcv_rate': bcv_rate,
    })

@login_required
@viewer_restricted
def guardar_cuenta(request, acc_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')
    
    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if acc_id:
        instance = get_object_or_404(Account, id=acc_id, organization=org)
    
    if request.method == 'POST':
        debug_event(
            "cuenta.guardar.intento",
            user_id=request.user.id,
            username=request.user.username,
            org_id=org.id,
            acc_id=acc_id,
            is_update=bool(instance),
            is_superuser=request.user.is_superuser,
        )
        form = AccountForm(request.POST, instance=instance)
        if form.is_valid():
            account = form.save(commit=False)
            account.organization = org
            # account.name is already handled by the form.save() or cleaned_data
            account.save()

            if not instance:
                balance = form.cleaned_data.get('initial_balance') or 0
                rate = form.cleaned_data.get('daily_rate') or get_bcv_rate()
                initial_tx = create_initial_balance_transaction(
                    organization=org,
                    account=account,
                    balance=balance,
                    daily_rate=rate,
                )
                if initial_tx:
                    debug_event(
                        "cuenta.saldo_inicial_transaccion_creada",
                        user_id=request.user.id,
                        org_id=org.id,
                        account_id=account.id,
                        currency=account.currency,
                        amount_bs=initial_tx.amount_bs,
                        amount_usd=initial_tx.amount_usd,
                        daily_rate=rate,
                    )
            debug_event(
                "cuenta.guardada",
                user_id=request.user.id,
                org_id=org.id,
                account_id=account.id,
                currency=account.currency,
                bank_code=account.bank_code,
                bank_name=account.bank_name,
                is_update=bool(instance),
            )
            messages.success(request, "Cuenta guardada correctamente.")
        else:
            debug_event(
                "cuenta.guardar.error",
                user_id=request.user.id,
                username=request.user.username,
                org_id=org.id,
                acc_id=acc_id,
                is_superuser=request.user.is_superuser,
                errors=form.errors.get_json_data(),
            )
            messages.error(request, f"Error al guardar la cuenta: {first_form_error(form)}")
            
    return redirect('lista_cuentas')

@login_required
@viewer_restricted
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
    
    # --- Lógica de Filtrado ---
    filter_type = request.GET.get('filter_type', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_raw = request.GET.getlist('category')
    category_ids = []
    for val in category_raw:
        if ',' in val:
            category_ids.extend([v.strip() for v in val.split(',') if v.strip()])
        else:
            category_ids.append(val)
    category_ids = [cid for cid in category_ids if cid and cid != 'None' and cid != 'null']
    search_query = request.GET.get('search', '')

    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    
    transactions_list = Transaction.objects.filter(account=account)

    if search_query:

        transactions_list = transactions_list.filter(
            models.Q(description__icontains=search_query) |
            models.Q(reference_number__icontains=search_query) |
            models.Q(notes__icontains=search_query) |
            models.Q(categories__name__icontains=search_query) |
            models.Q(project__name__icontains=search_query) |
            models.Q(valuation__name__icontains=search_query) |
            models.Q(status__icontains=search_query) |
            models.Q(amount_bs__icontains=search_query) |
            models.Q(amount_usd__icontains=search_query) |
            models.Q(real_dollars__icontains=search_query) |
            models.Q(daily_rate__icontains=search_query)
        )

    if category_ids:
        transactions_list = transactions_list.filter(categories__id__in=category_ids).distinct()

    today = timezone.localdate()
    
    if date_from or date_to:
        if date_from:
            transactions_list = transactions_list.filter(date__gte=date_from)
        if date_to:
            transactions_list = transactions_list.filter(date__lte=date_to)
    elif filter_type != 'all' and filter_type != 'custom':
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

    sort = request.GET.get('sort', 'desc')
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')
    
    totals = transactions_list.aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd')),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
        income_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
        expense_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
        fees_usd=Sum('bank_fee_usd'),
        fees_bs=Sum('bank_fee_bs'),
        fees_real_usd=Sum('bank_fee_real_usd')
    )
    
    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(organization=org)
    
    filter_options = [
        ('all', 'Todo el tiempo'),
        ('day', 'Hoy'),
        ('week', 'Esta semana'),
        ('15days', 'Últimos 15 días'),
        ('month', 'Último mes'),
        ('quarter', 'Último trimestre'),
        ('6months', 'Últimos 6 meses'),
        ('year', 'Último año'),
        ('custom', 'Personalizado'),
    ]

    # Mapeo de cuentas a monedas para lógica en JS
    accounts_data = {a.id: a.currency for a in Account.objects.filter(organization=org)}

    return render(request, 'organizations/detalle_cuenta.html', {
        'account': account,
        'page_obj': page_obj,
        'sort': sort,
        'search': search_query,
        'filter_type': filter_type,
        'date_from': date_from,
        'date_to': date_to,
        'categories': categories,
        'selected_category': category_ids[0] if category_ids else '',
        'selected_categories': category_ids,
        'filter_options': filter_options,
        'accounts_data': json.dumps(accounts_data),
        'totals': {
            'balance_usd': totals['balance_usd'] or 0,
            'balance_bs': totals['balance_bs'] or 0,
            'balance_real_usd': totals['balance_real_usd'] or 0,
            'income_usd': totals['income_usd'] or 0,
            'expense_usd': abs(totals['expense_usd'] or 0) + (totals['fees_usd'] or 0),
            'income_bs': totals['income_bs'] or 0,
            'expense_bs': abs(totals['expense_bs'] or 0) + (totals['fees_bs'] or 0),
            'income_real_usd': totals['income_real_usd'] or 0,
            'expense_real_usd': abs(totals['expense_real_usd'] or 0) + (totals['fees_real_usd'] or 0),
        }
    })

# --- Proyectos ---

@login_required
def lista_proyectos(request):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    
    # Proyectos que pertenecen a la organización o a los que tiene acceso
    # Y que el usuario actual tenga acceso explícito (ProjectUserAccess)
    projects_qs = Project.objects.filter(
        models.Q(organization=org) | models.Q(shared_organizations__organization=org),
        user_accesses__user=request.user
    ).distinct()

    # Subconsultas para calcular balance TOTAL del proyecto (todas las orgs)
    total_usd_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk')
    ).order_by().values('project').annotate(
        total=Sum(F('amount_usd') - F('bank_fee_usd'))
    ).values('total')

    total_bs_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk')
    ).order_by().values('project').annotate(
        total=Sum(F('amount_bs') - F('bank_fee_bs'))
    ).values('total')

    total_real_usd_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk')
    ).order_by().values('project').annotate(
        total=Sum(F('real_dollars') - F('bank_fee_real_usd'))
    ).values('total')

    projects = projects_qs.annotate(
        total_balance_usd=Coalesce(Subquery(total_usd_subquery), Value(0, output_field=models.DecimalField())),
        total_balance_bs=Coalesce(Subquery(total_bs_subquery), Value(0, output_field=models.DecimalField())),
        total_balance_real_usd=Coalesce(Subquery(total_real_usd_subquery), Value(0, output_field=models.DecimalField()))
    )

    form = ProjectForm()

    return render(request, 'organizations/proyectos.html', {
        'projects': projects,
        'form': form,
    })

@login_required
@viewer_restricted
def guardar_proyecto(request, proj_id=None):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    instance = None
    if proj_id:
        # Solo el dueño puede editar el proyecto
        instance = get_object_or_404(Project, id=proj_id, organization=org)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=instance)
        if form.is_valid():
            project = form.save(commit=False)
            if not instance:
                project.organization = org
            project.save()
            
            # Si es un proyecto nuevo, darle acceso al creador automáticamente
            if not instance:
                from .models import ProjectUserAccess
                ProjectUserAccess.objects.get_or_create(user=request.user, project=project)
                
            messages.success(request, "Proyecto guardado correctamente.")
        else:
            messages.error(request, "Error al guardar el proyecto.")

    return redirect('lista_proyectos')

@login_required
@viewer_restricted
def eliminar_proyecto(request, proj_id):
    org_id = request.session.get('org_id')
    if not org_id:
        return redirect('dashboard')

    org = get_object_or_404(Organization, id=org_id)
    # Solo el dueño puede eliminar
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
    
    # Verificar acceso: El proyecto debe pertenecer u estar compartido con la org, 
    # Y el usuario debe tener acceso.
    projects_owned = Project.objects.filter(organization=org)
    projects_shared = Project.objects.filter(shared_organizations__organization=org)
    project_qs = (projects_owned | projects_shared).distinct()
    
    project = get_object_or_404(project_qs, id=proj_id, user_accesses__user=request.user)

    # --- Lógica de Filtrado ---
    filter_type = request.GET.get('filter_type', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_org_id = request.GET.get('organization')
    search_query = request.GET.get('search', '')
    tx_filter = request.GET.get('tx_filter', 'all') # 'all', 'bcv', 'real'
    view_mode = request.GET.get('view_mode', 'bcv') # 'bcv' or 'real'

    # Sincronización: El filtro de transacciones afecta al toggle de balance
    if tx_filter == 'real':
        view_mode = 'real'
    elif tx_filter == 'bcv':
        view_mode = 'bcv'

    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if selected_org_id == 'None' or selected_org_id == '': selected_org_id = None

    # Ver TODAS las transacciones del proyecto (de cualquier organización con acceso)
    transactions_list = Transaction.objects.filter(project=project)

    # Filtrar por tipo de transacción (BCV / Real Dollars)
    if tx_filter == 'real':
        transactions_list = transactions_list.exclude(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))
    elif tx_filter == 'bcv':
        transactions_list = transactions_list.filter(models.Q(real_dollars=0) | models.Q(real_dollars__isnull=True))

    if search_query:
        transactions_list = transactions_list.filter(
            models.Q(description__icontains=search_query) |
            models.Q(reference_number__icontains=search_query) |
            models.Q(notes__icontains=search_query) |
            models.Q(category__name__icontains=search_query) |
            models.Q(account__name__icontains=search_query) |
            models.Q(project__name__icontains=search_query) |
            models.Q(valuation__name__icontains=search_query) |
            models.Q(status__icontains=search_query) |
            models.Q(amount_bs__icontains=search_query) |
            models.Q(amount_usd__icontains=search_query) |
            models.Q(real_dollars__icontains=search_query) |
            models.Q(daily_rate__icontains=search_query)
        )

    if selected_org_id:
        transactions_list = transactions_list.filter(organization_id=selected_org_id)

    today = timezone.localdate()
    
    if date_from or date_to:
        if date_from:
            transactions_list = transactions_list.filter(date__gte=date_from)
        if date_to:
            transactions_list = transactions_list.filter(date__lte=date_to)
    elif filter_type != 'all' and filter_type != 'custom':
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

    sort = request.GET.get('sort', 'desc')
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')

    # Anotar valuaciones con el monto cubierto por transacciones de crédito de TODAS las organizaciones
    # Sumamos tanto amount_usd (BCV) como real_dollars
    valuations = list(Valuation.objects.filter(project=project).annotate(
        covered_usd=Sum(
            Coalesce('transactions__amount_usd', Value(0, output_field=models.DecimalField())) + 
            Coalesce('transactions__real_dollars', Value(0, output_field=models.DecimalField())),
            filter=models.Q(transactions__amount_usd__gt=0) | models.Q(transactions__real_dollars__gt=0)
        ),
        covered_bs=Sum('transactions__amount_bs', filter=models.Q(transactions__amount_bs__gt=0))
    ))

    # Calcular porcentajes
    for val in valuations:
        val.progress = 0
        if val.amount_usd > 0:
            covered = val.covered_usd or 0
            val.progress = min(round((covered / val.amount_usd) * 100, 2), 100)
        elif val.amount_bs > 0:
            covered = val.covered_bs or 0
            val.progress = min(round((covered / val.amount_bs) * 100, 2), 100)

    # Totales GENERALES del proyecto (sin filtros de período/búsqueda/org)
    overall_project = Transaction.objects.filter(project=project).aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd')),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        income_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
        expense_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
        fees_usd=Sum('bank_fee_usd'),
        fees_bs=Sum('bank_fee_bs'),
        fees_real_usd=Sum('bank_fee_real_usd')
    )
    overall_org = Transaction.objects.filter(project=project, organization=org).aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd'))
    )

    # Totales FILTRADOS para el dashboard dinámico
    totals_project = transactions_list.aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd')),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0)),
        income_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__gt=0)),
        expense_real_usd=Sum('real_dollars', filter=models.Q(real_dollars__lt=0)),
        fees_usd=Sum('bank_fee_usd'),
        fees_bs=Sum('bank_fee_bs'),
        fees_real_usd=Sum('bank_fee_real_usd')
    )
    
    # Totales solo para la organización actual (balance de la organización FILTRADO)
    totals_org = transactions_list.filter(organization=org).aggregate(
        balance_usd=Sum(F('amount_usd') - F('bank_fee_usd')),
        balance_bs=Sum(F('amount_bs') - F('bank_fee_bs')),
        balance_real_usd=Sum(F('real_dollars') - F('bank_fee_real_usd'))
    )

    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    val_form = ValuationForm()
    trans_form = TransactionForm(organization=org, project=project)
    bcv_rate = get_bcv_rate()

    # Organizaciones para el filtro y datos dinámicos
    orgs_with_access = (Organization.objects.filter(projects=project) | Organization.objects.filter(shared_projects__project=project)).distinct()
    
    chart_data = get_chart_data(transactions_list, mode=view_mode)

    orgs_data = {}
    for o in orgs_with_access:
        orgs_data[o.id] = {
            'accounts': list(Account.objects.filter(organization=o).values('id', 'name', 'currency')),
            'categories': list(Category.objects.filter(organization=o).values('id', 'name', 'color')),
            'cost_centers': list(CostCenter.objects.filter(organization=o).values('id', 'name', 'code'))
        }

    filter_options = [
        ('all', 'Todo el tiempo'),
        ('day', 'Hoy'),
        ('week', 'Esta semana'),
        ('15days', 'Últimos 15 días'),
        ('month', 'Último mes'),
        ('quarter', 'Último trimestre'),
        ('6months', 'Últimos 6 meses'),
        ('year', 'Último año'),
        ('custom', 'Personalizado'),
    ]

    return render(request, 'organizations/detalle_proyecto.html', {
        'project': project,
        'valuations': valuations,
        'page_obj': page_obj,
        'val_form': val_form,
        'trans_form': trans_form,
        'orgs_data': json.dumps(orgs_data, cls=DecimalEncoder),
        'bcv_rate': bcv_rate,
        'orgs_with_access': orgs_with_access,
        'filter_type': filter_type,
        'date_from': date_from,
        'date_to': date_to,
        'search': search_query,
        'selected_org_id': selected_org_id,
        'filter_options': filter_options,
        'chart_data': chart_data,
        'sort': sort,
        'view_mode': view_mode,
        'tx_filter': tx_filter,
        'totals': {
            'balance_usd': (overall_project['balance_usd'] or 0) + (overall_project['balance_real_usd'] or 0),
            'balance_bs': overall_project['balance_bs'] or 0,
            'balance_real_usd': overall_project['balance_real_usd'] or 0,
            'org_balance_usd': (overall_org['balance_usd'] or 0) + (overall_org['balance_real_usd'] or 0),
            'org_balance_bs': overall_org['balance_bs'] or 0,
            'org_balance_real_usd': overall_org['balance_real_usd'] or 0,
            'income_usd': (overall_project['income_usd'] or 0) + (overall_project['income_real_usd'] or 0),
            'income_bs': overall_project['income_bs'] or 0,
            'income_real_usd': overall_project['income_real_usd'] or 0,
            'expense_usd': abs((overall_project['expense_usd'] or 0) + (overall_project['expense_real_usd'] or 0)) + 
                           (overall_project['fees_usd'] or 0) + (overall_project['fees_real_usd'] or 0),
            'expense_bs': abs(overall_project['expense_bs'] or 0) + (overall_project['fees_bs'] or 0),
            'expense_real_usd': abs(overall_project['expense_real_usd'] or 0) + (overall_project['fees_real_usd'] or 0),
            # Filtros dinámicos
            'filtered_balance_usd': (totals_project['balance_usd'] or 0) + (totals_project['balance_real_usd'] or 0),
            'filtered_balance_bs': totals_project['balance_bs'] or 0,
        },
        'tx_filter_options': [
            ('all', 'Todas las transacciones'),
            ('bcv', 'Transacciones BCV'),
            ('real', 'Transacciones Dólares Reales'),
        ],
    })

# --- Valuaciones ---

@login_required
@viewer_restricted
def guardar_valuacion(request, proj_id, val_id=None):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    
    # Permitir si es dueño O si tiene acceso compartido
    project = get_object_or_404(
        Project.objects.filter(
            models.Q(organization=org) | models.Q(shared_organizations__organization=org)
        ).distinct(), 
        id=proj_id
    )
    
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
@viewer_restricted
def eliminar_valuacion(request, val_id):
    org_id = request.session.get('org_id')
    org = get_object_or_404(Organization, id=org_id)
    
    # Buscar la valuación y verificar que la organización tenga acceso al proyecto
    valuation = get_object_or_404(Valuation, id=val_id)
    project = valuation.project
    
    # Verificar acceso (Dueño o Compartido)
    is_owner = project.organization == org
    is_shared = project.shared_organizations.filter(organization=org).exists()
    
    if not (is_owner or is_shared):
        messages.error(request, "No tiene permiso para eliminar esta valuación.")
        return redirect('lista_proyectos')

    proj_id = project.id

    if request.method == 'POST':
        valuation.delete()
        messages.success(request, "Valuación eliminada.")

    return redirect('detalle_proyecto', proj_id=proj_id)
