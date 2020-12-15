from django.urls import path
from . import views

app_name = 'courses'
urlpatterns = [
    path('', views.demo, name='demo'),
    path('detail/<int:course_id>/', views.CourseDetail.as_view(), name='course_detail'),
]
