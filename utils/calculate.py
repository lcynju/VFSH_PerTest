# 计算恒定度
# 恒定度 = (最大值 - 最小值) * 100 / (最大值 + 最小值)
def calculate_constancy(points):
    if not points:
        return 0.0
    sorted_pts = sorted(points)
    n = len(points)
    maxP = sum(sorted_pts[-5:]) / min(5, n)
    minP = sum(sorted_pts[:5]) / min(5, n)
    return (maxP - minP) * 100 / (maxP + minP)

# 计算锁定位置
# 锁定位置 = 实测位移值 / 去0时记录的y位置到最大y值的距离
def calculate_lock_position(measured_displacement, y_max):
    """锁定位置 = 实测位移值 / 去0时记录的y位置到最大y值的距离"""
    if y_max is None or y_max == 0:
        return None
    return measured_displacement / y_max

# 计算平均载荷偏差度
# 平均载荷偏差度 λ = |Wg - Wp| / Wg * 100%
# Wg: 工作载荷（设计载荷），Wp: (最大载荷 + 最小载荷)/2
def calculate_load_deviation(Wg, points):
    if not points:
        return 0.0
    Wp = sum(points[:5]) / min(5, len(points))
    deviation = abs(Wg - Wp) / Wg * 100
    return deviation
    