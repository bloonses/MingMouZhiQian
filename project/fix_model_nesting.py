import os
import shutil

buffalo_dir = os.path.join(os.path.dirname(__file__), '.insightface', 'models', 'buffalo_l')
models_subdir = os.path.join(buffalo_dir, 'models')

if os.path.exists(models_subdir):
    print('发现嵌套目录，正在移动文件...')
    # 移动所有文件到 buffalo_dir
    for item in os.listdir(models_subdir):
        src = os.path.join(models_subdir, item)
        dst = os.path.join(buffalo_dir, item)
        print(f'  移动: {item}')
        shutil.move(src, dst)
    # 删除嵌套目录
    shutil.rmtree(models_subdir)
    print('✅ 嵌套目录已修复！')

# 打印最终结构
print('\n📁 最终模型目录:')
for item in sorted(os.listdir(buffalo_dir)):
    print(f'  - {item}')

print('\n✅ 模型位置现在正确了！')
