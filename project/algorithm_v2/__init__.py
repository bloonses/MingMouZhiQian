# 明眸智签 v2.0 - 算法模块
# 全面升级的人脸识别算法包

from .optimized_inference import (
    OptimizedONNXModel,
    OptimizedInferenceEngine,
    get_optimized_engine,
    release_optimized_engine
)

__all__ = [
    'OptimizedONNXModel',
    'OptimizedInferenceEngine',
    'get_optimized_engine',
    'release_optimized_engine',
]
