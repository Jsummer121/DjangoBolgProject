from django.db import models
from utils.models import ModelBase


class Doc(ModelBase):
    """
    文件地址
    书籍标题
    书籍描述信息
    图片
    作者
    """
    file_url = models.URLField(verbose_name="书籍url", help_text="书籍url地址")
    title = models.CharField(max_length=150, verbose_name="书籍标题", help_text="书籍标题")
    desc = models.TextField(verbose_name="文档描述", help_text="文档描述")
    image_url = models.URLField(default="", verbose_name="图片url", help_text="图片url")
    author = models.ForeignKey('user.Users', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "tb_docs"   # 指明数据库表名
        verbose_name = "书籍"    # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return self.title
