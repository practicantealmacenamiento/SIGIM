"""Pruebas del catálogo de actores (equivalente funcional a 'gerencias')."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from app.infrastructure.models import Actor


class CatalogoActoresAPITest(TestCase):
    endpoint_name = "actors-list"

    def setUp(self):
        super().setUp()
        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append("testserver")
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password="seguro123",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_listado_filtra_por_tipo(self):
        Actor.objects.create(tipo=Actor.Tipo.PROVEEDOR, nombre="[TEST] Proveedor 1")
        Actor.objects.create(tipo=Actor.Tipo.TRANSPORTISTA, nombre="[TEST] Transportista 1")
        Actor.objects.create(tipo=Actor.Tipo.RECEPTOR, nombre="[TEST] Receptor 1")

        url = reverse(self.endpoint_name)
        response = self.client.get(url, {"tipo": "proveedor", "search": "[TEST]"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(len(payload) >= 1)
        self.assertTrue(all(actor["tipo"] == Actor.Tipo.PROVEEDOR for actor in payload))
        self.assertIn("[TEST] Proveedor 1", [actor["nombre"] for actor in payload])

    def test_busqueda_por_nombre_y_limit(self):
        for idx in range(5):
            Actor.objects.create(
                tipo=Actor.Tipo.PROVEEDOR,
                nombre=f"[TEST] Proveedor {idx}",
                documento=f"900{idx:03d}"
            )

        url = reverse(self.endpoint_name)
        response = self.client.get(url, {"search": "[TEST]", "limit": 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(len(payload), 3)
        self.assertTrue(all(actor["nombre"].startswith("[TEST]") for actor in payload))

    def test_autenticacion_requerida(self):
        url = reverse(self.endpoint_name)
        client = APIClient()
        response = client.get(url)

        self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})
