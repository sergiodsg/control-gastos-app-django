from django import forms
from .models import Transaction, Category, Account, Project, Valuation

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'date', 'account', 'reference_number', 'description', 
            'notes', 'category', 'project', 'valuation', 
            'status', 'amount_bs', 'amount_usd', 'daily_rate'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nro. Referencia'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción de la transacción'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas adicionales'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'valuation': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'type': 'number'}),
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
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['category'].queryset = Category.objects.filter(organization=organization)
            self.fields['account'].queryset = Account.objects.filter(organization=organization)
            self.fields['project'].queryset = Project.objects.filter(organization=organization)
            self.fields['valuation'].queryset = Valuation.objects.filter(project__organization=organization)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Breve descripción'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'height: 38px; width: 60px; padding: 2px;'}),
        }

class AccountForm(forms.ModelForm):
    initial_amount_usd = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False, label="Monto inicial (USD)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'})
    )
    initial_amount_bs = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False, label="Monto inicial (BS)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'})
    )
    daily_rate = forms.DecimalField(
        max_digits=20, decimal_places=4, required=False, label="Tasa del día (para monto inicial)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'type': 'number'})
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
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la cuenta (ej. Caja Menuda, Banco Banesco)'}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proyecto'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del proyecto'}),
        }

class ValuationForm(forms.ModelForm):
    class Meta:
        model = Valuation
        fields = ['name', 'amount_usd', 'amount_bs', 'daily_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Valuación 01, Fundaciones...'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'}),
            'amount_bs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'type': 'number'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'type': 'number'}),
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

