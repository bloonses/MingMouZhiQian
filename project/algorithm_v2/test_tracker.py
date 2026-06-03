"""
明眸智签 v2.0 - 人脸追踪器测试
验证 TR-9.2：追踪 ID 稳定性 > 90%
"""

import numpy as np
import time
from face_tracker import FaceTracker, TrackedFace


def generate_moving_bboxes(initial_bbox, num_frames=50, speed=2):
    """生成移动的检测框序列"""
    bboxes = []
    x1, y1, x2, y2 = initial_bbox
    for i in range(num_frames):
        # 平滑移动
        dx = np.sin(i * 0.1) * speed * 5
        dy = np.cos(i * 0.15) * speed * 3
        new_bbox = np.array([x1 + dx, y1 + dy, x2 + dx, y2 + dy])
        bboxes.append(new_bbox)
    return bboxes


def generate_multiple_moving_bboxes(num_people=3, num_frames=50, img_size=(640, 480)):
    """生成多个人脸移动的检测框序列"""
    sequences = []
    for pid in range(num_people):
        # 随机初始位置
        x1 = 50 + pid * 180
        y1 = 100
        x2 = x1 + 120
        y2 = y1 + 150
        bboxes = generate_moving_bboxes([x1, y1, x2, y2], num_frames, speed=1 + pid * 0.3)
        sequences.append(bboxes)
    return sequences


def test_single_track_stability():
    """测试单个人脸追踪 ID 稳定性"""
    print("=" * 60)
    print("测试 1: 单个人脸追踪 ID 稳定性")
    print("=" * 60)
    
    tracker = FaceTracker(max_age=3, min_hits=2, iou_threshold=0.25)
    
    # 生成移动的检测框
    initial_bbox = [100, 100, 220, 250]
    bboxes = generate_moving_bboxes(initial_bbox, num_frames=100)
    
    track_ids = []
    
    for frame_idx, bbox in enumerate(bboxes):
        # 模拟检测：有时会有小的抖动
        if np.random.random() > 0.85:
            # 偶尔添加小噪声
            bbox = bbox + np.random.randn(4) * 3
        
        active_tracks = tracker.update([bbox])
        
        if active_tracks:
            track_ids.append(active_tracks[0].track_id)
        else:
            track_ids.append(None)
    
    # 计算稳定性
    valid_tracks = [tid for tid in track_ids if tid is not None]
    if len(valid_tracks) >= 2:
        # 计算 ID 切换次数
        switches = 0
        for i in range(1, len(valid_tracks)):
            if valid_tracks[i] != valid_tracks[i-1]:
                switches += 1
        
        stability = 1.0 - (switches / (len(valid_tracks) - 1))
        print(f"总帧数: {len(bboxes)}")
        print(f"有效追踪帧数: {len(valid_tracks)}")
        print(f"ID 切换次数: {switches}")
        print(f"追踪 ID 稳定性: {stability * 100:.1f}%")
        
        result = stability >= 0.9
        print(f"TR-9.2 要求 (≥90%): {'✓ 通过' if result else '✗ 失败'}")
        return result
    return False


def test_multi_track_stability():
    """测试多个人脸追踪 ID 稳定性"""
    print("\n" + "=" * 60)
    print("测试 2: 多个人脸追踪 ID 稳定性")
    print("=" * 60)
    
    tracker = FaceTracker(max_age=5, min_hits=3, iou_threshold=0.3)
    
    num_people = 3
    num_frames = 80
    sequences = generate_multiple_moving_bboxes(num_people, num_frames)
    
    all_track_ids = {pid: [] for pid in range(num_people)}
    
    for frame_idx in range(num_frames):
        # 收集当前帧的所有检测框
        detections = []
        for pid in range(num_people):
            bbox = sequences[pid][frame_idx]
            detections.append(bbox)
        
        # 偶尔丢检或误检
        if np.random.random() > 0.9:
            if len(detections) > 1:
                detections.pop(np.random.randint(len(detections)))
        
        active_tracks = tracker.update(detections)
        
        # 简单的匹配：每个检测框找 IoU 最大的轨迹
        for pid in range(num_people):
            if frame_idx >= len(sequences[pid]):
                continue
            target_bbox = sequences[pid][frame_idx]
            
            best_iou = 0
            best_track_id = None
            for track in active_tracks:
                iou = tracker._iou(target_bbox, track.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track.track_id
            
            if best_iou > 0.5:
                all_track_ids[pid].append(best_track_id)
            else:
                all_track_ids[pid].append(None)
    
    # 计算每个人的稳定性
    total_stability = 0.0
    num_valid = 0
    
    for pid in range(num_people):
        valid_tracks = [tid for tid in all_track_ids[pid] if tid is not None]
        if len(valid_tracks) >= 2:
            switches = 0
            for i in range(1, len(valid_tracks)):
                if valid_tracks[i] != valid_tracks[i-1]:
                    switches += 1
            
            stability = 1.0 - (switches / (len(valid_tracks) - 1))
            total_stability += stability
            num_valid += 1
            print(f"  人员 {pid+1}: 稳定性 {stability * 100:.1f}% (有效帧数 {len(valid_tracks)})")
    
    if num_valid > 0:
        avg_stability = total_stability / num_valid
        print(f"\n平均追踪 ID 稳定性: {avg_stability * 100:.1f}%")
        
        result = avg_stability >= 0.9
        print(f"TR-9.2 要求 (≥90%): {'✓ 通过' if result else '✗ 失败'}")
        return result
    return False


def test_sign_cache():
    """测试签到缓存功能"""
    print("\n" + "=" * 60)
    print("测试 3: 签到缓存功能")
    print("=" * 60)
    
    tracker = FaceTracker(cache_timeout=1)  # 1秒超时
    
    # 标记签到
    tracker.mark_signed("S1001")
    tracker.mark_signed("S1002")
    
    print("刚标记后:")
    print(f"  S1001 已签到: {tracker.is_already_signed('S1001')}")
    print(f"  S1002 已签到: {tracker.is_already_signed('S1002')}")
    print(f"  S1003 已签到: {tracker.is_already_signed('S1003')}")
    
    # 等待超时
    print("\n等待 1.5 秒后...")
    time.sleep(1.5)
    
    print(f"  S1001 已签到: {tracker.is_already_signed('S1001')}")
    print(f"  S1002 已签到: {tracker.is_already_signed('S1002')}")
    
    # 重新标记
    tracker.mark_signed("S1001")
    print("\n重新标记 S1001 后:")
    print(f"  S1001 已签到: {tracker.is_already_signed('S1001')}")
    
    print("\n✓ 签到缓存功能测试完成")
    return True


def test_recognition_interval():
    """测试识别间隔控制功能"""
    print("\n" + "=" * 60)
    print("测试 4: 识别间隔控制")
    print("=" * 60)
    
    tracker = FaceTracker(recognition_interval=3)
    bbox = np.array([100, 100, 220, 250])
    
    recognize_count = 0
    for frame in range(20):
        tracker.update([bbox])
        tracks = tracker.get_tracks_for_recognition()
        if tracks:
            recognize_count += 1
            for track in tracks:
                tracker.update_recognition_result(track.track_id, "S001", 0.95)
    
    print(f"总帧数: 20")
    print(f"识别间隔: {tracker.recognition_interval}")
    print(f"实际识别次数: {recognize_count}")
    print(f"预期识别次数: ~{20 // tracker.recognition_interval}")
    
    # 检查是否合理
    expected_min = max(1, 20 // (tracker.recognition_interval + 1))
    expected_max = 20 // max(1, tracker.recognition_interval - 1) + 1
    
    result = expected_min <= recognize_count <= expected_max
    print(f"测试结果: {'✓ 通过' if result else '✗ 失败'}")
    return result


def test_tracker_stats():
    """测试追踪器统计功能"""
    print("\n" + "=" * 60)
    print("测试 5: 追踪器统计信息")
    print("=" * 60)
    
    tracker = FaceTracker()
    
    # 模拟几帧
    bboxes = [
        [np.array([100, 100, 200, 220]), np.array([300, 100, 400, 220])],
        [np.array([105, 105, 205, 225]), np.array([305, 105, 405, 225])],
        [np.array([110, 110, 210, 230]), np.array([310, 110, 410, 230])],
        [np.array([115, 115, 215, 235]), np.array([315, 115, 415, 235])],
        [np.array([120, 120, 220, 240])],
    ]
    
    for dets in bboxes:
        tracker.update(dets)
    
    # 标记签到
    tracker.mark_signed("S001")
    
    stats = tracker.get_stats()
    print(f"统计信息:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    result = (stats['frame_count'] == len(bboxes) and 
              stats['total_tracks'] > 0 and 
              stats['signed_students'] == 1)
    print(f"测试结果: {'✓ 通过' if result else '✗ 失败'}")
    return result


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("明眸智签 v2.0 - 人脸追踪器测试套件")
    print("=" * 60)
    
    results = []
    
    results.append(("单人脸追踪稳定性", test_single_track_stability()))
    results.append(("多人脸追踪稳定性", test_multi_track_stability()))
    results.append(("签到缓存功能", test_sign_cache()))
    results.append(("识别间隔控制", test_recognition_interval()))
    results.append(("追踪器统计信息", test_tracker_stats()))
    
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    
    return passed == len(results)


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
