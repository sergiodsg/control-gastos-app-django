from datetime import date

import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from .models import Organization, OrganizationAccess, Project, Transaction, Account, Category, ProjectOrganizationAccess, ProjectUserAccess

class TransactionAccessTest(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password')
        self.org_a = Organization.objects.create(name='Org A')
        OrganizationAccess.objects.create(user=self.user_a, organization=self.org_a)
        
        self.org_b = Organization.objects.create(name='Org B')
        
        self.project_p = Project.objects.create(name='Project P', organization=self.org_b)
        
        # Share project P with Org A
        ProjectOrganizationAccess.objects.create(project=self.project_p, organization=self.org_a)
        # Give User A access to project P
        ProjectUserAccess.objects.create(user=self.user_a, project=self.project_p)
        
        self.account_b = Account.objects.create(
            organization=self.org_b,
            currency=Account.CURRENCY_BS,
            bank_code='0102',
            bank_name='Banco de Venezuela, S.A. Banco Universal',
            rif='J123456789',
            account_number='01021234567890123456',
            holder='Titular de Prueba',
            name='Account B',
        )
        self.category_b = Category.objects.create(organization=self.org_b, name='Category B')
        
        self.transaction = Transaction.objects.create(
            date=date.today(),
            organization=self.org_b,
            account=self.account_b,
            description='Test Trans',
            amount_bs=100,
            amount_usd=10,
            daily_rate=10,
            project=self.project_p,
            category=self.category_b,
            status='completado'
        )
        
        self.client = Client()
        self.client.login(username='user_a', password='password')
        
        # Set org_id in session
        session = self.client.session
        session['org_id'] = self.org_a.id
        session.save()

    def test_edit_shared_project_transaction_success(self):
        """
        Verify that editing a transaction from another organization
        works if it belongs to a shared project the user has access to.
        """
        url = reverse('editar_transaccion', kwargs={'trans_id': self.transaction.id})
        data = {
            'date': self.transaction.date,
            'organization': self.org_b.id,
            'account': self.account_b.id,
            'description': 'Updated Trans',
            'amount_bs': 200, # Revenue (positive)
            'amount_usd': 20,
            'daily_rate': 10,
            'project': self.project_p.id,
            'category': self.category_b.id,
            'status': 'completado',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify transaction was updated
        self.transaction.refresh_from_db()
        self.assertEqual(float(self.transaction.amount_bs), 200.0)
        self.assertEqual(self.transaction.description, 'Updated Trans')

    def test_detail_shared_project_transaction_success(self):
        """
        Verify that viewing details of a transaction from another organization
        works if it belongs to a shared project the user has access to.
        """
        url = reverse('detalle_transaccion', kwargs={'trans_id': self.transaction.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.transaction.description)

    def test_delete_shared_project_transaction_success(self):
        """
        Verify that deleting a transaction from another organization
        works if it belongs to a shared project the user has access to.
        """
        url = reverse('eliminar_transaccion', kwargs={'trans_id': self.transaction.id})
        # Use POST for delete
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(id=self.transaction.id).exists())


@pytest.mark.django_db
def test_usuario_normal_no_crea_cuenta_con_banco_invalido(client, capsys, settings):
    settings.DEBUG = True

    user = User.objects.create_user(username='usuario_normal', password='password')
    org = Organization.objects.create(name='Org Normal')
    OrganizationAccess.objects.create(user=user, organization=org)

    client.force_login(user)
    session = client.session
    session['org_id'] = org.id
    session['org_name'] = org.name
    session.save()

    response = client.post(reverse('crear_cuenta'), {
        'currency': Account.CURRENCY_BS,
        'bank_code': '9999',
        'bank_name': 'Banco Inexistente',
        'rif': 'J-12345678-9',
        'account_number': '01021234567890123456',
        'holder': 'Titular de Prueba',
        'initial_balance': '100.00',
        'daily_rate': '36.5000',
    }, follow=True)

    messages = [str(message) for message in get_messages(response.wsgi_request)]
    captured = capsys.readouterr()
    debug_output = captured.out + captured.err

    assert response.status_code == 200
    assert user.is_superuser is False
    assert Account.objects.filter(organization=org).count() == 0
    assert Transaction.objects.filter(organization=org).count() == 0
    assert any('Seleccione un banco válido en bolívares.' in message for message in messages)
    assert 'cuenta.guardar.error' in debug_output
