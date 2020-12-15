from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, reverse
from django.views import View
import json
from user import forms
from user.forms import LoginForm
from utils.res_code import to_json_data, Code, error_map
from .models import Users


class RegisterView(View):
    def get(self, request):
        return render(request, 'users/register.html')

    def post(self, request):
        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=[error_map[Code.PARAMERR]])
        data_dict = json.loads(json_str.decode('utf8'))
        form = forms.RegisterForm(data=data_dict)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            mobile = form.cleaned_data.get('mobile')
            user = Users.objects.create_user(username=username, password=password, mobile=mobile)
            login(request, user)
            return to_json_data(errmsg='恭喜您注册成功')
        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LoginView(View):
    def get(self, request):
        return render(request, 'users/login.html')

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))  # 没有解码，会产生bug
        form = LoginForm(data=dict_data, request=request)
        if form.is_valid():
            return to_json_data(errmsg="恭喜您，登录成功！")
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LogoutView(View):
    def get(self, request):
        logout(request)
        # 重定向，反向解析
        return redirect(reverse("news:index"))
