import streamlit as st
import streamlit.components.v1 as components
import random
import time
from datetime import datetime

st.set_page_config(page_title="育肥羊数字孪生平台", layout="wide")
st.title("🐑 育肥羊数字孪生云平台")
st.markdown("**现实与虚拟实时映射 · 双向交互 · 故障预判**")

# ---------- 侧边栏控制 ----------
with st.sidebar:
    st.header("🎮 虚拟控制台（孪生反向控制）")
    vent_level = st.slider("通风机转速 (%)", 0, 100, 60)
    humidifier = st.checkbox("加湿器", False)
    feed_mode = st.selectbox("投喂模式", ["正常", "增量", "减量"])
    st.markdown("---")
    st.caption("操作将实时影响虚拟环境")
    st.markdown("**📋 操作日志**")
    if "control_log" not in st.session_state:
        st.session_state.control_log = []
    for log in st.session_state.control_log[-5:]:
        st.text(log)

# ---------- 数据生成 ----------
def generate_data(vent, hum_on, feed_mode):
    base_temp = 39.0 + random.uniform(-0.5, 0.5)
    temp = base_temp - (vent - 50) * 0.02
    humidity = 60 + random.uniform(-10, 10)
    if hum_on:
        humidity += 15
    ammonia = max(0, 15 + random.uniform(-5, 5) - vent * 0.15)
    if feed_mode == "正常":
        feed_weight = 10 + random.uniform(-2, 2)
    elif feed_mode == "增量":
        feed_weight = 12 + random.uniform(-1, 3)
    else:
        feed_weight = 8 + random.uniform(-2, 1)
    feed_weight = max(3, min(15, feed_weight))
    motor_current = random.choice([0, 0, 2.5, 2.6, 2.7]) if random.random() > 0.05 else 0
    device_online = random.random() > 0.05
    sheep_data = []
    for i in range(1, 6):
        stemp = temp + random.uniform(-0.3, 0.3)
        sfeed = feed_weight * random.uniform(0.8, 1.2) / 5
        sheep_data.append({
            "ear_tag": f"YF-{i:03d}",
            "temp": round(stemp, 1),
            "feed": round(sfeed, 2),
            "health": "normal" if 38.0 <= stemp <= 39.5 else "warning"
        })
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "temperature": round(temp, 1),
        "humidity": round(humidity, 1),
        "ammonia": round(ammonia, 1),
        "feed_weight": round(feed_weight, 1),
        "motor_current": motor_current,
        "device_online": device_online,
        "sheep": sheep_data
    }

# ---------- 初始化 ----------
if "alarms" not in st.session_state:
    st.session_state.alarms = []
if "last_feed" not in st.session_state:
    st.session_state.last_feed = 10.0
if "history" not in st.session_state:
    st.session_state.history = []
if "control_log" not in st.session_state:
    st.session_state.control_log = []
if "prev_vent" not in st.session_state:
    st.session_state.prev_vent = 60
if "prev_hum" not in st.session_state:
    st.session_state.prev_hum = False
if "prev_feed" not in st.session_state:
    st.session_state.prev_feed = "正常"

# 记录控制日志
if vent_level != st.session_state.prev_vent:
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} 通风调至 {vent_level}%")
    st.session_state.prev_vent = vent_level
if humidifier != st.session_state.prev_hum:
    action = "开启" if humidifier else "关闭"
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} {action}加湿器")
    st.session_state.prev_hum = humidifier
if feed_mode != st.session_state.prev_feed:
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} 投喂模式切换至{feed_mode}")
    st.session_state.prev_feed = feed_mode

data = generate_data(vent_level, humidifier, feed_mode)
st.session_state.history.append(data)
if len(st.session_state.history) > 20:
    st.session_state.history.pop(0)

# ---------- 报警 ----------
def check_alarms(data):
    new_alarms = []
    temp = data["temperature"]
    if temp > 40.0:
        new_alarms.append({"type": "高温紧急", "msg": f"温度 {temp}℃ >40℃", "level": "critical"})
    elif temp > 39.5:
        new_alarms.append({"type": "高温预警", "msg": f"温度 {temp}℃ 偏高", "level": "warning"})
    elif temp < 38.0:
        new_alarms.append({"type": "低温预警", "msg": f"温度 {temp}℃ 偏低", "level": "warning"})
    cur_feed = data["feed_weight"]
    if st.session_state.last_feed > 0:
        change = (cur_feed - st.session_state.last_feed) / st.session_state.last_feed
        if change < -0.25:
            new_alarms.append({"type": "采食骤降", "msg": f"料槽变化 {change*100:.0f}%", "level": "critical"})
        elif change < -0.15:
            new_alarms.append({"type": "采食下降", "msg": f"料槽变化 {change*100:.0f}%", "level": "warning"})
    st.session_state.last_feed = cur_feed
    if data["motor_current"] == 0:
        new_alarms.append({"type": "电机停转", "msg": "饲喂电机电流=0", "level": "critical"})
    if not data["device_online"]:
        new_alarms.append({"type": "设备离线", "msg": "传感器心跳超时", "level": "critical"})
    for a in new_alarms:
        a["time"] = datetime.now().strftime("%H:%M:%S")
        a["status"] = "待处理"
        a["push"] = "已推送"
        st.session_state.alarms.insert(0, a)

check_alarms(data)

# ---------- 趋势预测 ----------
def predict_risk(history):
    if len(history) < 5:
        return []
    temps = [h["temperature"] for h in history]
    n = len(temps)
    x_mean = (n-1)/2
    y_mean = sum(temps)/n
    num = sum((i-x_mean)*(t-y_mean) for i,t in enumerate(temps))
    den = sum((i-x_mean)**2 for i in range(n))
    slope = num/den if den else 0
    preds = []
    if slope > 0.08:
        preds.append({"type": "温度上升风险", "msg": f"温度趋势上升 (斜率 {slope:.3f})，建议检查通风"})
    if slope > 0.15:
        preds.append({"type": "高温紧急风险", "msg": f"温度快速攀升，请立即处置"})
    return preds

predictions = predict_risk(st.session_state.history)

# ---------- UI ----------
tab1, tab2 = st.tabs(["📊 实时监控与孪生映射", "🐑 羊只个体状态"])

with tab1:
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("🌡️ 环境参数与设备状态")
        c1, c2, c3 = st.columns(3)
        temp = data["temperature"]
        color = "red" if temp>40 else ("orange" if temp>39.5 else "green")
        c1.metric("温度 ℃", temp, delta="异常" if color!="green" else "正常", delta_color="inverse" if color=="red" else "normal")
        c2.metric("湿度 %", data["humidity"])
        c3.metric("氨气 ppm", data["ammonia"])

        st.markdown("---")
        st.subheader("📋 最近 5 条历史记录（实时映射）")
        if st.session_state.history:
            # 显示最近 5 条
            recent = list(st.session_state.history)[-5:]
            table_md = "| 时间 | 温度 ℃ | 湿度 % | 料槽 kg | 电机电流 A | 设备 |\n"
            table_md += "|------|--------|--------|---------|------------|------|\n"
            for h in recent:
                motor_str = f"{h['motor_current']:.1f}" if h['motor_current']>0 else "0 (停转)"
                device_str = "在线" if h['device_online'] else "离线"
                table_md += f"| {h['timestamp']} | {h['temperature']} | {h['humidity']} | {h['feed_weight']} | {motor_str} | {device_str} |\n"
            st.markdown(table_md)
        else:
            st.info("暂无历史数据")

    with col_right:
        st.subheader("🏠 虚拟羊舍（孪生场景）")
        temp_norm = min(1, max(0, (temp - 38) / 3))
        bg_color = f"rgba(255, {255 - int(temp_norm*150)}, {255 - int(temp_norm*150)}, 0.3)"
        fan_rotation = vent_level / 100 * 360
        motor_status = "运转中" if data["motor_current"] > 0 else "停止"
        motor_color = "green" if data["motor_current"] > 0 else "red"
        device_color = "green" if data["device_online"] else "red"
        html_code = f"""
        <div style="width:100%; height:300px; background:{bg_color}; border-radius:15px; padding:10px; position:relative; overflow:hidden;">
            <div style="position:absolute; top:10px; left:10px; background:white; padding:5px; border-radius:5px;">
                <b>羊舍温度 {temp}℃</b>
            </div>
            <div style="position:absolute; bottom:20px; right:20px; text-align:center;">
                <div style="font-size:30px; transform:rotate({fan_rotation}deg); transition: transform 0.3s;">🌀</div>
                <div style="font-size:12px;">通风机 ({vent_level}%)</div>
            </div>
            <div style="position:absolute; bottom:20px; left:20px; text-align:center;">
                <div style="font-size:30px;">🪣</div>
                <div style="font-size:12px;">料槽 {data["feed_weight"]}kg</div>
            </div>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); font-size:40px;">🐑🐑🐑</div>
            <div style="position:absolute; top:20px; right:20px;">
                <span style="color:{motor_color};">⚙️ 电机 {motor_status}</span><br>
                <span style="color:{device_color};">📡 传感器 {'在线' if data['device_online'] else '离线'}</span>
            </div>
        </div>
        """
        components.html(html_code, height=320)
        st.caption("背景色随温度变化 · 风机转速随控制变化")

    st.divider()
    st.subheader("🔮 故障风险预测")
    if predictions:
        for p in predictions:
            st.warning(f"🟡 {p['msg']}")
    else:
        st.success("当前趋势正常")

    st.subheader("🚨 报警记录与闭环处理")
    if not st.session_state.alarms:
        st.info("无报警")
    else:
        table_md = "| 时间 | 类型 | 详情 | 级别 | 状态 | 推送 |\n|------|------|------|------|------|------|\n"
        for a in st.session_state.alarms[:10]:
            icon = "🔴" if a["level"]=="critical" else "🟡"
            table_md += f"| {a['time']} | {a['type']} | {a['msg']} | {icon} | {a['status']} | {a['push']} |\n"
        st.markdown(table_md)
        pending = [a for a in st.session_state.alarms if a["status"]=="待处理"]
        if pending:
            opts = [f"{a['time']} {a['type']}: {a['msg']}" for a in pending]
            sel = st.selectbox("选择报警处理", opts)
            if st.button("✅ 确认处理"):
                for a in st.session_state.alarms:
                    if a["status"]=="待处理" and f"{a['time']} {a['type']}: {a['msg']}" == sel:
                        a["status"] = "已处理"
                        break
                st.rerun()

with tab2:
    st.subheader("🐑 育肥羊个体孪生卡片")
    sheep_list = data["sheep"]
    cols = st.columns(len(sheep_list))
    for i, sheep in enumerate(sheep_list):
        with cols[i]:
            health_icon = "🟢" if sheep["health"]=="normal" else "🔴"
            st.markdown(f"**{sheep['ear_tag']}**")
            st.write(f"{health_icon} 体温: {sheep['temp']}℃")
            st.write(f"采食: {sheep['feed']} kg")
            st.progress(min(1, sheep['feed']/3))

st.caption("数据每秒自动刷新 | 无外部图表依赖，稳定运行")
time.sleep(1)
st.rerun()