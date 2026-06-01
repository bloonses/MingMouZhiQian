import os
import ssl
import urllib.request
import zipfile

# 禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context

# 目标路径
model_root = os.path.expanduser('~/.insightface/models/buffalo_l')
os.makedirs(model_root, exist_ok=True)

zip_path = os.path.join(model_root, 'buffalo_l.zip')

# 下载链接
url = 'https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip'

print(f'正在下载 buffalo_l.zip 到 {zip_path}...')
try:
    urllib.request.urlretrieve(url, zip_path)
    print('✅ 下载完成！')
    
    # 解压
    print('正在解压...')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(model_root)
    print('✅ 解压完成！')
    
    # 删除 zip 文件
    os.remove(zip_path)
    print('✅ 临时文件已删除！')
    
    print('\n🎈 模型已准备好，请重新运行验证命令！')
    
except Exception as e:
    print(f'❌ 下载失败: {e}')
    print('\n💡 请手动下载:')
    print('  https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip')
    print(f'  解压到: {model_root}')
