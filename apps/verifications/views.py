import random
# from django import forms
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django_redis import get_redis_connection
from utils.captcha.captcha import captcha
from django.views import View
from django.http import HttpResponse
import logging
from celery_tasks.sms import tasks as sms_tasks
from utils.yuntongxun.sms import CCP
from verifications import constants
from verifications import forms
from user.models import Users
from utils.res_code import Code, to_json_data, error_map
import json

# 导入日志器
logger = logging.getLogger('django')


class ImageCode(View):
    """
    define image verification view
    # /image_codes/<uuid:image_code_id>/
    """

    def get(self, request, image_code_id):
        text, image = captcha.generate_captcha()
        # 确保settings.py文件中有配置redis CACHE
        # Redis原生指令参考 http://redisdoc.com/index.html
        # Redis python客户端 方法参考 http://redis-py.readthedocs.io/en/latest/#indices-and-tables
        con_redis = get_redis_connection(alias='verify_codes')
        img_key = "img_{}".format(image_code_id).encode('utf-8')
        # 将图片验证码的key和验证码文本保存到redis中，并设置过期时间
        con_redis.setex(img_key, 300, text)
        logger.info("Image code: {}".format(text))
        return HttpResponse(content=image, content_type="images/jpg")


class CheckUsernameView(View):
    def get(self, request, username):
        data = {
            'username': username,
            'count': Users.objects.filter(username=username).count()
        }

        # return JsonResponse(data=data)
        return to_json_data(data=data)


class CheckMobile(View):
    def get(self, request, mobile):
        data = {
            'mobile': mobile,
            'count': Users.objects.filter(mobile=mobile).count()
        }

        # return JsonResponse(data=data)
        return to_json_data(data=data)


class Sms_code(View):
    def post(self, request):
        " mobile  text  iamge_code_id"
        # 获取前台传过来的数据request.body
        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数为空')
        dict_data = json.loads(json_str) # json数据转化为字典
        form = forms.FromRegister(data=dict_data)

        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')
            # 生成6位短信验证码
            sms_num = '%06d' % random.randint(0, 999999)

            # 构建外键
            # 连接数据库
            con_redis = get_redis_connection(alias='verify_codes')
            # 短信建  5分钟  sms_num
            sms_text_flag = "sms_{}".format(mobile).encode('utf8')
            # 过期时间
            sms_flag_fmt = 'sms_flag_{}'.format(mobile).encode('utf8')
            # 存入redis
            pl = con_redis.pipeline() # 运用redis的管道技术，先获所有的值，然后在存入
            pl.setex(sms_text_flag, 300, sms_num)# 设置短信验证码的有效时间，后面为短信验证码
            pl.setex(sms_flag_fmt, 60, 1)  # 设置点击发送验证码的有效时间，后面为放入的值，随便写
            pl.execute() # 触发

            # 发送短信
            logger.info('短信验证码是：{}'.format(sms_num))
            logging.info('发送短信验证码正常[mobile:%s,sms_num:%s]'% (mobile,sms_num))
            return to_json_data(errmsg='短信验证码发送成功')

            # 使用celery异步处理短信发送任务
            # expires = 300
            # sms_tasks.send_sms_code.delay(mobile, sms_num, expires, 1)
            # return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")


            # 调用接口发送短信
            # try:
            #     result = CCP().send_template_sms(mobile,
            #                                      [sms_num, constants.SMS_CODE_EXPIRES],
            #                                      constants.SMS_CODE_TEMP_ID)
            # except Exception as e:
            #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
            #     return to_json_data(errno=Code.SMSERROR, errmsg=error_map[Code.SMSERROR])
            # else:
            #     if result == 0:
            #         logger.info("发送验证码短信[正常][ mobile: %s sms_code: %s]" % (mobile, sms_num))
            #         return to_json_data(errmsg='短信发送正常')
            #     else:
            #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
            #         return to_json_data(errno=Code.SMSFAIL, errmsg=error_map[Code.SMSFAIL])

        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class Modle1(View):
    def get(self,request):
        return render(request, 'md/md.html')

