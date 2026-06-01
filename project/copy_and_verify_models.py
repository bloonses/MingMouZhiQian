import os
import shutil

# 1. 复制 .insightface 到工作目录
src_dir = os.path.expanduser('~/.insightface')
dst_dir = os.path.join(os.path.dirname(__file__), '.insightface')

print(f'正在复制 {src_dir} 到 {dst_dir}...')
if os.path.exists(dst_dir):
    shutil.rmtree(dst_dir)
shutil.copytree(src_dir, dst_dir)
print('✅ 复制完成！')

# 2. 检查 buffalo_l 目录
buffalo_path = os.path.join(dst_dir, 'models', 'buffalo_l')
if not os.path.exists(buffalo_path):
    print('❌ 未找到 buffalo_l 目录')
else:
    print(f'✅ 找到 buffalo_l 目录: {buffalo_path}')
    files = os.listdir(buffalo_path)
    print(f'   包含文件: {files}')

# 3. 如果目录嵌套，修正它
buffalo_subdir = os.path.join(buffalo_path, 'models', 'buffalo_l')
if os.path.exists(buffalo_subdir) and len(os.listdir(buffalo_path)) == 1:
    print('发现嵌套目录，正在移动...')
    for item in os.listdir(buffalo_subdir):
        shutil.move(os.path.join(buffalo_subdir, item), buffalo_path)
    os.rmdir(os.path.join(buffalo_path, 'models'))
    print('✅ 嵌套已修正！')

# 4. 最终检查
print('\n📁 最终目录结构:')
for root, dirs, files in os.walk(os.path.join(dst_dir, 'models')):
    level = root.replace(os.path.join(dst_dir, 'models'), '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for f in files:
        print(f'{subindent}{f}')

print('\n🎈 模型准备好了！接下来修改代码从本地加载。')
