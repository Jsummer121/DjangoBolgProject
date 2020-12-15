import json
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import F
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.views import View
import logging
from utils.res_code import to_json_data, Code, error_map
from . import models
from django.contrib.auth.decorators import login_required
from haystack.views import SearchView

logger = logging.info('django')
# Create your views here.
class IndexView(View):
    # 热门新闻
    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        hot_news = models.HotNews.objects.select_related('news').only('news__title', 'news__image_url', 'news_id').filter(is_delete=False).order_by('priority', '-news__clicks')[0:3]
        return render(request, 'news/index.html', locals())


# 这边使用的是硬编码--（直接在端口号后面添加后面的路由）
# @login_required(login_url='/login/')
# def demo(request):
#     return render(request, 'news/search.html')


class NewsListView(View):
    def get(self, request):
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.error('页面或标签定义错误\n{}'.format(e))
            tag_id = 0
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.error('页面或标签定义错误\n{}'.format(e))
            page = 1

        news_list = models.News.objects.select_related('tag', 'author').only('id', 'title', 'digest', 'image_url',
                                                                             'author__username', 'update_time',
                                                                             'tag__name').filter(is_delete=False)  # 一般
        # news_list = models.News.objects.values('id', 'title', 'digest', 'image_url', 'update_time').annotate(tag_name=F('tag__name'), author=F('author__username'))
        news = news_list.filter(is_delete=False, tag_id=tag_id) or news_list.filter(is_delete=False)

        # 分页  带分页对象 分页数量
        paginator = Paginator(news, 4)
        try:
            news_info = paginator.page(page)
        except Exception as e:
            logger.info('给定的页码错误\n{}'.format(e))
            news_info = paginator.page(paginator.num_pages)

        news_info_list = []
        for n in news_info:
            news_info_list.append({
                'id': n.id,
                'title': n.title,
                'digest': n.digest,
                'author': n.author.username,
                'image_url': n.image_url,
                'tag_name': n.tag.name,
                'update_time': n.update_time.strftime('%Y年%m月%d日 %H:%M')
            })

        data = {
            "news": news_info_list,
            # "news": list(news_info),
            "total_pages": paginator.num_pages,
        }
        return to_json_data(data=data)


class Banner_View(View):
    def get(self, request):
        # banners = models.Banner.objects.select_related('news').only('image_url', 'news__title', 'news_id').filter(is_delete=False)
        # annotate为外键连接，news_id=F('news__id'),前面为关键字，后面的__前面为数据表名，后面的为字段名
        banners = models.Banner.objects.values('image_url').annotate(news_id=F('news__id'), news_title=F('news__title'))

        # banner_info = []
        # for i in banners:
        #     banner_info.append({
        #         'image_url': i.image_url,
        #         'news_id': i.news.id,  # ID 传给前台做轮播图详情页渲染
        #         'news_title': i.news.title
        #     })
        data = {
            'banners': list(banners)
        }

        return to_json_data(data=data)


class News_detail(View):
    def get(self, request, news_id):
        news = models.News.objects.select_related('tag', 'author').only('title', 'content', 'update_time', 'tag__name',
                                                                        'author__username').filter(is_delete=False,
                                                                                                   id=news_id).first()

        comments = models.Comments.objects.select_related('author', 'parent').only('author__username', 'update_time',
                                                                                   'parent__update_time').filter(
            is_delete=False, news_id=news_id)
        comments_list = []
        for comm in comments:
            comments_list.append(comm.to_dict_data())

        if news:
            return render(request, 'news/news_detail.html', locals())
        else:
            return HttpResponseNotFound('PAGE NOT FOUND')


# 追加评论数据
class Comment_View(View):
    """
       /news/<int:news_id>/comments/
       1, 判断用户是否已登录
       2，获取参数
       3，校验参数
       4，保存到数据库
       """

    def post(self, request, news_id):
        if not request.user.is_authenticated:
            return to_json_data(errno=Code.SESSIONERR, errmsg=error_map[Code.SESSIONERR])

        if not models.News.objects.only('id').filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='新闻不存在！')

            # 2 获取参数
        json_data = request.body  # 一个汉字几个字节
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        dict_data = json.loads(json_data.decode('utf8'))

        #  一级评论内容
        content = dict_data.get('content')
        if not dict_data.get('content'):
            return to_json_data(errno=Code.PARAMERR, errmsg='评论内容不能为空！')

        # 回复评论 ---  二级评论
        parent_id = dict_data.get('parent_id')
        try:
            if parent_id:
                if not models.Comments.objects.only('id').filter(is_delete=False, id=parent_id,
                                                                 news_id=news_id).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        except Exception as e:
            logging.info('前台传的parent_id 异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='未知异常')

        # 保存数据库
        news_content = models.Comments()
        news_content.content = content
        news_content.news_id = news_id
        news_content.author = request.user
        news_content.parent_id = parent_id if parent_id else None
        news_content.save()
        return to_json_data(data=news_content.to_dict_data())


class Search(SearchView):
    template = 'news/search.html'

    def create_response(self):
        # 接收前台用户输入的查询值
        # kw='python'
        query = self.request.GET.get('q', '')
        if not query:
            show = True
            host_news = models.HotNews.objects.select_related('news').only('news_id', 'news__title',
                                                                           'news__image_url').filter(
                is_delete=False).order_by('priority')
            paginator = Paginator(host_news, 5)
            try:
                page = paginator.page(int(self.request.GET.get('page', 1)))
            # 假如传的不是整数
            except PageNotAnInteger:
                # 默认返回第一页
                page = paginator.page(1)

            except EmptyPage:
                page = paginator.page(paginator.num_pages)
            return render(self.request, self.template, locals())
        else:
            # 重新进行一次查找
            show = False
            return super().create_response()
