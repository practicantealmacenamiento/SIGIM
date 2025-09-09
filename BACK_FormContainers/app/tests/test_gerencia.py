import pytest
from rest_framework.test import APIClient
from rest_framework import status

""" Ejemplo practico de prueba unitaria para la API de Gerencia """
@pytest.mark.django_db
class TestGerenciaAPI:
    endpoint = '/app/api/gerencias/'

    def test_list_gerencias(self):
        client = APIClient()
        response = client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK


#Ejecución prueba 1
# pytest -v SERVICE_bia/bia/tests/test_gerencia.py::TestGerenciaAPI::test_create_gerencia

# Ejecución prueba 2
# pytest -v SERVICE_bia/bia/tests/test_gerencia.py::TestGerenciaAPI::test_list_gerencias