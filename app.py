import streamlit as st
import streamlit.components.v1 as components
import random
import time
import json
import math
from datetime import datetime

st.set_page_config(page_title="育肥羊数字孪生平台", layout="wide")
st.title("🐑 育肥羊数字孪生云平台")
st.markdown("**2D/3D数字孪生 · 双向交互 · 故障预判 · 告警闭环**")

# ==================== 羊舍布局 ====================
PEN_WIDTH, PEN_LENGTH, PEN_COLS = 20.0, 30.0, 5
PEN_LAYOUTS = [(0, 0, PEN_WIDTH, 6), (0, 6, PEN_WIDTH, 6), (0, 12, PEN_WIDTH, 6), (0, 18, PEN_WIDTH, 6), (0, 24, PEN_WIDTH, 6)]
FAN_POSITIONS = [(0.5, 3), (0.5, 9), (0.5, 15), (0.5, 21), (0.5, 27)]
FEEDER_POS = (PEN_WIDTH - 0.5, PEN_LENGTH / 2)
WATER_POS = (1.5, 1)

# ==================== 侧边栏：控制与参数配置 ====================
with st.sidebar:
    st.header("🎮 虚拟控制台")
    vent_level = st.slider("通风机转速 (%)", 0, 100, 60)
    humidifier = st.checkbox("加湿器", False)
    feed_mode = st.selectbox("投喂模式", ["正常", "增量", "减量"])

    with st.expander("⚙️ 报警阈值配置"):
        temp_high = st.number_input("高温预警 (℃)", value=39.5)
        temp_critical = st.number_input("高温紧急 (℃)", value=40.0)
        temp_low = st.number_input("低温预警 (℃)", value=38.0)
        feed_drop_warn = st.slider("采食下降预警 (%)", 5, 30, 15) / 100
        feed_drop_crit = st.slider("采食骤降紧急 (%)", 10, 40, 25) / 100

    st.markdown("---")
    st.caption("控制与阈值实时生效")
    st.markdown("**📋 操作日志**")
    if "control_log" not in st.session_state:
        st.session_state.control_log = []
    for log in st.session_state.control_log[-5:]:
        st.text(log)

# ==================== 模拟数据生成 ====================
def generate_data(vent, hum_on, feed_mode):
    base_temp = 39.0 + random.uniform(-0.5, 0.5)
    temp = base_temp - (vent - 50) * 0.02
    humidity = 60 + random.uniform(-10, 10)
    if hum_on: humidity += 15
    ammonia = max(0, 15 + random.uniform(-5, 5) - vent * 0.15)
    if feed_mode == "正常": feed_weight = 10 + random.uniform(-2, 2)
    elif feed_mode == "增量": feed_weight = 12 + random.uniform(-1, 3)
    else: feed_weight = 8 + random.uniform(-2, 1)
    feed_weight = max(3, min(15, feed_weight))
    motor_current = random.choice([0, 0, 2.5, 2.6, 2.7]) if random.random() > 0.05 else 0
    device_online = random.random() > 0.05

    sheep_data = []
    for i in range(1, 6):
        pen_idx = (i - 1) % PEN_COLS
        pen = PEN_LAYOUTS[pen_idx]
        sx = pen[0] + random.uniform(2, pen[2] - 2)
        sy = pen[1] + random.uniform(1, pen[3] - 1)
        stemp = temp + random.uniform(-0.3, 0.3)
        sfeed = feed_weight * random.uniform(0.15, 0.25)
        health = "normal" if temp_low <= stemp <= temp_high else "warning"
        sheep_data.append({
            "ear_tag": f"YF-{i:03d}", "temp": round(stemp, 1), "feed": round(sfeed, 2),
            "health": health, "x": round(sx, 1), "y": round(sy, 1), "pen": pen_idx + 1
        })
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "temperature": round(temp, 1), "humidity": round(humidity, 1),
        "ammonia": round(ammonia, 1), "feed_weight": round(feed_weight, 1),
        "motor_current": motor_current, "device_online": device_online, "sheep": sheep_data
    }

# ==================== 初始化状态 ====================
if "alarms" not in st.session_state: st.session_state.alarms = []
if "last_feed" not in st.session_state: st.session_state.last_feed = 10.0
if "history" not in st.session_state: st.session_state.history = []
if "control_log" not in st.session_state: st.session_state.control_log = []
if "prev_vent" not in st.session_state: st.session_state.prev_vent = 60
if "prev_hum" not in st.session_state: st.session_state.prev_hum = False
if "prev_feed" not in st.session_state: st.session_state.prev_feed = "正常"
if "selected_sheep" not in st.session_state: st.session_state.selected_sheep = None

# 控制日志
if vent_level != st.session_state.prev_vent:
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} 通风调至 {vent_level}%")
    st.session_state.prev_vent = vent_level
if humidifier != st.session_state.prev_hum:
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} {'开启' if humidifier else '关闭'}加湿器")
    st.session_state.prev_hum = humidifier
if feed_mode != st.session_state.prev_feed:
    st.session_state.control_log.append(f"{datetime.now().strftime('%H:%M:%S')} 投喂模式切换至{feed_mode}")
    st.session_state.prev_feed = feed_mode

data = generate_data(vent_level, humidifier, feed_mode)
st.session_state.history.append(data)
if len(st.session_state.history) > 30: st.session_state.history.pop(0)

# ==================== 报警引擎（分级+闭环） ====================
def check_alarms(data):
    new_alarms = []
    temp = data["temperature"]
    if temp > temp_critical:
        new_alarms.append({"type": "高温紧急", "msg": f"温度 {temp}℃ > {temp_critical}℃", "level": "critical"})
    elif temp > temp_high:
        new_alarms.append({"type": "高温预警", "msg": f"温度 {temp}℃ 偏高", "level": "warning"})
    elif temp < temp_low:
        new_alarms.append({"type": "低温预警", "msg": f"温度 {temp}℃ 偏低", "level": "warning"})
    cur_feed = data["feed_weight"]
    if st.session_state.last_feed > 0:
        change = (cur_feed - st.session_state.last_feed) / st.session_state.last_feed
        if change < -feed_drop_crit:
            new_alarms.append({"type": "采食骤降", "msg": f"料槽变化 {change*100:.0f}%", "level": "critical"})
        elif change < -feed_drop_warn:
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

# ==================== 故障预测（量化+原因） ====================
def predict_risk(history):
    if len(history) < 5: return []
    temps = [h["temperature"] for h in history]
    feeds = [h["feed_weight"] for h in history]
    n = len(temps)
    x_mean = (n - 1) / 2
    y_mean = sum(temps) / n
    num = sum((i - x_mean) * (t - y_mean) for i, t in enumerate(temps))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den else 0
    f_mean = sum(feeds) / n
    f_num = sum((i - x_mean) * (f - f_mean) for i, f in enumerate(feeds))
    f_slope = f_num / den if den else 0
    preds = []
    if slope > 0.15:
        risk = min(95, int(abs(slope) * 300))
        preds.append({"type": "🔴 高温紧急风险", "msg": f"温度快速攀升 (风险 {risk}%)。可能原因：通风不足、外部高温。建议：立即检查风机，加大通风量。", "level": "critical"})
    elif slope > 0.08:
        risk = min(80, int(abs(slope) * 200))
        preds.append({"type": "🟡 温度上升风险", "msg": f"温度持续上升 (风险 {risk}%)。可能原因：羊群密度大、通风效率降低。建议：关注温度，准备加大通风。", "level": "warning"})
    if f_slope < -0.08:
        risk = min(85, int(abs(f_slope) * 300))
        preds.append({"type": "🟡 采食下降风险", "msg": f"采食量持续下降 (风险 {risk}%)。可能原因：饲料适口性差、羊只应激。建议：检查饲料质量，观察羊只行为。", "level": "warning"})
    return preds

predictions = predict_risk(st.session_state.history)

# ==================== 2D 布局 ====================
def generate_2d_html(data, selected_tag):
    sheep_items = "".join(
        f"""<div class='sheep' style='left:{s['x']/PEN_WIDTH*100}%; bottom:{s['y']/PEN_LENGTH*100}%; {"border: 3px solid yellow;" if s['ear_tag']==selected_tag else ""}'>
            <div class='sheep-emoji'>🐑</div>
            <div class='sheep-tooltip'>🐑{s['ear_tag']}<br>🌡️{s['temp']}℃<br>🍽️{s['feed']}kg</div>
            <div class='dot' style='background:{"#4CAF50" if s["health"]=="normal" else "#F44336"};'></div>
        </div>""" for s in data["sheep"]
    )
    temp = data["temperature"]
    r = min(255, int((temp-38)/3*255)); g = min(255, int((1-(temp-38)/3)*255))
    bg = f"rgba({r},{g},{max(0,255-r-g)},0.2)"
    fans = "".join(f"<div class='fan' style='left:{x/PEN_WIDTH*100}%; bottom:{y/PEN_LENGTH*100}%; animation-duration:{max(0.2,2-vent_level/100*1.8)}s;'>🌀</div>" for x,y in FAN_POSITIONS)
    lines = "".join(f"<div class='line' style='bottom:{i*PEN_LENGTH/PEN_COLS/PEN_LENGTH*100}%;'></div>" for i in range(1,PEN_COLS))
    return f"""<style>
        .pen{{width:100%;height:500px;background:{bg};border:2px solid #555;border-radius:10px;position:relative;overflow:hidden;}}
        .line{{position:absolute;left:0;width:100%;height:2px;background:repeating-linear-gradient(90deg,#888 0px,#888 10px,transparent 10px,transparent 20px);z-index:1;}}
        .sheep{{position:absolute;transform:translate(-50%,50%);cursor:pointer;z-index:10;}}
        .sheep:hover{{transform:translate(-50%,50%) scale(1.2);z-index:20;}}
        .sheep-emoji{{font-size:28px;text-align:center;}}
        .sheep-tooltip{{display:none;position:absolute;bottom:40px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.8);color:#fff;padding:4px 8px;border-radius:6px;font-size:11px;white-space:nowrap;}}
        .sheep:hover .sheep-tooltip{{display:block;}}
        .dot{{width:10px;height:10px;border-radius:50%;position:absolute;top:0;right:0;border:1px solid #fff;}}
        .fan{{position:absolute;font-size:24px;transform:translate(-50%,50%);animation:spin linear infinite;z-index:5;}}
        @keyframes spin{{from{{transform:translate(-50%,50%) rotate(0deg);}}to{{transform:translate(-50%,50%) rotate(360deg);}}}}
        .float-info{{position:absolute;top:10px;right:10px;background:rgba(255,255,255,0.9);padding:8px 12px;border-radius:8px;font-size:14px;font-weight:bold;z-index:15;}}
    </style>
    <div class='pen'>
        {lines}
        <div class='float-info'>🌡️{data["temperature"]}℃ | 💧{data["humidity"]}% | ☁️{data["ammonia"]}ppm</div>
        {fans}
        <div style='position:absolute;left:{FEEDER_POS[0]/PEN_WIDTH*100}%; bottom:{FEEDER_POS[1]/PEN_LENGTH*100}%; font-size:20px;'>🪣</div>
        <div style='position:absolute;left:{WATER_POS[0]/PEN_WIDTH*100}%; bottom:{WATER_POS[1]/PEN_LENGTH*100}%; font-size:20px;'>💧</div>
        {sheep_items}
    </div>"""

# ==================== 3D Canvas 视图（零依赖） ====================
def generate_3d_canvas(data, selected_tag):
    sheep_json = json.dumps(data["sheep"])
    selected_json = json.dumps(selected_tag)
    return f"""
    <canvas id="c3d" style="width:100%;height:450px;border:1px solid #ccc;border-radius:10px;cursor:grab;"></canvas>
    <script>
    (function(){{
        const canvas = document.getElementById('c3d');
        const ctx = canvas.getContext('2d');
        const sheep = JSON.parse('{sheep_json}');
        const selected = JSON.parse('{selected_json}');
        let angle = 0.5, isDrag = false, lastX;
        function project(x,y,z){{
            let px = x*Math.cos(angle) - y*Math.sin(angle);
            let py = x*Math.sin(angle) + y*Math.cos(angle);
            let sx = px*15 + canvas.width/2;
            let sy = -py*15*Math.cos(1) + z*8 + 300;
            return [sx, sy];
        }}
        function draw(){{
            ctx.clearRect(0,0,canvas.width,canvas.height);
            ctx.fillStyle='#f8f8f8';ctx.fillRect(0,0,canvas.width,canvas.height);
            // 地面
            let corners = [project(0,0,37), project(20,0,37), project(20,30,37), project(0,30,37)];
            ctx.beginPath();ctx.moveTo(corners[0][0],corners[0][1]);
            for(let i=1;i<4;i++) ctx.lineTo(corners[i][0],corners[i][1]);
            ctx.closePath();ctx.strokeStyle='#999';ctx.stroke();
            // 栏位线
            for(let i=1;i<5;i++){{
                let p1=project(0,i*6,37), p2=project(20,i*6,37);
                ctx.beginPath();ctx.moveTo(p1[0],p1[1]);ctx.lineTo(p2[0],p2[1]);
                ctx.strokeStyle='#ccc';ctx.setLineDash([5,5]);ctx.stroke();ctx.setLineDash([]);
            }}
            // 羊只
            sheep.forEach(s=>{{
                let g=project(s.x,s.y,37), t=project(s.x,s.y,s.temp);
                let color = s.health==='normal'?'#4CAF50':'#F44336';
                ctx.strokeStyle=color;ctx.lineWidth=(s.ear_tag===selected?6:3);
                ctx.globalAlpha=0.5;ctx.beginPath();ctx.moveTo(g[0],g[1]);ctx.lineTo(t[0],t[1]);ctx.stroke();ctx.globalAlpha=1;
                ctx.fillStyle=color;ctx.beginPath();ctx.arc(t[0],t[1],(s.ear_tag===selected?7:4),0,Math.PI*2);ctx.fill();
                ctx.fillStyle='#000';ctx.font='10px Arial';ctx.fillText(s.ear_tag,t[0]-12,t[1]-10);
            }});
        }}
        function resize(){{ canvas.width = canvas.parentElement.clientWidth; canvas.height = 450; draw(); }}
        window.addEventListener('resize',resize);
        canvas.addEventListener('mousedown',e=>{{isDrag=true;lastX=e.clientX;}});
        window.addEventListener('mouseup',()=>isDrag=false);
        window.addEventListener('mousemove',e=>{{if(!isDrag)return; angle += (e.clientX-lastX)*0.01; lastX=e.clientX; draw();}});
        canvas.addEventListener('wheel',e=>{{e.preventDefault();angle += e.deltaY*0.005; draw();}});
        resize();
    }})();
    </script>
    """

# ==================== 主界面 ====================
tab1, tab2, tab3 = st.tabs(["🏠 2D数字孪生", "🏗️ 3D轻量场景", "📋 数据与报警"])

with tab1:
    st.subheader("羊舍2D实时布局")
    components.html(generate_2d_html(data, st.session_state.selected_sheep), height=520)

with tab2:
    st.subheader("📊 3D 羊舍健康监测（Canvas）")
    st.caption("拖拽旋转 | 滚轮缩放 | 柱子高度=体温 | 绿=正常 红=异常")
    components.html(generate_3d_canvas(data, st.session_state.selected_sheep), height=480)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("🟢 健康羊", "体温正常")
    col_b.metric("🔴 异常羊", "体温偏高/低")
    col_c.metric("📏 柱子", "高度=体温值")

with tab3:
    col_left, col_right = st.columns([2, 1])
    with col_left:
        c1, c2, c3 = st.columns(3)
        temp = data["temperature"]
        color = "red" if temp>40 else ("orange" if temp>39.5 else "green")
        c1.metric("温度 ℃", temp, delta="异常" if color!="green" else "正常")
        c2.metric("湿度 %", data["humidity"])
        c3.metric("氨气 ppm", data["ammonia"])
        st.markdown("---")
        st.subheader("📈 历史记录 (最近5条)")
        recent = list(st.session_state.history)[-5:]
        table_md = "| 时间 | 温度 | 湿度 | 料槽 | 电机 | 设备 |\n|------|------|------|------|------|------|\n"
        for h in recent:
            motor = f"{h['motor_current']:.1f}" if h['motor_current']>0 else "0(停转)"
            dev = "在线" if h['device_online'] else "离线"
            table_md += f"| {h['timestamp']} | {h['temperature']} | {h['humidity']} | {h['feed_weight']} | {motor} | {dev} |\n"
        st.markdown(table_md)

        st.subheader("🔮 故障风险预测")
        if predictions:
            for p in predictions:
                if p["level"] == "critical": st.error(p["msg"])
                else: st.warning(p["msg"])
        else:
            st.success("当前趋势正常")

        # ====== 告警溯源 ======
        st.markdown("---")
        st.subheader("🔍 告警溯源")
        if st.session_state.alarms:
            trace_sel = st.selectbox("选择报警查看当时数据",
                                     [f"{a['time']} {a['type']}: {a['msg']}" for a in st.session_state.alarms[:10]])
            if trace_sel:
                alarm_time = trace_sel.split(" ")[0]
                related = [h for h in st.session_state.history if alarm_time in h["timestamp"]]
                if related:
                    st.caption("报警前后环境数据：")
                    tmd = "| 时间 | 温度 | 湿度 | 料槽 | 电机 | 设备 |\n|------|------|------|------|------|------|\n"
                    for h in related:
                        motor = f"{h['motor_current']:.1f}" if h['motor_current']>0 else "0"
                        dev = "在线" if h['device_online'] else "离线"
                        tmd += f"| {h['timestamp']} | {h['temperature']} | {h['humidity']} | {h['feed_weight']} | {motor} | {dev} |\n"
                    st.markdown(tmd)
                    st.caption("💡 可结合温度、电机电流判断故障原因。")
        else:
            st.info("暂无报警记录")

    with col_right:
        st.subheader("🐑 个体详情")
        sel = next((s for s in data["sheep"] if s["ear_tag"]==st.session_state.selected_sheep), None)
        if sel:
            st.markdown(f"### {sel['ear_tag']}")
            st.write(f"{'🟢' if sel['health']=='normal' else '🔴'} {sel['health']}")
            st.write(f"🌡️ {sel['temp']}℃  🍽️ {sel['feed']}kg")
            st.write(f"📍 栏位{sel['pen']} ({sel['x']},{sel['y']})")
            st.progress(min(1, sel['feed']/3))
            # 单羊历史趋势
            st.markdown("---")
            st.subheader("📈 个体近期趋势")
            sheep_history = []
            for h in st.session_state.history:
                for s in h["sheep"]:
                    if s["ear_tag"] == sel["ear_tag"]:
                        sheep_history.append((h["timestamp"], s["temp"], s["feed"]))
            if sheep_history:
                smd = "| 时间 | 体温 ℃ | 采食 kg |\n|------|--------|--------|\n"
                for t in sheep_history[-5:]:
                    smd += f"| {t[0]} | {t[1]} | {t[2]} |\n"
                st.markdown(smd)
        else:
            st.info("👆 点击2D/3D中的羊只")

        st.markdown("---")
        st.subheader("🚨 报警记录")
        if not st.session_state.alarms:
            st.info("无报警")
        else:
            for a in st.session_state.alarms[:5]:
                icon = "🔴" if a["level"]=="critical" else "🟡"
                st.text(f"{icon} {a['time']} {a['type']} [{a['status']}]")
            pending = [a for a in st.session_state.alarms if a["status"]=="待处理"]
            if pending:
                opts = [f"{a['time']} {a['type']}" for a in pending]
                sel_alarm = st.selectbox("处理报警", opts)
                if st.button("✅ 确认处理"):
                    for a in st.session_state.alarms:
                        if f"{a['time']} {a['type']}" == sel_alarm:
                            a["status"] = "已处理"
                            break
                    st.rerun()

st.caption("每秒自动刷新 | 2D/3D实时映射 | 告警闭环 | 故障预测溯源")
time.sleep(1)
st.rerun()
