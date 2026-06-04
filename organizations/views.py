from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from .models import Organization, OrganizationAccess, Transaction, Category, Account, Project, Valuation
from .amounts import create_initial_balance_transaction
from .forms import TransactionForm, CategoryForm, AccountForm, ProjectForm, ValuationForm
from django.contrib import messages
from django.db.models import Sum, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce, TruncMonth

def get_chart_data(transactions_qs):
    # 1. Desglose de Gastos por Categoría
    category_spending = transactions_qs.filter(amount_usd__lt=0).values('category__name', 'category__color').annotate(
        total=Sum('amount_usd')
    ).order_by('total')
    
    cat_labels = [item['category__name'] or 'Sin categoría' for item in category_spending]
    cat_series = [float(abs(item['total'])) for item in category_spending]
    cat_colors = [item['category__color'] or '#000000' for item in category_spending]

    # 2. Balance Total (Ingresos vs Gastos)
    totals_data = transactions_qs.aggregate(
        income=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense=Sum('amount_usd', filter=models.Q(amount_usd__lt=0))
    )
    
    total_income = float(totals_data['income'] or 0)
    total_expense = float(abs(totals_data['expense'] or 0))

    # 3. Evolución del Saldo
    evolution_data = transactions_qs.order_by('date').values('date').annotate(
        daily_sum=Sum('amount_usd')
    )
    
    evo_labels = []
    evo_series = []
    current_balance = 0
    for item in evolution_data:
        current_balance += float(item['daily_sum'])
        evo_labels.append(item['date'].strftime('%Y-%m-%d'))
        evo_series.append(round(current_balance, 2))

    return {
        'cat_labels': json.dumps(cat_labels),
        'cat_series': json.dumps(cat_series),
        'cat_colors': json.dumps(cat_colors),
        'total_income': total_income,
        'total_expense': total_expense,
        'evo_labels': json.dumps(evo_labels),
        'evo_series': json.dumps(evo_series),
    }
from django.utils import timezone
from datetime import timedelta
import json
from django.db import models
from django.core.paginator import Paginator
from decimal import Decimal
from CashFlow.debug import debug_event, first_form_error
from BCV.services.bcv_scrapper import as_dashboard_rates, get_rate_for_date

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
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0))
    )
    
    return {
        'income_usd': res['income_usd'] or 0,
        'expense_usd': abs(res['expense_usd'] or 0),
        'income_bs': res['income_bs'] or 0,
        'expense_bs': abs(res['expense_bs'] or 0),
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
    if sort == 'asc':
        recent_transactions = Transaction.objects.filter(organization_id=org_id).order_by('date', 'id')[:10]
    else:
        recent_transactions = Transaction.objects.filter(organization_id=org_id).order_by('-date', '-id')[:10]
    
    chart_data = get_chart_data(Transaction.objects.filter(organization_id=org_id))
    
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

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
    sort = request.GET.get('sort', 'desc')
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')

    # Calcular totales filtrados

    totals = transactions_list.aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs'),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0))
    )
    
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
        'sort': sort,
        'totals': {
            'balance_usd': totals['balance_usd'] or 0,
            'balance_bs': totals['balance_bs'] or 0,
            'income_usd': totals['income_usd'] or 0,
            'income_bs': totals['income_bs'] or 0,
            'expense_usd': abs(totals['expense_usd'] or 0),
            'expense_bs': abs(totals['expense_bs'] or 0),
        },
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
    
    # Datos de la tabla
    data = [
        [
            Paragraph("Fecha", header_cell_style),
            Paragraph("Descripción", header_cell_style),
            Paragraph("Referencia", header_cell_style),
            Paragraph("Monto (BS)", header_cell_style),
            Paragraph("Tasa", header_cell_style),
            Paragraph("Monto (USD)", header_cell_style),
            Paragraph("Notas", header_cell_style)
        ]
    ]
    
    for trans in transactions:
        row = [
            trans.date.strftime("%d/%m/%Y"),
            Paragraph(trans.description or "", cell_style),
            trans.reference_number or "---",
            f"{trans.amount_bs:,.2f}",
            f"{trans.daily_rate:,.4f}",
            f"{trans.amount_usd:,.2f}",
            Paragraph(trans.notes or "", cell_style)
        ]
        data.append(row)
    
    # Fila de balance
    if transactions:
        data.append([
            "", "", "BALANCE:",
            f"{report_totals['total_bs'] or 0:,.2f} Bs.",
            "",
            f"{report_totals['total_usd'] or 0:,.2f} $",
            ""
        ])

    # Anchos de columna basados en el template original
    col_widths = [1.94*cm, 5.29*cm, 2.12*cm, 3.0*cm, 1.76*cm, 3.0*cm, 5.29*cm]
    
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
        # Monto BS
        if trans.amount_bs < 0:
            table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#dc3545"))
        else:
            table_style.add('TEXTCOLOR', (3, idx), (3, idx), colors.HexColor("#198754"))
        table_style.add('FONTNAME', (3, idx), (3, idx), 'Helvetica-Bold')
        
        # Monto USD
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


@login_required
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
            if instance:
                account.name = build_account_display_name(
                    account.bank_name,
                    account.account_number,
                    account.currency,
                )
            else:
                account.name = form.cleaned_data['name']
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
    
    sort = request.GET.get('sort', 'desc')
    transactions_list = Transaction.objects.filter(account=account)
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')
    
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
        'sort': sort,
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
    
    # Proyectos que pertenecen a la organización o a los que tiene acceso
    # Y que el usuario actual tenga acceso explícito (ProjectUserAccess)
    projects_qs = Project.objects.filter(
        models.Q(organization=org) | models.Q(shared_organizations__organization=org),
        user_accesses__user=request.user
    ).distinct()

    # Subconsultas para calcular balance de MI organización
    org_usd_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk'),
        organization_id=org_id
    ).order_by().values('project').annotate(
        total=Sum('amount_usd')
    ).values('total')

    org_bs_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk'),
        organization_id=org_id
    ).order_by().values('project').annotate(
        total=Sum('amount_bs')
    ).values('total')

    # Subconsultas para calcular balance TOTAL del proyecto (todas las orgs)
    total_usd_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk')
    ).order_by().values('project').annotate(
        total=Sum('amount_usd')
    ).values('total')

    total_bs_subquery = Transaction.objects.filter(
        project_id=OuterRef('pk')
    ).order_by().values('project').annotate(
        total=Sum('amount_bs')
    ).values('total')

    projects = projects_qs.annotate(
        org_balance_usd=Coalesce(Subquery(org_usd_subquery), Value(0, output_field=models.DecimalField())),
        org_balance_bs=Coalesce(Subquery(org_bs_subquery), Value(0, output_field=models.DecimalField())),
        total_balance_usd=Coalesce(Subquery(total_usd_subquery), Value(0, output_field=models.DecimalField())),
        total_balance_bs=Coalesce(Subquery(total_bs_subquery), Value(0, output_field=models.DecimalField()))
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

    if date_from == 'None': date_from = None
    if date_to == 'None': date_to = None
    if selected_org_id == 'None' or selected_org_id == '': selected_org_id = None

    # Ver TODAS las transacciones del proyecto (de cualquier organización con acceso)
    transactions_list = Transaction.objects.filter(project=project)

    if selected_org_id:
        transactions_list = transactions_list.filter(organization_id=selected_org_id)

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

    sort = request.GET.get('sort', 'desc')
    if sort == 'asc':
        transactions_list = transactions_list.order_by('date', 'id')
    else:
        transactions_list = transactions_list.order_by('-date', '-id')

    # Anotar valuaciones con el monto cubierto por transacciones de crédito de TODAS las organizaciones
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

    # Totales para el balance del proyecto (transacciones filtradas)
    totals_project = transactions_list.aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs'),
        income_usd=Sum('amount_usd', filter=models.Q(amount_usd__gt=0)),
        expense_usd=Sum('amount_usd', filter=models.Q(amount_usd__lt=0)),
        income_bs=Sum('amount_bs', filter=models.Q(amount_bs__gt=0)),
        expense_bs=Sum('amount_bs', filter=models.Q(amount_bs__lt=0))
    )
    
    # Totales solo para la organización actual (balance de la organización)
    totals_org = transactions_list.filter(organization=org).aggregate(
        balance_usd=Sum('amount_usd'),
        balance_bs=Sum('amount_bs')
    )

    paginator = Paginator(transactions_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    val_form = ValuationForm()
    trans_form = TransactionForm(organization=org, project=project)
    bcv_rate = get_bcv_rate()

    # Organizaciones para el filtro y datos dinámicos
    orgs_with_access = (Organization.objects.filter(projects=project) | Organization.objects.filter(shared_projects__project=project)).distinct()
    
    chart_data = get_chart_data(transactions_list)

    orgs_data = {}
    for o in orgs_with_access:
        orgs_data[o.id] = {
            'accounts': list(Account.objects.filter(organization=o).values('id', 'name')),
            'categories': list(Category.objects.filter(organization=o).values('id', 'name'))
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
        'selected_org_id': selected_org_id,
        'filter_options': filter_options,
        'chart_data': chart_data,
        'sort': sort,
        'totals': {
            'balance_usd': totals_project['balance_usd'] or 0,
            'balance_bs': totals_project['balance_bs'] or 0,
            'income_usd': totals_project['income_usd'] or 0,
            'expense_usd': abs(totals_project['expense_usd'] or 0),
            'income_bs': totals_project['income_bs'] or 0,
            'expense_bs': abs(totals_project['expense_bs'] or 0),
            'org_balance_usd': totals_org['balance_usd'] or 0,
            'org_balance_bs': totals_org['balance_bs'] or 0,
        }
    })

# --- Valuaciones ---

@login_required
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
