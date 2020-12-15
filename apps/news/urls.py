# -*- coding: utf-8 -*-
from django.urls import path
from news import views

app_name = 'news'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # path('demo/', views.demo),
    path('news/<int:news_id>/', views.News_detail.as_view(), name='news_detail'),
    path('news/', views.NewsListView.as_view(), name='news_list'),
    path('news/banners/', views.Banner_View.as_view(), name='news_banner'),
    path('news/<int:news_id>/comments/', views.Comment_View.as_view(), name='comments'),
    path('search/', views.Search(), name='search'),
]
