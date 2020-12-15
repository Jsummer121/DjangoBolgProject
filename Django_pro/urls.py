"""Django_pro URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
                  path('', include('news.urls')),  # 设置为根目录，是为了直接可以请求首页。
                  path('', include('user.urls')),
                  path('', include('verifications.urls')),  # 设置为根目录，是为了方便后台的数据请求。
                  path('course/', include('course.urls')),  # 视频文件
                  path('doc/', include('doc.urls')),  # 书籍文件
                  path('admin/', include('admin.urls'))
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
