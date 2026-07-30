"""
自动化专业 Python 科学计算栈 — 全套演示
涵盖：PID 控制、系统响应分析、Bode 图、根轨迹
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal, optimize
import control as ct

# ---- 中文字体设置 ----
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 传递函数 & 阶跃响应
# ============================================================
print("=" * 60)
print("1. 二阶系统阶跃响应")
print("=" * 60)

# 定义传递函数 G(s) = ω_n² / (s² + 2ζω_n s + ω_n²)
omega_n = 5.0  # 自然频率 (rad/s)
zeta_vals = [0.2, 0.5, 0.7, 1.0, 1.5]  # 不同阻尼比

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle("自动化专业 — Python 科学计算演示", fontsize=14, fontweight="bold")

# ---- 阶跃响应 ----
ax1 = axes[0, 0]
t = np.linspace(0, 5, 500)
for z in zeta_vals:
    G = ct.tf([omega_n**2], [1, 2*z*omega_n, omega_n**2])
    t_out, y = ct.step_response(G, t)
    ax1.plot(t_out, y, label=f"ζ={z}")

ax1.set_title("阶跃响应 (不同阻尼比)")
ax1.set_xlabel("时间 (s)"); ax1.set_ylabel("幅值")
ax1.legend(); ax1.grid(True, alpha=0.3)

# ---- 零极点图 ----
ax2 = axes[0, 1]
for i, z in enumerate(zeta_vals):
    poles = np.roots([1, 2*z*omega_n, omega_n**2])
    ax2.scatter(poles.real, poles.imag, marker='x', s=80, label=f"ζ={z}")
ax2.axhline(0, color='gray', lw=0.5)
ax2.axvline(0, color='gray', lw=0.5)
ax2.set_title("极点分布")
ax2.set_xlabel("实部"); ax2.set_ylabel("虚部")
ax2.legend(); ax2.grid(True, alpha=0.3)
ax2.set_aspect('equal')

# ============================================================
# 2. PID 控制器设计 & 仿真
# ============================================================
print("\n" + "=" * 60)
print("2. PID 控制器仿真")
print("=" * 60)

# 被控对象: G(s) = 1 / (s² + 2s + 1)
G_plant = ct.tf([1], [1, 2, 1])

# PID 参数
Kp, Ki, Kd = 10.0, 5.0, 2.0
C_pid = ct.tf([Kd, Kp, Ki], [1, 0])  # PID: (Kd·s² + Kp·s + Ki) / s

# 闭环传函
G_cl = ct.feedback(C_pid * G_plant, 1)

t = np.linspace(0, 10, 1000)
t_out, y = ct.step_response(G_cl, t)

# 求时域指标
info = ct.step_info(G_cl)
print(f"  上升时间: {info.get('RiseTime', 'N/A'):.4f} s")
print(f"  调节时间: {info.get('SettlingTime', 'N/A'):.4f} s")
print(f"  超调量:   {info.get('Overshoot', 0):.2f}%")
print(f"  稳态误差: {abs(1 - y[-1]):.6f}")

ax3 = axes[1, 0]
ax3.plot(t_out, y, 'b-', linewidth=2)
ax3.axhline(1, color='k', linestyle='--', alpha=0.5)
ax3.set_title(f"PID 闭环阶跃响应 (Kp={Kp}, Ki={Ki}, Kd={Kd})")
ax3.set_xlabel("时间 (s)"); ax3.set_ylabel("输出")
ax3.grid(True, alpha=0.3)

# ============================================================
# 3. Bode 图
# ============================================================
print("\n" + "=" * 60)
print("3. Bode 图 & 稳定性分析")
print("=" * 60)

# 开环传函
G_ol = C_pid * G_plant
gm, pm, wgm, wpm = ct.margin(G_ol)
print(f"  增益裕度: {gm:.2f} dB")
print(f"  相位裕度: {pm:.2f}°")
print(f"  穿越频率: {wpm:.2f} rad/s")

mag, phase, omega = ct.bode(G_ol, plot=False)
ax4 = axes[1, 1]
# 手动画 Bode 幅值
ax4_mag = ax4
ax4_phase = ax4.twinx()
ax4_mag.semilogx(omega, 20*np.log10(mag), 'b-', label='幅值')
ax4_phase.semilogx(omega, np.degrees(phase), 'r-', label='相位')
ax4_mag.set_title("Bode 图 (开环)")
ax4_mag.set_xlabel("频率 (rad/s)")
ax4_mag.set_ylabel("幅值 (dB)", color='b')
ax4_phase.set_ylabel("相位 (°)", color='r')
ax4_mag.grid(True, alpha=0.3)

plt.tight_layout()

# ============================================================
# 4. SciPy — 最优化示例：PID 参数自动整定
# ============================================================
print("\n" + "=" * 60)
print("4. PID 自动整定 (ITAE 准则)")
print("=" * 60)


def simulate_pid(params):
    """仿真 PID 并返回 ITAE 指标"""
    Kp, Ki, Kd = params
    C = ct.tf([Kd, Kp, Ki], [1, 0])
    G_closed = ct.feedback(C * G_plant, 1)
    t_arr = np.linspace(0, 8, 500)
    _, y_arr = ct.step_response(G_closed, t_arr)
    error = 1 - y_arr
    itae = np.trapezoid(t_arr * np.abs(error), t_arr)  # ITAE = ∫ t·|e| dt
    return itae


# 初始猜测 + 边界
x0 = [5.0, 1.0, 0.5]
bounds = [(0.1, 100), (0.01, 50), (0.0, 20)]
result = optimize.minimize(simulate_pid, x0, bounds=bounds, method='L-BFGS-B')

Kp_opt, Ki_opt, Kd_opt = result.x
print(f"  优化后 PID: Kp={Kp_opt:.2f}, Ki={Ki_opt:.2f}, Kd={Kd_opt:.2f}")
print(f"  ITAE 指标: {result.fun:.4f}")

# 验证优化后结果
C_opt = ct.tf([Kd_opt, Kp_opt, Ki_opt], [1, 0])
G_cl_opt = ct.feedback(C_opt * G_plant, 1)
t_out_opt, y_opt = ct.step_response(G_cl_opt, t)

ax3.plot(t_out_opt, y_opt, 'r--', linewidth=2, label='ITAE优化')
ax3.legend()

# 保存图片
fig.savefig("control_demo_output.png", dpi=150, bbox_inches="tight")
print(f"\n图表已保存到 control_demo_output.png")
print("科学计算栈搭建完成!")
