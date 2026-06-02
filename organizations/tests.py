from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Organization, OrganizationAccess, Project, Transaction, Account, Category, ProjectOrganizationAccess, ProjectUserAccess
from datetime import date

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
        
        self.account_b = Account.objects.create(organization=self.org_b, name='Account B')
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
