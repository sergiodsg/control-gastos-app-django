import pytest
from django.contrib.auth.models import User

from organizations.models import Account, Organization, OrganizationAccess


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="tester",
        password="secret123",
        first_name="Test",
    )


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Org QA")


@pytest.fixture
def organization_access(user, organization):
    return OrganizationAccess.objects.create(user=user, organization=organization)


@pytest.fixture
def account(organization):
    return Account.objects.create(organization=organization, name="Cuenta Principal")


@pytest.fixture
def authenticated_client(client, user, organization, organization_access):
    client.force_login(user)
    session = client.session
    session["org_id"] = organization.id
    session["org_name"] = organization.name
    session.save()
    return client
