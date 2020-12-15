from fdfs_client.client import Fdfs_client
client = Fdfs_client('utils/fastdfs/client.conf')

# 上传文件时有几个方法
# 1.针对文件名字
# ret = FDFS_Client.upload_by_filename('media/son.png')
# 2.针对文件数据（bytes 类型） client.upload_by_buffer
