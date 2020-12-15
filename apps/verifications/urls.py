# -*- coding: utf-8 -*-
from django.urls import path, re_path

from . import views

app_name = "verifications"

urlpatterns = [
    # 路由里的正则,使用（？P开头<>里面为得到的变量名，后面则为正则的表达式，\d为数字{里面为匹配几个},\w为匹配字符，同样{里面为匹配几个}）
    # 路由如果在后面添加了/那你在输入时，不管你是否在浏览器内输入最后的/都会转到相应的网页，但是如果路由后面不加/，你在浏览器里加了/,则会导致浏览不成功。
    # image_code_id为uuid格式
    path('image_code/<uuid:image_code_id>/', views.ImageCode.as_view(), name='image_code'),
    re_path('username/(?P<username>\w{5,20})/',views.CheckUsernameView.as_view(), name='username'),
    re_path('mobile/(?P<mobile>1[3-9]\d{9})/',views.CheckMobile.as_view(), name='mobile'),
    path('sms_code/', views.Sms_code.as_view(), name='sms_code'),
    path('md/', views.Modle1.as_view(),name='123')
]
