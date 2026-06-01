import os
import urllib.request
import sys

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

MODELS = {
    'detector.onnx': 'https://github.com/onnx/models/raw/main/validated/vision/body_analysis/face_detection/model/detection_Resnet50_Final.onnx',
}

print('[1/3] 检查 insightface 包...')
try:
    import insightface
    from insightface.model_zoo import get_model
    print('  insightface 已安装，使用内置模型下载...')
    
    detector = insightface.model_zoo.get_model('buffalo_l/det_500m.onnx')
    detector.prepare(ctx_id=-1)
    print('  检测模型就绪')
    
    recognizer = insightface.model_zoo.get_model('buffalo_l/w600k_r50.onnx')
    recognizer.prepare(ctx_id=-1)
    print('  识别模型就绪')
    
    print('\n[OK] 模型通过 insightface 加载成功，无需手动下载！')
    sys.exit(0)
except ImportError:
    print('  insightface 未安装，尝试下载 ONNX 模型...')
except Exception as e:
    print(f'  insightface 加载失败: {e}')
    print('  尝试直接下载 ONNX 模型...')

print('\n[2/3] 安装 insightface...')
print('  请手动运行: pip install insightface')
print('  或者继续手动下载 ONNX 模型文件...')

print('\n[3/3] 手动下载模型:')
print('  1. RetinaFace ONNX:')
print('     https://github.com/onnx/models/raw/main/validated/vision/body_analysis/face_detection/model/detection_Resnet50_Final.onnx')
print('     保存为: models/detector.onnx')
print()
print('  2. ArcFace ONNX (w600k_r50):')
print('     运行 pip install insightface 后自动下载，或使用:')
print('     git clone https://huggingface.co/onnx-community/arcfaceresnet100-8')
print('     保存为: models/arcface.onnx')

print('\n推荐方式: pip install insightface onnxruntime')
print('insightface 会自动下载和管理模型文件')