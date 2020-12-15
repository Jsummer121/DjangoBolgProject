from django.contrib.auth import logout
# from django.contrib.auth.mixins import LoginRequiredMixin  # 用来检查是否登录
from django.contrib.auth.mixins import PermissionRequiredMixin  # 权限
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission, Group
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from Django_pro import settings
from datetime import datetime
from .forms import NewsPubForm, DocsPubForm, CoursePubForm
from collections import OrderedDict
from urllib.parse import urlencode
from news import models
from user.models import Users
from course.models import Course, Teacher, CourseCategory
from doc.models import Doc
from utils.fastdfs.fdfs import client
import qiniu
from utils.up_qiniu import qiniu_info
from . import page_script
from utils.res_code import Code, error_map, to_json_data
import logging
import json

logger = logging.info('django')


class LoginRequiredMixin(object):
    @method_decorator(login_required(login_url='/login/'))
    def dispatch(self, request, *a, **k):
        return super(LoginRequiredMixin, self).dispatch(request, *a, **k)


class LogoutView(View):
    def get(self, request):
        logout(request)
        # 重定向，反向解析
        return redirect(reverse("admin:index"))


class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'admin/index/index.html')


class TagsManageView(LoginRequiredMixin, PermissionRequiredMixin, View):
    # 验证当前用户是否含有指定的权限
    permission_required = ('news.view_tag', 'news.add_tag', 'news.change_tag', 'news.delete_tag')

    def handle_no_permission(self):
        if self.request.method != 'GET':
            return to_json_data(errno=Code.PARAMERR, errmsg='用户没有权限')
        else:
            return super(TagsManageView, self).handle_no_permission()

    def get(self, request):
        """
        """
        # 分组查询
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(
            is_delete=False).order_by('-num_news')

        return render(request, 'admin/news/tag_manage.html', locals())

    def post(self, request):
        """
        """
        json_data = request.body  # 二进制数据
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        # 去除两端空白
        if tag_name:
            tag_name = tag_name.strip()  # 默认去掉两边
            # 如果查找到一个对象，get_or_create() 返回一个包含匹配到的对象以及False 组成的元组。
            # 如果查找不到对象， get_or_create() 将会实例化并保存一个新的对象，返回新对象组成的true元组
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            # 如果为True  走 if ，false 走 else
            return to_json_data(errmsg="标签创建成功") if tag_tuple[-1] else to_json_data(errno=Code.DATAEXIST,
                                                                                    errmsg="标签名已存在")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="标签名为空")

    def put(self, request, tag_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            if tag_name:
                tag_name = tag_name.strip()
                # 有查询集有数据就返回True ,否则返回False
                if not models.Tag.objects.only('id').filter(name=tag_name).exists():
                    tag.name = tag_name
                    tag.save(update_fields=['name'])
                    return to_json_data(errmsg="标签更新成功")
                else:
                    return to_json_data(errno=Code.DATAEXIST, errmsg="标签名已存在")
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg="标签名为空")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的标签不存在")

    def delete(self, request, tag_id):
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            tag.is_delete = True
            tag.save()
            return to_json_data(errmsg="标签删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的标签不存在")


class HotNewsManageView(LoginRequiredMixin, View):

    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news').only('news_id', 'news__title',
                                                                      'news__tag__name').filter(
            is_delete=False).order_by('priority', '-news__clicks')[0:3]
        return render(request, 'admin/news/news_hot.html', locals())


class HotNewsEditView(LoginRequiredMixin, View):

    def delete(self, request, hotnews_id):
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if hotnews:
            hotnews.is_delete = True
            hotnews.save(update_fields=['is_delete'])
            return to_json_data(errmsg="热门文章删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的热门文章不存在")

    def put(self, request, hotnews_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRT_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='格式错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()

        if not hotnews:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的热门文章不存在")

        if hotnews.priority == priority:
            return to_json_data(errno=Code.PARAMERR, errmsg="热门文章的优先级未改变")

        hotnews.priority = priority
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg="热门文章优先级更新成功")


class HotNewsAddView(LoginRequiredMixin, View):

    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')). \
            filter(is_delete=False).order_by('-num_news')
        # 优先级列表
        # priority_list = {K: v for k, v in models.HotNews.PRI_CHOICES}
        priority_dict = OrderedDict(models.HotNews.PRT_CHOICES)

        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('前端传过来的文章id参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRT_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        # 创建热门新闻
        try:
            hotnews_trup = models.HotNews.objects.get_or_create(news_id=news_id, priority=priority)
            return to_json_data(errmsg="热门文章创建成功") if hotnews_trup[-1] else to_json_data(errno=Code.DATAEXIST,
                                                                                         errmsg="该热门文章已存在")
        except:
            return to_json_data(errno=Code.DATAEXIST, errmsg='该热门文章已存在，如果要修改优先级请到上级操作')


# 根据tag_id来查出该id下的所有的新闻
class NewsByTagIdView(LoginRequiredMixin, View):
    """
    route: /admin/tags/<int:tag_id>/news/
    """

    def get(self, request, tag_id):
        newses = models.News.objects.values('id', 'title').filter(is_delete=False, tag_id=tag_id)
        news_list = [i for i in newses]
        return to_json_data(data={'news': news_list})


class NewsManage(LoginRequiredMixin, View):
    def get(self, request):
        # 处理时间
        start_time = request.GET.get('start_time', '')
        # 2019/12/12  把字符串格式转乘 日期格式
        start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''
        end_time = request.GET.get('end_time', '')
        end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''

        newses = models.News.objects.only('title', 'author__username', 'tag__name', 'update_time').filter(
            is_delete=False)
        # 单选开始 没选结束    返回比开始时间大的数据
        if start_time and not end_time:
            newses = newses.filter(update_time__gte=start_time)
            # 单选结束 没选开始    返回比结束时间小的数据
        if end_time and not start_time:
            newses = newses.filter(update_time__lte=end_time)
            # 结束 开始都有    返回开始和结束实时间之间的数据
        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))

        # 处理标题   模糊查询
        title = request.GET.get('title', '')
        if title:
            # icontains忽略大小写
            newses = newses.filter(title__icontains=title)
        # 作者处理 模糊查询
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)
        # 处理分类
        tags = models.Tag.objects.only('name').filter(is_delete=False)
        tag_id = int(request.GET.get('tag_id', 0))
        newses = newses.filter(is_delete=False, tag_id=tag_id) or newses.filter(is_delete=False)
        # 处理分页
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info('页面错误')
            page = 1

        pt = Paginator(newses, 6)
        try:
            news_info = pt.page(page)
        except EmptyPage:
            logger.info('页码错误')
            news_info = pt.page(pt.num_pages)

        # 自定义分页器
        pages_data = page_script.get_page_data(pt, news_info)
        # 把日期格式转字符串格式
        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if end_time else ''

        data = {
            'news_info': news_info,
            'tags': tags,
            'paginator': pt,
            'start_time': start_time,
            'end_time': end_time,
            'title': title,
            'author_name': author_name,
            'tag_id': tag_id,
            'other_param': urlencode({
                'start_time': start_time,
                'end_time': end_time,
                'title': title,
                'author_name': author_name,
                'tag_id': tag_id,
            })
        }
        data.update(pages_data)

        return render(request, 'admin/news/news_manage.html', context=data)


class NewsEditView(LoginRequiredMixin, View):
    def get(self, request, news_id):
        news = models.News.objects.filter(id=news_id, is_delete=False).first()
        if news:
            tags = models.Tag.objects.only('name').filter(is_delete=False)
            data = {
                'news': news,
                'tags': tags
            }
            return render(request, 'admin/news/news_pub.html', context=data)
        else:
            raise Http404('资源不存在')

    def delete(self, request, news_id):
        news = models.News.objects.only('id').filter(is_delete=False, id=news_id).first()
        if news:
            news.is_delete = True
            news.save()
            return to_json_data(errmsg='文章删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='该文章删除失败')

    def put(self, request, news_id):
        """
        title  digest tag image_url content
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.filter(id=news_id, is_delete=False).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        js_str = request.body
        if not js_str:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        dict_data = json.loads(js_str)
        # 清洗数据
        form = NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.tag = form.cleaned_data.get('tag')
            news.image_url = form.cleaned_data.get('image_url')
            news.content = form.cleaned_data.get('content')
            news.save()
            return to_json_data(errmsg='文章更新成功')
        else:
            err_m_l = []
            for i in form.errors.values():
                err_m_l.append(i[0])
            err_msg_str = '/'.join(err_m_l)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


# 正常的图片上传服务器
class Up_img_server(LoginRequiredMixin, View):
    def post(self, request):
        image_file = request.FILES.get('image_file')
        if not image_file:
            return to_json_data(errno=Code.PARAMERR, errmsg='文件获取失败')

        if image_file.content_type not in ('image/jpeg', 'image/gif', 'image/png'):
            return to_json_data(errno=Code.PARAMERR, errmsg='不能上传非图片文件')

        try:  # jpg
            image_ext_name = image_file.name.split('.')[-1]  # 切割后返回列表取最后一个元素尾缀
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'
        # 上传
        try:
            upload_img = client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.info('图片上传失败{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传失败')
        else:
            if upload_img.get('Status') != 'Upload successed.':
                logger.info('图片上传失败')
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.PARAMERR])
            else:
                img_name = upload_img.get('Remote file_id')
                image_url = settings.FDFS_URL + img_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功')


# 在MARKDOWN里面上传图片
@method_decorator(csrf_exempt, name='dispatch')
class MarkDownUploadImage(LoginRequiredMixin, View):
    def post(self, request):
        image_file = request.FILES.get('editormd-image-file')  # 记得这个不要写错啦
        if not image_file:
            logger.info('从前端获取图片失败')
            return JsonResponse({'success': 0, 'message': '图片未获取'})
        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return JsonResponse({'success': 0, 'message': '不能上传非图片文件'})

        try:  # 取到图片的后缀名 jpg
            image_ext_name = image_file.name.split('.')[-1]  # 切割后返回列表取最后一个元素尾缀
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.info('图片上传出现异常：{}'.format(e))
            return JsonResponse({'success': 0, 'message': '上传异常'})
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return JsonResponse({'success': 0, 'message': '图片不能上传到服务器'})
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FDFS_URL + image_name
                return JsonResponse({'success': 1, 'message': '上传成功', 'url': image_url})


# 新闻上传
class NewsPub(LoginRequiredMixin, View):
    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())

    def post(self, request):
        """
        获取表单数据 标题  摘要 图片 文本内容
        数据清洗/判断是否合法
        保存到数据库
        :param request:
        :return:
        """
        json_str = request.body
        if not json_str:
            to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        dict_data = json.loads(json_str)

        # 数据清洗
        form = NewsPubForm(data=dict_data)
        if form.is_valid():
            # 对于作者更新对于的新闻， 知道新闻是哪个作者发布的
            # 创建实例  不保存到数据库
            newss = form.save(commit=False)
            newss.author_id = request.user.id
            newss.save()
            return to_json_data(errmsg='文章发布成功')
        else:
            err_m_l = []
            for i in form.errors.values():
                err_m_l.append(i[0])
            err_msg_str = '/'.join(err_m_l)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class BannerView(LoginRequiredMixin, View):
    def get(self, request):
        banners = models.Banner.objects.only('id', 'image_url', 'priority').filter(is_delete=False)
        priority_dict = OrderedDict(models.Banner.PRT_CHOICES)
        return render(request, 'admin/news/news_banner.html', locals())


class BannerEditView(LoginRequiredMixin, View):
    def delete(self, request, b_id):
        banners = models.Banner.objects.only('id').filter(is_delete=False, id=b_id).first()
        if banners:
            banners.is_delete = True
            banners.save(update_fields=['is_delete'])
            return to_json_data(errmsg='轮播图删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='查找的轮播图不存在')

    # 编辑用put，添加用post
    def put(self, request, b_id):
        """
        1, 获取参数    priority   image_url
        2，校验参数
        3，保存并返回
        :param b_id:
        :return:
        """
        banners = models.Banner.objects.only('id').filter(is_delete=False, id=b_id).first()
        if not banners:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图不存在')

        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg='获取参数失败')
        dict_data = json.loads(json_str)

        # 获取参数  优先级
        priority = int(dict_data.get('priority'))  # 整形
        priority_list = [i for i, _ in models.Banner.PRT_CHOICES]

        if priority not in priority_list:
            return to_json_data(errno=Code.PARAMERR, errmsg='优先级不存在')

        image_url = dict_data['image_url']
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='图片数据为空')

        # 判断是否已修改

        if banners.priority == priority and banners.image_url == image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='数据没有修改')

        # 保存到数据库
        banners.priority = priority  # 1 2 3 4  5 6  看他的值
        banners.image_url = image_url

        banners.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg='轮播图更新成功')


class AddBannerView(LoginRequiredMixin, View):
    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(
            is_delete=False).order_by('num_news', 'update_time')
        # 优先级列表
        priority_dict = OrderedDict(models.Banner.PRT_CHOICES)
        return render(request, 'admin/news/banner_add.html', locals())

    def post(self, request):
        """
        获取参数     # news_id   priority  image_url
        校验参数
        保存
        返回
        :param request:
        :return:
        """  # int   int         str
        json_str = request.body  # news_id   priority  image_url
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        dict_data = json.loads(json_str)

        # 校验参数
        news_id = int(dict_data.get('news_id'))

        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='新闻不存在')
        try:
            priority = int(dict_data.get('priority'))

            priority_list = [i for i, _ in models.Banner.PRT_CHOICES]

            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级错误')
        except Exception as e:
            logger.info('轮播图优先级异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级错误')

        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级为空')

        # 创建轮播图  obj  true
        # 创建实例  保存到数据库
        banner = models.Banner.objects.get_or_create(news_id=news_id, priority=priority)
        banners, is_cre = banner
        banners.priority = priority
        banners.image_url = image_url
        banners.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg='轮播图创建成功')


class DocManageView(LoginRequiredMixin, View):
    def get(self, request):
        docs = Doc.objects.only('title', 'create_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', context={'docs': docs})


class DocEditView(View):
    def get(self, request, doc_id):
        doc = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if doc:
            return render(request, 'admin/doc/doc_pub.html', context={'doc': doc})
        else:
            raise Http404('PAGE NOT FOUND')

    def put(self, request, doc_id):
        """
        1，获取参数
        2，数据清洗，通过表单
        3，保存到数据库
        4，返回
        :param request:
         "title": sTitle,
         "desc": sDesc,
        "image_url": sThumbnailUrl,
        "file_url": sDocFileUrl,
        :return:
        """
        docs = Doc.objects.filter(id=doc_id).first()
        if not docs:
            return to_json_data(errno=Code.PARAMERR, errmsg='文档不存在')
        js_dtr = request.body
        dict_data = json.loads(js_dtr)
        # print(dict_data)
        # 数据清洗 表单
        form = DocsPubForm(data=dict_data)
        if form.is_valid():
            for key, value in form.cleaned_data.items():
                # print(key)
                # print(value)
                setattr(docs, key, value)
            # docs.title = form.cleaned_data.get('title')
            # docs.desc = form.cleaned_data.get('desc')
            # docs.image_url = form.cleaned_data.get('image_url')
            # docs.file_url = form.cleaned_data.get('file_url')
            docs.save()
            return to_json_data(errmsg='更新成功')

        else:
            err_m_l = []
            for i in form.errors.values():
                err_m_l.append(i[0])
            err_msg_str = '/'.join(err_m_l)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

    def delete(self, request, doc_id):
        docs = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if docs:
            docs.is_delete = True
            docs.save(update_fields=['is_delete'])
            return to_json_data(errmsg='文档删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='查找的文档不存在')


# 文件上传服务器
class DocUpFile(LoginRequiredMixin, View):
    def post(self, request):
        # 键来源于js
        text_files = request.FILES.get('text_files')
        if not text_files:
            return to_json_data(errno=Code.PARAMERR, errmsg='文件获取失败')

        if text_files.content_type not in ('application/zip', 'application/pdf', 'text/plain', 'application/msowrd'):
            return to_json_data(errno=Code.PARAMERR, errmsg='不能上传非文本吧文件')

        file_ext_name = text_files.name.split('.')[-1]
        # 上传
        try:
            upload_doc = client.upload_by_buffer(text_files.read(), file_ext_name=file_ext_name)
        except Exception as e:
            logger.error('文件上传失败{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传失败')
        else:
            if upload_doc.get('Status') != 'Upload successed.':
                logger.info('文件上传失败')
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.PARAMERR])
            else:
                file_name = upload_doc.get('Remote file_id')
                file_url = settings.FDFS_URL + file_name
                return to_json_data(data={'text_file': file_url}, errmsg='文档上传成功')


class DocsPubView(LoginRequiredMixin, View):
    """
    route: /admin/news/pub/
    """

    def get(self, request):
        return render(request, 'admin/doc/doc_pub.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = DocsPubForm(data=dict_data)
        if form.is_valid():
            docs_instance = form.save(commit=False)
            docs_instance.author_id = request.user.id
            docs_instance.save()
            return to_json_data(errmsg='文档创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class CourseManageView(LoginRequiredMixin, View):
    def get(self, request):
        courses = Course.objects.select_related('category', 'teacher').only('title', 'category__name',
                                                                            'teacher__name').filter(is_delete=False)
        return render(request, 'admin/course/course_manage.html', locals())


class CourseEditView(LoginRequiredMixin, View):
    def get(self, request, course_id):
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if course:
            teachers = Teacher.objects.only('name').filter(is_delete=False)
            categories = CourseCategory.objects.only('name').filter(is_delete=False)
            return render(request, 'admin/course/news_pub.html', locals())
        else:
            Http404('需要更新的课程不存在')

    def delete(self, request, course_id):
        course = Course.objects.only('id').filter(is_delete=False, id=course_id).first()
        if course:
            course.is_delete = True
            course.save(update_fields=['is_delete'])
            return to_json_data(errmsg='课程删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='更新的课程不存在')

    def put(self, request, course_id):
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if not course:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的课程不存在')
        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_str.decode('utf8'))
        form = CoursePubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(course, attr, value)
            course.save()
            return to_json_data(errmsg='课程更新成功')
        else:
            # 定义一个错误信息列表
            err_m_l = []
            for i in form.errors.values():
                err_m_l.append(i[0])
            err_msg_str = '/'.join(err_m_l)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class CoursePubView(LoginRequiredMixin, View):
    """
    "title": sTitle,
    "profile": sDesc,
    "cover_url": sThumbnailUrl,
    "video_url": sCourseFileUrl,
    "outline": sContentHtml,
    "teacher": sTeacherId,
    "category": sCategoryId
    """

    def get(self, request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request, 'admin/course/news_pub.html', locals())

    def post(self, request):
        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        data_dict = json.loads(json_str.decode('utf8'))
        form = CoursePubForm(data=data_dict)
        if form.is_valid():
            course_instance = form.save(commit=False)
            course_instance.save()
            return to_json_data(errmsg='课程发布成功')
        else:
            # 定义一个错误信息列表
            err_m_l = []
            for i in form.errors.values():
                err_m_l.append(i[0])
            err_msg_str = '/'.join(err_m_l)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class GroupsManageView(LoginRequiredMixin, View):
    def get(self, request):
        group = Group.objects.values('id', 'name').annotate(num_users=Count('user')).order_by('num_users')
        return render(request, 'admin/user/groups_manage.html', context={'groups': group})


class GroupsEdit(LoginRequiredMixin, View):
    def get(self, request, g_id):
        group = Group.objects.filter(id=g_id).first()
        if group:
            per = Permission.objects.only('id').all()  # 获取权限
            return render(request, 'admin/user/groups_add.html', context={'group': group, 'permissions': per})
        else:
            raise Http404('PAGE NOT FOUND')

    def put(self, request, g_id):
        """
        1, 获取参数   组名  权限
        2，数据清洗
        3，保存
        4，返回
        :param request:
        :param g_id:
        :return:
        """
        group = Group.objects.filter(id=g_id).first()
        if not group:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        js_str = request.body
        dict_data = json.loads(js_str)
        # 组名
        g_name = dict_data.get('name', '').strip()  # 男人团
        if not g_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        if g_name != group.name and Group.objects.filter(name=g_name).exists():
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名存在')

        # 权限校验
        g_permission = dict_data['group_permission']  # [1,2,3,4,5]
        if not g_permission:
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        per_set = set(i for i in g_permission)
        # print(per_set)
        # 去数据库取数据
        db_per_set = set(i.id for i in group.permissions.all())
        if per_set == db_per_set:
            return to_json_data(errno=Code.DATAEXIST, errmsg='用户在没有修改')

        # 设置权限 保存
        for i in per_set:
            p = Permission.objects.get(id=i)
            group.permissions.add(p)

        group.name = g_name
        group.save()
        return to_json_data(errmsg='组创建成功')

    def delete(self, request, g_id):
        gp = Group.objects.filter(id=g_id).first()
        if gp:
            gp.permissions.clear()
            gp.delete()
            return to_json_data(errmsg='删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='删除的组不存在')


class GroupsAddView(LoginRequiredMixin, View):
    """
    route: /admin/groups/add/
    """

    def get(self, request):
        permissions = Permission.objects.only('id').all()
        return render(request, 'admin/user/groups_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出组名，进行判断
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')

        one_group, is_created = Group.objects.get_or_create(name=group_name, )
        if not is_created:
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在')

        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')

        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')

        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')

        # 设置权限
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            one_group.permissions.add(p)

        one_group.save()
        return to_json_data(errmsg='组创建成功！')


# 七牛云上传
class UploadToken(LoginRequiredMixin, View):
    def get(self, request):
        access_key = qiniu_info.QINIU_ACCESS_KEY
        secret_key = qiniu_info.QINIU_SECRET_KEY
        bucket_name = qiniu_info.QINIU_BUCKET_NAME
        # 构建鉴权对象
        q = qiniu.Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)

        return JsonResponse({"uptoken": token})


class UsersManageView(LoginRequiredMixin, View):
    """
    route: /admin/users/
    """
    def get(self, request):
        users = Users.objects.only('username', 'is_staff', 'is_superuser').filter(is_active=True)
        return render(request, 'admin/user/users_manage.html', locals())


class UsersEditView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            groups = Group.objects.only('name').all()
            return render(request, 'admin/user/users_edit.html', locals())
        else:
            raise Http404('更新得用户组不存在')

    def put(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if not user_instance:
            return to_json_data(errno=Code.NODATA, errmsg='无数据')

        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.NODATA])

        dict_data = json.loads(json_str)
        try:
            groups = dict_data.get('groups')
            is_superuser = int(dict_data['is_superuser'])  # 0
            is_staff = int(dict_data.get('is_staff'))  # 1
            is_active = int(dict_data['is_active'])  # 1
            params = (is_active, is_staff, is_superuser)
            if not all([q in (0, 1) for q in params]):
                return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        except Exception as e:
            logger.info('从前端获取得用户参数错误{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        try:
            if groups:
                groups_set = set(int(i) for i in groups)
            else:
                groups_set = set()
        except Exception as e:
            logger.info('用户组参数异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组参数异常')

        # 组
        all_groups_set = set(i.id for i in Group.objects.only('id'))
        # 判断前台传得组是否在所有用户组里面
        if not groups_set.issubset(all_groups_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的用户组参数')

        gsa = Group.objects.filter(id__in=groups_set)  # [1,3,4]

        # 保存
        user_instance.groups.clear()
        user_instance.groups.set(gsa)
        user_instance.is_staff = bool(is_staff)
        user_instance.is_superuser = bool(is_superuser)
        user_instance.is_active = bool(is_active)
        user_instance.save()
        return to_json_data(errmsg='用户组更新成功')

    def delete(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            user_instance.groups.clear()  # 去除用户组
            user_instance.user_permissions.clear()  # 清楚用户权限
            user_instance.is_active = False
            user_instance.save()
            return to_json_data(errmsg='用户删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的用户不存在')
