from django.urls import path
from . import views

# app的名字
app_name = 'admin'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),  # 将这条路由命名为index
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('tags/', views.TagsManageView.as_view(), name='tags'),
    path('tags/<int:tag_id>/', views.TagsManageView.as_view(), name='tags_manage'),
    path('tags/<int:tag_id>/news/', views.NewsByTagIdView.as_view(), name='news_by_tagid'),
    path('hotnews/', views.HotNewsManageView.as_view(), name='hotnews_manage'),
    path('hotnews/<int:hotnews_id>/', views.HotNewsEditView.as_view(), name='hotnews_edit'),
    path('hotnews/add/', views.HotNewsAddView.as_view(), name='hotnews_add'),
    path('news/', views.NewsManage.as_view(), name='news_manage'),
    path('news/<int:news_id>/', views.NewsEditView.as_view(), name='news_edit'),
    path('news/images/', views.Up_img_server.as_view(), name='up_image'),
    path('markdown/images/', views.MarkDownUploadImage.as_view(), name='markdown_image_upload'),
    path('news/pub/', views.NewsPub.as_view(), name='news_pub'),
    path('banners/', views.BannerView.as_view(), name='banner_manage'),
    path('banners/<int:b_id>/', views.BannerEditView.as_view(), name='banner_edit'),
    path('banners/add/', views.AddBannerView.as_view(), name='banner_add'),
    path('doc/', views.DocManageView.as_view(), name='doc_manage'),
    path('doc/<int:doc_id>/', views.DocEditView.as_view(), name='doc_edit'),
    path('doc/files/', views.DocUpFile.as_view(), name='doc_up_file'),
    path('doc/pub/', views.DocsPubView.as_view(), name='doc_pub'),
    path('courses/', views.CourseManageView.as_view(), name='course_manage'),
    path('courses/<int:course_id>/', views.CourseEditView.as_view(), name='course_edit'),
    path('courses/pub/', views.CoursePubView.as_view(), name='course_pub'),
    path('groups/', views.GroupsManageView.as_view(), name='groups'),
    path('groups/<int:g_id>/', views.GroupsEdit.as_view(), name='g_edit'),
    path('groups/add/', views.GroupsAddView.as_view(), name='groups_add'),
    path('token/', views.UploadToken.as_view(), name='upload_token'),  # 七牛
    path('users/', views.UsersManageView.as_view(), name='users_manage'),
    path('users/<int:user_id>/', views.UsersEditView.as_view(), name='users_edit'),
]
