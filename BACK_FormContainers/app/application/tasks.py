"""
    Registra aca las tareas de Celery que necesites para tu aplicación.
    Puedes crear tareas para enviar correos, procesar datos, etc.
"""
from celery import shared_task

@shared_task
def sharedtask():
    return 