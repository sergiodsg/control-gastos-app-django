from django import forms
from django.db import models
from .models import Transaction, Category, Account, Project, Valuation, Organization

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'date', 'organization', 'account', 'reference_number', 'description', 
            'notes', 'category', 'project', 'valuation', 
            'status', 'amount_bs', 'amount_usd', 'daily_rate'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'class': 'cf-input', 'type': 'date'}),
            'organization': forms.Select(attrs={'class': 'cf-input'}),
            'account': forms.Select(attrs={'class': 'cf-input'}),
            'reference_number': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nro. Referencia'}),
            'description': forms.Textarea(attrs={'class': 'cf-input', 'rows': 2, 'placeholder': 'Descripción de la transacción'}),
            'notes': forms.Textarea(attrs={'class': 'cf-input', 'rows': 2, 'placeholder': 'Notas adicionales'}),
            'category': forms.Select(attrs={'class': 'cf-input'}),
            'project': forms.Select(attrs={'class': 'cf-input'}),
            'valuation': forms.Select(attrs={'class': 'cf-input'}),
            'status': forms.Select(attrs={'class': 'cf-input'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount_bs = cleaned_data.get('amount_bs')
        amount_usd = cleaned_data.get('amount_usd')
        daily_rate = cleaned_data.get('daily_rate') or 1
        
        # Si uno es cero y el otro no, calculamos el faltante basándonos en la tasa
        if (amount_usd and amount_usd != 0) and (not amount_bs or amount_bs == 0):
            cleaned_data['amount_bs'] = round(amount_usd * daily_rate, 2)
        elif (amount_bs and amount_bs != 0) and (not amount_usd or amount_usd == 0):
            cleaned_data['amount_usd'] = round(amount_bs / daily_rate, 2) if daily_rate != 0 else 0
            
        return cleaned_data

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
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
    initial_amount_usd = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False, label="Monto inicial (USD)",
        widget=forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'})
    )
    initial_amount_bs = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False, label="Monto inicial (BS)",
        widget=forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'})
    )
    daily_rate = forms.DecimalField(
        max_digits=20, decimal_places=4, required=False, label="Tasa del día (para monto inicial)",
        widget=forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number'})
    )

    def clean(self):
        cleaned_data = super().clean()
        usd = cleaned_data.get('initial_amount_usd')
        bs = cleaned_data.get('initial_amount_bs')
        rate = cleaned_data.get('daily_rate') or 1
        
        if (usd and usd != 0) and (not bs or bs == 0):
            cleaned_data['initial_amount_bs'] = round(usd * rate, 2)
        elif (bs and bs != 0) and (not usd or usd == 0):
            cleaned_data['initial_amount_usd'] = round(bs / rate, 2) if rate != 0 else 0
            
        return cleaned_data

    class Meta:
        model = Account
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nombre de la cuenta (ej. Caja Menuda, Banco Banesco)'}),
        }

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
            'name': forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Ej. Valuación 01, Fundaciones...'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.01', 'type': 'number'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'cf-input', 'step': '0.0001', 'type': 'number'}),
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
