from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data_processed" / "demo_predictions_final.csv"

@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH).sort_values(["subject", "task", "window_end_sec"])

def subject_key(value):
    return int(str(value).split("_")[1])

def fatigue_level(pred_rpe):
    if pred_rpe < 13:
        return "Low"
    if pred_rpe < 17:
        return "Moderate-High"
    return "High"

st.set_page_config(page_title="Wearable IMU Fatigue Demo", layout="wide")
df_demo = load_data()

st.title("基于可穿戴 IMU 的运动疲劳评估与高疲劳预警 Demo")
st.caption("Upper-arm ACC + Gyroscope | 100 Hz | 10 s Window | Random Forest / XGBoost / Linear Models | Cross-subject OOF")
st.write("本项目使用上臂 IMU 的加速度计和陀螺仪信号，每 10 秒提取时域特征，估计 Borg RPE，并探索高疲劳状态预警。")
st.info("本 Demo 仅用于机器学习与可穿戴运动疲劳研究展示，不用于医学诊断或临床决策。")
st.write("使用历史公开数据的 OOF prediction 进行模拟实时回放。当前页面不连接真实传感器。")
st.write("Final Regression Model: **XGBoost**")
st.write("Final Classification Model: **LogisticRegression**")

subject = st.sidebar.selectbox("Subject", sorted(df_demo["subject"].unique(), key=subject_key))
subject_df = df_demo[df_demo["subject"] == subject]
task = st.sidebar.selectbox("Task", sorted(subject_df["task"].unique()))
task_df = subject_df[subject_df["task"] == task].sort_values("window_end_sec")
mode = st.sidebar.radio("模式", ["单窗口查看", "历史回放"])
windows = task_df["window_end_sec"].astype(int).tolist()

if mode == "单窗口查看":
    current_window = st.sidebar.selectbox("Window", windows, format_func=lambda x: f"{x} s")
else:
    position = st.sidebar.slider("当前回放到第几个窗口", 1, len(windows), len(windows))
    current_window = windows[position - 1]

current_row = task_df[task_df["window_end_sec"] == current_window].iloc[0]
visible_df = task_df[task_df["window_end_sec"] <= current_window] if mode == "历史回放" else task_df

st.subheader("当前窗口")
st.write(f"`{subject}` | `{task}` | `{current_row.exercise_folder}` | end={int(current_window)} s")
c1, c2, c3, c4 = st.columns(4)
c1.metric("True Borg RPE", f"{current_row.true_rpe:.0f}")
c2.metric("Predicted Borg RPE", f"{current_row.pred_rpe:.2f}")
c3.metric("Absolute Error", f"{current_row.absolute_error:.2f}")
c4.metric("High-fatigue Probability", f"{current_row.pred_high_fatigue_probability:.3f}")

st.write(f"Demo fatigue level: **{fatigue_level(current_row.pred_rpe)}**（仅为展示分级，不是医学标准）")
st.write(f"Current warning threshold: `{current_row.selected_threshold:.3f}`")
warning = current_row.pred_high_fatigue_probability >= current_row.selected_threshold
if warning:
    st.warning("实验性高疲劳提醒")
else:
    st.success("当前未触发高疲劳提醒")

left, right = st.columns(2)
with left:
    st.write("True High Fatigue (RPE>=17):", int(current_row.true_high_fatigue))
with right:
    st.write("Predicted Warning:", "Yes" if warning else "No")

st.subheader("True RPE vs Predicted RPE")
st.line_chart(visible_df.set_index("window_end_sec")[["true_rpe", "pred_rpe"]])
st.subheader("High-fatigue Probability vs Selected Threshold")
st.line_chart(visible_df.set_index("window_end_sec")[["pred_high_fatigue_probability", "selected_threshold"]])

with st.expander("为什么阈值不是 0.5？"):
    st.write("模型超参数在训练受试者内部选择；随后使用训练侧 inner OOF probability，以 F2 为目标选择实验性 warning threshold。降低阈值可减少高疲劳漏识别，但会明显增加误报。它不是医学标准。")

with st.expander("项目方法"):
    st.write("Upper-arm IMU → ACC + Gyroscope → 100 Hz → 10-second non-overlap window → 56 time-domain features → subject-level Nested GroupKFold → RPE regression + high-fatigue classification → experimental warning")

with st.expander("56 个特征是怎么来的？"):
    st.write("acc_x/y/z 与 gyr_x/y/z 共 6 通道，每通道提取 mean、std、min、max、range、rms、median，共 42 个；acc_mag 与 gyr_mag 各提取 7 个，共 14 个；总计 56。")

with st.expander("模型实验结果"):
    st.write("最佳回归模型：XGBoost；最佳分类模型：LogisticRegression。所有展示均来自跨受试者 OOF prediction。分类判别能力有限，降低阈值提高 Recall 的同时会增加大量 False Positive。")

with st.expander("项目局限性"):
    st.write("当前只使用单 Upper-arm IMU 和简单时域特征；RPE 是主观量表；跨受试者差异明显；分类 AUC 有限；降低预警阈值会增加误报。未来可研究多位置 IMU、PPG、EMG、个体基线归一化和更丰富时序特征，但当前项目未实现。")

with st.expander("这个 Demo 想说明什么？"):
    st.write("重点是完成可穿戴信号 → 时间窗口 → 特征工程 → 机器学习 → 跨受试者验证 → 疲劳评估 → 预警展示的完整原型，而不是构建临床级预警器。")
