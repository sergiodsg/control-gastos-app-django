from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from .models import Transaction, Category, Account, Project, Valuation, Organization
from .amounts import apply_dual_currency_amounts
from .banks import build_account_display_name, validate_bank_for_currency
from .validators import validate_account_number, validate_holder, validate_rif

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'date', 'organization', 'account', 'reference_number', 'description', 
            'notes', 'category', 'project', 'valuation', 
            'status', 'amount_bs', 'amount_usd', 'daily_rate',
            'bank_fee_bs', 'bank_fee_usd', 'real_dollars', 'bank_fee_real_usd'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'class': 'cf-input', 'type': 'date', 'required': 'required'}),
            'organization': forms.Select(attrs={'class': 'cf-input', 'required': 'required'}),
            'account': forms.Select(attrs={'class': 'cf-input', 'required': 'required'}),
            'reference_number': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nro. Referencia'}),
            'description': forms.Textarea(attrs={'class': 'cf-input', 'rows': 2, 'placeholder': 'Descripción de la transacción', 'required': 'required'}),
            'notes': forms.Textarea(attrs={'class': 'cf-input', 'rows': 2, 'placeholder': 'Notas adicionales'}),
            'category': forms.Select(attrs={'class': 'cf-input'}),
            'project': forms.Select(attrs={'class': 'cf-input'}),
            'valuation': forms.Select(attrs={'class': 'cf-input'}),
            'status': forms.Select(attrs={'class': 'cf-input', 'required': 'required'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number', 'required': 'required'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number', 'required': 'required'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number', 'required': 'required'}),
            'bank_fee_bs': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'bank_fee_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'real_dollars': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'bank_fee_real_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        if not account:
            return cleaned_data

        real_dollars = cleaned_data.get('real_dollars') or 0
        bank_fee_real_usd = cleaned_data.get('bank_fee_real_usd') or 0
        
        # Si la cuenta es en dólares, forzar el uso de real_dollars
        if account.currency == Account.CURRENCY_USD:
            amount_usd_bcv = cleaned_data.get('amount_usd') or 0
            
            # Si el usuario mandó el monto en el campo BCV por error, lo movemos a real_dollars
            if real_dollars == 0 and amount_usd_bcv != 0:
                real_dollars = amount_usd_bcv
                cleaned_data['real_dollars'] = real_dollars

            if real_dollars == 0:
                raise ValidationError("Una cuenta en dólares solo puede recibir fondos en Dólares Reales.")

            cleaned_data['amount_bs'] = 0
            cleaned_data['amount_usd'] = 0
            cleaned_data['bank_fee_bs'] = 0
            cleaned_data['bank_fee_usd'] = 0
            # Mantenemos bank_fee_real_usd tal cual viene del form
        
        else:
            # CUENTA EN BOLÍVARES: Solo BCV
            if real_dollars != 0 or bank_fee_real_usd != 0:
                raise ValidationError("Una cuenta en bolívares solo puede recibir fondos mediante BCV (Bolívares o Dólares BCV).")
            
            cleaned_data['real_dollars'] = 0
            cleaned_data['bank_fee_real_usd'] = 0
            
            amount_bs = cleaned_data.get('amount_bs') or 0
            amount_usd = cleaned_data.get('amount_usd') or 0
            daily_rate = cleaned_data.get('daily_rate') or 1
            amount_bs, amount_usd = apply_dual_currency_amounts(amount_bs, amount_usd, daily_rate)
            cleaned_data['amount_bs'] = amount_bs
            cleaned_data['amount_usd'] = amount_usd

            # Comisión bancaria BCV
            bank_fee_bs = cleaned_data.get('bank_fee_bs') or 0
            bank_fee_usd = cleaned_data.get('bank_fee_usd') or 0
            bank_fee_bs, bank_fee_usd = apply_dual_currency_amounts(bank_fee_bs, bank_fee_usd, daily_rate)
            cleaned_data['bank_fee_bs'] = bank_fee_bs
            cleaned_data['bank_fee_usd'] = bank_fee_usd

        return cleaned_data

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Estado por defecto: Completado
        self.fields['status'].initial = 'completado'
        
        if project:
            # Si estamos en un proyecto, restringir organizaciones a las que tienen acceso
            orgs_owned = Organization.objects.filter(projects=project)
            orgs_shared = Organization.objects.filter(shared_projects__project=project)
            self.fields['organization'].queryset = (orgs_owned | orgs_shared).distinct()
            
            # Valuaciones del proyecto
            self.fields['valuation'].queryset = Valuation.objects.filter(project=project)
            
            # Filtrar cuentas y categorías por la organización seleccionada (o la actual si no hay post)
            selected_org = self.data.get('organization') or (self.instance.organization_id if self.instance.pk else organization.id if organization else None)
            if selected_org:
                self.fields['organization'].initial = selected_org
                self.fields['account'].queryset = Account.objects.filter(organization_id=selected_org)
                self.fields['category'].queryset = Category.objects.filter(organization_id=selected_org)
            else:
                self.fields['account'].queryset = Account.objects.none()
                self.fields['category'].queryset = Category.objects.none()
        elif organization:
            # Comportamiento original para la vista de transacciones
            self.fields['organization'].queryset = Organization.objects.filter(id=organization.id)
            self.fields['organization'].initial = organization
            self.fields['organization'].widget = forms.HiddenInput()
            
            self.fields['category'].queryset = Category.objects.filter(organization=organization)
            self.fields['account'].queryset = Account.objects.filter(organization=organization)
            self.fields['project'].queryset = Project.objects.filter(
                models.Q(organization=organization) | models.Q(shared_organizations__organization=organization)
            ).distinct()
            self.fields['valuation'].queryset = Valuation.objects.filter(
                models.Q(project__organization=organization) | models.Q(project__shared_organizations__organization=organization)
            ).distinct()

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nombre de la categoría'}),
            'description': forms.Textarea(attrs={'class': 'cf-input', 'rows': 2, 'placeholder': 'Breve descripción'}),
            'color': forms.TextInput(attrs={'class': 'cf-input', 'type': 'color', 'style': 'height: 38px; width: 60px; padding: 2px;'}),
        }

class AccountForm(forms.ModelForm):
    currency = forms.ChoiceField(
        choices=Account.CURRENCY_CHOICES,
        label='Moneda de la cuenta',
        widget=forms.Select(attrs={'class': 'cf-select', 'id': 'id_account_currency'}),
    )
    bank_code = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_bank_code'}),
    )
    bank_name = forms.CharField(
        label='Banco',
        widget=forms.HiddenInput(attrs={'id': 'id_bank_name'}),
    )
    rif = forms.CharField(
        label='RIF',
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'J-12345678-9'}),
    )
    account_number = forms.CharField(
        label='Número de cuenta',
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': '0102xxxxxxxxxxxxxxxx'}),
    )
    holder = forms.CharField(
        label='Titular',
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nombre del titular'}),
    )
    name = forms.CharField(
        label='Nombre de la cuenta',
        required=True,
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Ej. Cuenta Principal, Nómina, etc.'}),
    )
    initial_balance = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        required=False,
        label='Saldo inicial',
        widget=forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number', 'placeholder': '0.00'}),
    )
    daily_rate = forms.DecimalField(
        max_digits=20,
        decimal_places=4,
        required=False,
        label='Tasa BCV del día',
        widget=forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number'}),
    )

    class Meta:
        model = Account
        fields = ['currency', 'bank_code', 'bank_name', 'rif', 'account_number', 'holder', 'name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['currency'].disabled = True

    def clean_rif(self):
        return validate_rif(self.cleaned_data['rif'])

    def clean_account_number(self):
        return validate_account_number(self.cleaned_data['account_number'])

    def clean_holder(self):
        return validate_holder(self.cleaned_data['holder'])

    def clean(self):
        cleaned_data = super().clean()
        currency = cleaned_data.get('currency')
        bank_code = cleaned_data.get('bank_code')
        bank_name = cleaned_data.get('bank_name')

        try:
            code, name = validate_bank_for_currency(currency, bank_code, bank_name)
            cleaned_data['bank_code'] = code
            cleaned_data['bank_name'] = name
        except ValidationError as exc:
            self.add_error('bank_name', exc.messages[0])

        balance = cleaned_data.get('initial_balance') or 0
        if balance < 0:
            self.add_error('initial_balance', 'El saldo inicial no puede ser negativo.')

        return cleaned_data

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nombre del proyecto'}),
            'description': forms.Textarea(attrs={'class': 'cf-input', 'rows': 3, 'placeholder': 'Descripción del proyecto'}),
        }

class ValuationForm(forms.ModelForm):
    class Meta:
        model = Valuation
        fields = ['name', 'amount_usd', 'amount_bs', 'daily_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Ej. Valuación 01, Fundaciones...', 'required': 'required'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number', 'required': 'required'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number', 'required': 'required'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number', 'required': 'required'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        usd = cleaned_data.get('amount_usd')
        bs = cleaned_data.get('amount_bs')
        rate = cleaned_data.get('daily_rate') or 1
        
        if (usd and usd != 0) and (not bs or bs == 0):
            cleaned_data['amount_bs'] = round(usd * rate, 2)
        elif (bs and bs != 0) and (not usd or usd == 0):
            cleaned_data['amount_usd'] = round(bs / rate, 2) if rate != 0 else 0
            
        return cleaned_data
