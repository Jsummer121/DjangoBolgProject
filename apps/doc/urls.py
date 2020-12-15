# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'doc'
urlpatterns = [
    path('', views.doc, name='index'),
    path('download/<int:doc_id>/', views.DocDownload.as_view(), name='download')
]