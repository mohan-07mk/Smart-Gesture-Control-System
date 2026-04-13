"""
╔══════════════════════════════════════════════════════════════════╗
║   JARVIS GESTURE CONTROL SYSTEM  —  Dashboard v5 FINAL           ║
║   Fixed slider text overlap · Iron Man side animations           ║
║   Futuristic running tech display                                ║
╚══════════════════════════════════════════════════════════════════╝

pip install PyQt5 opencv-python mediapipe pyautogui psutil
pip install screen-brightness-control pycaw comtypes
"""

import sys, time, math, os, threading, collections
import cv2, mediapipe as mp, pyautogui, psutil, numpy as np

try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except Exception:
    SBC_AVAILABLE = False

try:
    from ctypes import POINTER, cast
    import comtypes
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _dev = AudioUtilities.GetSpeakers()
    _ifc = _dev.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
    volume_ctrl = cast(_ifc, POINTER(IAudioEndpointVolume))
    PYCAW_AVAILABLE = True
except Exception:
    volume_ctrl = None
    PYCAW_AVAILABLE = False

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QSizePolicy,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QScrollArea
)
from PyQt5.QtCore  import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui   import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush,
    QFont, QLinearGradient, QRadialGradient, QPainterPath, QPalette
)

# ── PALETTE ─────────────────────────────────────────────────────────
BG      = QColor("#08111E")
PANEL   = QColor("#0B1929")
BORDER  = QColor("#0F3F60")
BORDER2 = QColor("#1A5C82")
CYAN    = QColor("#00E5FF")
CYAN_D  = QColor("#0097A7")
ORANGE  = QColor("#FF6D00")
ORANGE2 = QColor("#FFA040")
GREEN   = QColor("#00E676")
RED     = QColor("#FF1744")
TEXT    = QColor("#C8E8F8")
TEXT_D  = QColor("#3A6680")
TEXT_M  = QColor("#7AB8D4")
WHITE   = QColor("#EAF6FF")

def hex2q(h): return QColor(h)

# ── FONTS ───────────────────────────────────────────────────���────────
def F(size, bold=False, mono=True):
    f = QFont("Consolas" if mono else "Segoe UI", size)
    if bold: f.setWeight(QFont.Bold)
    return f

# ════════════════════════════════════════════════════════════════════
#  GESTURE WORKER
# ════════════════════════════════════════════════════════════════════
class GestureWorker(QThread):
    frame_ready    = pyqtSignal(np.ndarray)
    volume_changed = pyqtSignal(int)
    bright_changed = pyqtSignal(int)
    notification   = pyqtSignal(str)
    gesture_name   = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        mpH   = mp.solutions.hands
        mpDrw = mp.solutions.drawing_utils
        hands = mpH.Hands(max_num_hands=1, model_complexity=0,
                          min_detection_confidence=0.70,
                          min_tracking_confidence=0.70)
        tips  = [4, 8, 12, 16, 20]

        BRI_STEP=2; BRI_INT=0.08; VOL_CD=0.04; SS_CD=2.0; CFR=3
        dl = os.path.join(os.path.expanduser("~"), "Downloads")

        lv=lb=ls=0; pd=0; sf=0

        def dst(a,b): return math.hypot(b[0]-a[0], b[1]-a[1])
        def fup(lm):
            f=[]
            f.append(1 if lm[4][0]>lm[3][0] else 0)
            for i in range(1,5):
                f.append(1 if lm[tips[i]][1]<lm[tips[i]-2][1] else 0)
            return f

        while self._running:
            ok, fr = cap.read()
            if not ok: time.sleep(0.01); continue
            fr  = cv2.flip(fr, 1)
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)
            h,w = fr.shape[:2]; now=time.time(); gl="—"

            if res.multi_hand_landmarks:
                for hlm in res.multi_hand_landmarks:
                    mpDrw.draw_landmarks(fr, hlm, mpH.HAND_CONNECTIONS,
                        mpDrw.DrawingSpec(color=(0,229,255), thickness=2, circle_radius=3),
                        mpDrw.DrawingSpec(color=(0,120,180), thickness=2))
                    lm=[(int(l.x*w),int(l.y*h)) for l in hlm.landmark]
                    if lm[0][1]<80: continue
                    fi=fup(lm); th=lm[4]; ix=lm[8]; d=dst(th,ix)
                    if abs(d-pd)<8: sf+=1
                    else: sf=0
                    pd=d
                    if sf<CFR: continue

                    if fi==[0,1,1,1,0]:
                        gl="SCREENSHOT"
                        if now-ls>SS_CD:
                            fn=os.path.join(dl,f"screenshot_{int(now)}.png")
                            pyautogui.screenshot(fn)
                            self.notification.emit("📸  Screenshot saved")
                            ls=now
                    elif fi==[1,1,1,1,1]:
                        gl="BRIGHT ▲"
                        if SBC_AVAILABLE and now-lb>BRI_INT:
                            cv=sbc.get_brightness()[0]; nv=min(100,cv+BRI_STEP)
                            sbc.set_brightness(nv)
                            self.bright_changed.emit(nv)
                            self.notification.emit(f"☀  Brightness → {nv}%")
                            lb=now
                    elif fi==[0,0,0,0,0]:
                        gl="BRIGHT ▼"
                        if SBC_AVAILABLE and now-lb>BRI_INT:
                            cv=sbc.get_brightness()[0]; nv=max(0,cv-BRI_STEP)
                            sbc.set_brightness(nv)
                            self.bright_changed.emit(nv)
                            self.notification.emit(f"🌑  Brightness → {nv}%")
                            lb=now
                    else:
                        if d<45:
                            gl="VOL ▼"
                            if now-lv>VOL_CD: pyautogui.press("volumedown"); lv=now
                        elif d>65:
                            gl="VOL ▲"
                            if now-lv>VOL_CD: pyautogui.press("volumeup"); lv=now
                        else: gl="STANDBY"

            self.gesture_name.emit(gl)
            self.frame_ready.emit(fr.copy())
            time.sleep(0.001)

        cap.release()
        hands.close()


# ════════════════════════════════════════════════════════════════════
#  ARC REACTOR
# ════════════════════════════════════════════════════════════════════
class ArcReactor(QWidget):
    def __init__(self, size=220, parent=None):
        super().__init__(parent)
        self._sz  = size
        self._ang = 0.0
        self._pls = 0.0
        self._pd  = 1
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def _tick(self):
        self._ang = (self._ang+1.8)%360
        self._pls += 0.035*self._pd
        if self._pls>=1: self._pd=-1
        elif self._pls<=0: self._pd=1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx=cy=self._sz//2; r=cx-12

        # multi-layer glow
        for gw,al in [(r+20,25),(r+13,45),(r+6,80),(r+2,120)]:
            c=QColor(0,229,255,al)
            p.setPen(QPen(c,2)); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx,cy),gw,gw)

        # bg
        bg=QRadialGradient(cx,cy,r)
        bg.setColorAt(0.0,QColor(0,90,140,220))
        bg.setColorAt(0.55,QColor(0,45,80,200))
        bg.setColorAt(1.0,QColor(4,12,28,230))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(bg))
        p.drawEllipse(QPointF(cx,cy),r,r)

        # outer rotating arcs (12 segments)
        for i in range(12):
            a=(self._ang+i*30)*math.pi/180
            col=QColor(0,229,255,200) if i%3!=2 else QColor(255,109,0,180)
            p.setPen(QPen(col,2.5,Qt.SolidLine,Qt.RoundCap))
            rect=QRectF(cx-r+12,cy-r+12,2*(r-12),2*(r-12))
            p.drawArc(rect,int((self._ang+i*30)*16),int(18*16))

        # mid ring (counter-rotating)
        for i in range(8):
            a=(-self._ang*1.3+i*45)*math.pi/180
            p.setPen(QPen(QColor(0,170,255,150),1.5))
            mr=r-28
            rect2=QRectF(cx-mr,cy-mr,2*mr,2*mr)
            p.drawArc(rect2,int((-self._ang*1.3+i*45)*16),int(22*16))

        # inner diamond ring
        for i in range(4):
            a=(self._ang*2+i*90)*math.pi/180
            ir=r-48
            x1=cx+ir*math.cos(a); y1=cy+ir*math.sin(a)
            x2=cx+ir*math.cos(a+0.4); y2=cy+ir*math.sin(a+0.4)
            p.setPen(QPen(QColor(255,200,50,int(150+100*self._pls)),1.5))
            p.drawLine(QPointF(x1,y1),QPointF(x2,y2))

        # hexagon
        hr=r-56
        path=QPainterPath()
        for i in range(6):
            a=math.radians(self._ang*0.4+i*60)
            pt=QPointF(cx+hr*math.cos(a), cy+hr*math.sin(a))
            path.moveTo(pt) if i==0 else path.lineTo(pt)
        path.closeSubpath()
        p.setPen(QPen(QColor(0,220,255,int(160+90*self._pls)),2))
        p.setBrush(QBrush(QColor(0,70,110,120)))
        p.drawPath(path)

        # core glow
        cg=QRadialGradient(cx,cy,20)
        cg.setColorAt(0.0,QColor(230,248,255,255))
        cg.setColorAt(0.35,QColor(0,220,255,240))
        cg.setColorAt(0.7,QColor(0,120,200,80))
        cg.setColorAt(1.0,QColor(0,60,140,0))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(cg))
        p.drawEllipse(QPointF(cx,cy),20,20)
        p.end()


# ════════════════════════════════════════════════════════════════════
#  LIVE GRAPH
# ════════════════════════════════════════════════════════════════════
class LiveGraph(QWidget):
    def __init__(self, label, color, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = color
        self._data  = collections.deque([0.0]*90, maxlen=90)
        self._val   = 0
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def push(self, v):
        self._val = int(v); self._data.append(float(v)); self.update()

    def paintEvent(self, _):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); pad=8

        # panel bg
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(6,18,32,230)))
        p.drawRoundedRect(0,0,w,h,6,6)
        p.setPen(QPen(BORDER,1.5)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(0,0,w,h,6,6)

        # grid lines
        p.setPen(QPen(QColor(14,62,95,120),1,Qt.DotLine))
        for frac in [0.25,0.5,0.75]:
            y=int(h-20-(frac*(h-26))); p.drawLine(pad,y,w-pad,y)

        data=list(self._data); n=len(data)
        if n<2: p.end(); return
        xs=[pad+i*(w-2*pad)/(n-1) for i in range(n)]
        ch=h-26
        ys=[h-20-(v/100)*ch for v in data]

        # fill
        pf=QPainterPath()
        pf.moveTo(xs[0],h-20)
        for x,y in zip(xs,ys): pf.lineTo(x,y)
        pf.lineTo(xs[-1],h-20); pf.closeSubpath()
        gr=QLinearGradient(0,0,0,h)
        fc=QColor(self.color); fc.setAlpha(90)
        gc=QColor(self.color); gc.setAlpha(8)
        gr.setColorAt(0,fc); gr.setColorAt(1,gc)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(gr)); p.drawPath(pf)

        # line
        pl=QPainterPath()
        pl.moveTo(xs[0],ys[0])
        for x,y in zip(xs[1:],ys[1:]): pl.lineTo(x,y)
        p.setPen(QPen(self.color,2.5,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        p.setBrush(Qt.NoBrush); p.drawPath(pl)

        # live dot
        p.setPen(Qt.NoPen)
        dot=QColor(self.color); dot.setAlpha(220)
        p.setBrush(QBrush(dot)); p.drawEllipse(QPointF(xs[-1],ys[-1]),5,5)

        # label & value
        p.setPen(QPen(TEXT_D)); p.setFont(F(10))
        p.drawText(pad+4,h-4,self.label)
        p.setPen(QPen(self.color)); p.setFont(F(11,True))
        p.drawText(w-60,h-4,f"{self._val}%")
        p.end()


# ════════════════════════════════════════════════════════════════════
#  THICK VERTICAL BAR - FIXED SLIDER WITH PROPER TEXT SPACING
# ════════════════════════════════════════════════════════════════════
class ThickBar(QWidget):
    def __init__(self, label, sublabel, color, parent=None):
        super().__init__(parent)
        self.label    = label
        self.sublabel = sublabel
        self.color    = color
        self._target  = 50
        self._display = 50.0
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        t=QTimer(self); t.timeout.connect(self._smooth); t.start(16)

    def set_value(self, v):
        self._target = max(0,min(100,int(v)))

    def _smooth(self):
        d=self._target-self._display
        if abs(d)>0.4: self._display+=d*0.12; self.update()

    def paintEvent(self, _):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height()
        
        # FIXED: Reserve 50px at bottom for text area
        text_area_height = 50
        slider_height = h - 90  # Total - top margin - text area
        
        bx,bw=w//2-20,40
        by=60
        bh=slider_height-60

        frac=max(0,min(1,self._display/100))
        filled=int(bh*frac)

        # track
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(10,28,48)))
        p.drawRoundedRect(bx,by,bw,bh,8,8)

        # fill gradient
        if filled>2:
            gr=QLinearGradient(0,by+bh,0,by)
            dim=QColor(self.color); dim.setAlpha(70)
            br=QColor(self.color).lighter(130)
            gr.setColorAt(0,dim); gr.setColorAt(0.6,self.color); gr.setColorAt(1,br)
            p.setBrush(QBrush(gr))
            p.drawRoundedRect(bx,by+bh-filled,bw,filled,8,8)
            # top glow tick
            gl=QPen(QColor(self.color).lighter(160),3.5)
            p.setPen(gl); p.drawLine(bx+4,by+bh-filled+2,bx+bw-4,by+bh-filled+2)

        # border
        p.setPen(QPen(BORDER2,2)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bx,by,bw,bh,8,8)

        # segment ticks
        p.setPen(QPen(QColor(14,62,95,150),1.5))
        for i in range(1,5):
            ty=by+bh-int(bh*i/5)
            p.drawLine(bx+1,ty,bx+bw-1,ty)

        # FIXED: Percentage text in dedicated bottom area
        # This ensures it never overlaps the slider
        text_y_start = by + bh + 10
        p.setPen(QPen(QColor(self.color)))
        p.setFont(F(22,True))
        pct_str=f"{int(self._display)}%"
        p.drawText(0, text_y_start, w, 28, Qt.AlignHCenter | Qt.AlignTop, pct_str)

        # sublabel below percentage
        p.setPen(QPen(TEXT_M))
        p.setFont(F(10))
        p.drawText(0, text_y_start + 30, w, 16, Qt.AlignHCenter | Qt.AlignTop, self.sublabel)

        # top label
        p.setPen(QPen(QColor(self.color)))
        p.setFont(F(11,True))
        p.drawText(0,8,w,22,Qt.AlignHCenter,self.label)

        # icon dots
        p.setPen(Qt.NoPen)
        ic=QColor(self.color); ic.setAlpha(int(80+120*frac))
        p.setBrush(QBrush(ic))
        for i in range(5):
            filled_dot = i < int(frac*5)
            c2=QColor(self.color) if filled_dot else QColor(14,40,60)
            p.setBrush(QBrush(c2))
            p.drawEllipse(QPointF(bx+(bw/6)*(i+0.5)+bw//6,by-18),5,5)

        p.end()


# ════════════════════════════════════════════════════════════════════
#  LEFT ANIMATION PANEL - IRON MAN STYLE
# ════════════════════════════════════════════════════════════════════
class LeftAnimationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(90)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._angle = 0.0
        self._scan_y = 0.0
        self._pulse_y = 0.0
        self._signal = 50.0
        self._sig_dir = 1
        self._time = 0.0
        t = QTimer(self); t.timeout.connect(self._animate); t.start(30)

    def _animate(self):
        self._angle = (self._angle + 2.5) % 360
        self._scan_y = (self._scan_y + 3.5) % 100
        self._pulse_y = (self._pulse_y + 2.2) % 100
        self._signal += 1.2 * self._sig_dir
        if self._signal > 95: self._sig_dir = -1
        elif self._signal < 25: self._sig_dir = 1
        self._time += 0.03
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h = self.width(),self.height()
        
        # Dark background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(4,12,28,180)))
        p.drawRect(0,0,w,h)
        
        # Border
        p.setPen(QPen(QColor(0,100,150,150),1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(0,0,w-1,h-1)
        
        # ── RUNNING SCANNING LINES ──
        p.setPen(QPen(QColor(0,229,255,90),1.5))
        for i in range(5):
            y_offset = int((self._scan_y + i*20) % h)
            p.drawLine(8, y_offset, w-8, y_offset)
            # Glow effect
            p.setPen(QPen(QColor(0,229,255,40),2.5))
            p.drawLine(8, y_offset+1, w-8, y_offset+1)
            p.setPen(QPen(QColor(0,229,255,90),1.5))
        
        # ── ROTATING CIRCULAR INDICATOR ──
        cx, cy = w//2, h//6
        angle_rad = math.radians(self._angle)
        p.setPen(QPen(QColor(0,200,255,150),1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx,cy), 14, 14)
        
        # Rotation marker
        inner_r = 14
        x_end = cx + inner_r * math.cos(angle_rad)
        y_end = cy + inner_r * math.sin(angle_rad)
        p.setPen(QPen(QColor(0,229,255,200),2))
        p.drawLine(QPointF(cx,cy), QPointF(x_end,y_end))
        
        # Rotating dots
        for dot_i in range(3):
            dot_angle = angle_rad + (dot_i * 2 * math.pi / 3)
            dot_x = cx + (inner_r-4) * math.cos(dot_angle)
            dot_y = cy + (inner_r-4) * math.sin(dot_angle)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0,229,255,int(200-60*dot_i))))
            p.drawEllipse(QPointF(dot_x,dot_y), 2, 2)
        
        # ── ANIMATED SIGNAL BARS ──
        bar_y = 2*h//3
        bars = 6
        bar_width = (w-20) // bars
        for i in range(bars):
            # Animated fill based on signal and bar position
            bar_fill = max(0, self._signal - (i * 15))
            filled = bar_fill > 0
            col = QColor(0,229,255,int(180+20*math.sin(self._time + i))) if filled else QColor(0,80,120,60)
            p.setPen(QPen(col,1))
            p.setBrush(QBrush(col))
            bar_h = 6 + i*2.5
            p.drawRect(10+i*bar_width+1, int(bar_y-bar_h), bar_width-2, int(bar_h))
        
        # ── UPWARD DATA PULSES ──
        p.setPen(QPen(QColor(255,150,0,200),1.5))
        for pulse_i in range(4):
            pulse_y = int(h - 40 - (self._pulse_y + pulse_i*25) % (h-40))
            if 40 < pulse_y < h-40:
                p.drawEllipse(QPointF(w//2, pulse_y), 3+pulse_i, 3+pulse_i)
        
        p.end()


# ════════════════════════════════════════════════════════════════════
#  RIGHT ANIMATION PANEL - IRON MAN STYLE
# ════════════════════════════════════════════════════════════════════
class RightAnimationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(90)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._angle = 0.0
        self._radar_angle = 0.0
        self._energy = 50.0
        self._energy_dir = 1
        self._data_offset = 0.0
        self._time = 0.0
        self._hex_angle = 0.0
        t = QTimer(self); t.timeout.connect(self._animate); t.start(30)

    def _animate(self):
        self._angle = (self._angle + 3.2) % 360
        self._radar_angle = (self._radar_angle + 1.8) % 360
        self._hex_angle = (self._hex_angle + 2.5) % 360
        self._energy += 1.5 * self._energy_dir
        if self._energy > 95: self._energy_dir = -1
        elif self._energy < 30: self._energy_dir = 1
        self._data_offset = (self._data_offset + 2.1) % 8
        self._time += 0.03
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h = self.width(),self.height()
        
        # Dark background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(4,12,28,180)))
        p.drawRect(0,0,w,h)
        
        # Border
        p.setPen(QPen(QColor(0,100,150,150),1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(0,0,w-1,h-1)
        
        # ── MINI RADAR ANIMATION ──
        cx, cy = w//2, h//6
        radar_r = 12
        p.setPen(QPen(QColor(0,150,200,100),1))
        p.setBrush(Qt.NoBrush)
        for r_step in range(1,4):
            p.drawEllipse(QPointF(cx,cy), radar_r*r_step//3, radar_r*r_step//3)
        
        # Radar sweep
        sweep_angle = math.radians(self._radar_angle)
        x_sweep = cx + radar_r * math.cos(sweep_angle)
        y_sweep = cy + radar_r * math.sin(sweep_angle)
        p.setPen(QPen(QColor(0,229,255,200),2))
        p.drawLine(QPointF(cx,cy), QPointF(x_sweep,y_sweep))
        
        # Radar targets
        for target_i in range(3):
            target_angle = sweep_angle + math.pi/4 + target_i * math.pi/6
            target_r = radar_r * (0.3 + 0.2*target_i)
            target_x = cx + target_r * math.cos(target_angle)
            target_y = cy + target_r * math.sin(target_angle)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255,150,0,int(180-40*target_i))))
            p.drawEllipse(QPointF(target_x,target_y), 1.5, 1.5)
        
        # ── DIGITAL DATA STREAM ──
        p.setPen(QPen(QColor(0,200,255,120),1))
        for row_i in range(5):
            y_pos = int(h//2 + 15 + (row_i*3 - self._data_offset) % 16)
            if 0 <= y_pos < h:
                p.drawLine(8, y_pos, w-8, y_pos)
        
        # ── ROTATING HEXAGON (BOTTOM) ──
        hex_cx, hex_cy = w//2, 5*h//6
        hex_r = 9
        hex_angle_rad = math.radians(self._hex_angle)
        path = QPainterPath()
        hex_points = []
        for hex_i in range(6):
            angle = hex_angle_rad + hex_i * math.pi / 3
            x = hex_cx + hex_r * math.cos(angle)
            y = hex_cy + hex_r * math.sin(angle)
            hex_points.append(QPointF(x,y))
            if hex_i == 0:
                path.moveTo(QPointF(x,y))
            else:
                path.lineTo(QPointF(x,y))
        path.closeSubpath()
        p.setPen(QPen(QColor(255,150,0,180),1.5))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        
        # Hexagon center glow
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255,150,0,40)))
        p.drawEllipse(QPointF(hex_cx,hex_cy), 4, 4)
        
        # ── VERTICAL ENERGY BAR (RIGHT SIDE) ──
        energy_bar_x = w - 12
        energy_bar_y_start = h // 2 - 25
        energy_bar_h = int(50 * self._energy / 100)
        
        # Background bar
        p.setPen(QPen(QColor(255,150,0,60),1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(energy_bar_x-3, energy_bar_y_start, 6, 50)
        
        # Animated fill
        p.setPen(Qt.NoPen)
        energy_col = QColor(255,150,0,int(160+80*math.sin(self._time)))
        p.setBrush(QBrush(energy_col))
        p.drawRect(energy_bar_x-3, energy_bar_y_start + (50-energy_bar_h), 6, energy_bar_h)
        
        # Energy value display
        p.setPen(QPen(QColor(255,150,0,150)))
        p.setFont(F(8,True))
        p.drawText(energy_bar_x-18, energy_bar_y_start-5, 16, 10, Qt.AlignHCenter, f"{int(self._energy)}%")
        
        p.end()


# ════════════════════════════════════════════════════════════════════
#  ENHANCED CAMERA VIEW WITH SIDE ANIMATIONS
# ════════════════════════════════════════════════════════════════════
class CameraView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pix     = None
        self._gesture = "—"
        self._fps     = 0
        self._fc      = 0
        self._ft      = time.time()
        self._status  = "SYSTEM ACTIVE"
        self._pls     = 0.0
        self._pd      = 1
        self._border_glow = 0.0
        self._border_dir = 1
        
        # Create animation panels
        self.left_anim = LeftAnimationPanel()
        self.right_anim = RightAnimationPanel()
        
        t = QTimer(self); t.timeout.connect(self._anim); t.start(30)

    def _anim(self):
        self._pls += 0.06*self._pd
        if self._pls >= 1: self._pd = -1
        elif self._pls <= 0: self._pd = 1
        
        self._border_glow += 0.08*self._border_dir
        if self._border_glow >= 1: self._border_dir = -1
        elif self._border_glow <= 0: self._border_dir = 1
        
        self.update()

    def set_frame(self, fr: np.ndarray):
        self._fc += 1
        now = time.time()
        if now - self._ft >= 1.0:
            self._fps = self._fc
            self._fc = 0
            self._ft = now
        h,w = fr.shape[:2]
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        qi = QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888)
        self._pix = QPixmap.fromImage(qi)
        self.update()

    def set_gesture(self, g):
        self._gesture = g

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(4,10,20)))
        p.drawRect(0,0,w,h)

        # Left animation panel
        left_pix = QPixmap(90, h-100)
        left_pix.fill(Qt.transparent)
        left_painter = QPainter(left_pix)
        self.left_anim.render(left_painter)
        left_painter.end()
        p.drawPixmap(8, 50, left_pix)

        # Right animation panel
        right_pix = QPixmap(90, h-100)
        right_pix.fill(Qt.transparent)
        right_painter = QPainter(right_pix)
        self.right_anim.render(right_painter)
        right_painter.end()
        p.drawPixmap(w-98, 50, right_pix)

        # Camera feed (center)
        if self._pix:
            scaled = self._pix.scaled(w-200, h-100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = (w-scaled.width())//2
            oy = 50 + (h-100-scaled.height())//2
            p.drawPixmap(ox, oy, scaled)
            cw, ch = scaled.width(), scaled.height()
        else:
            cw, ch = w-200, h-100
            ox = (w-cw)//2
            oy = 50

        # Animated glowing border
        border_alpha = int(80 + 100*self._border_glow)
        for pw, al in [(6,border_alpha//5),(4,border_alpha//3),(2,border_alpha)]:
            bc = QColor(CYAN)
            bc.setAlpha(min(al, border_alpha))
            p.setPen(QPen(bc,pw))
            p.setBrush(Qt.NoBrush)
            p.drawRect(ox,oy,cw,ch)

        # Corner brackets
        BL = 40
        BT = 3.5
        p.setPen(QPen(CYAN,BT))
        for (x0,y0,sx,sy) in [(ox,oy,1,1),(ox+cw,oy,-1,1),(ox,oy+ch,1,-1),(ox+cw,oy+ch,-1,-1)]:
            p.drawLine(x0,y0,x0+sx*BL,y0)
            p.drawLine(x0,y0,x0,y0+sy*BL)

        # Top status bar
        p.setPen(Qt.NoPen)
        sb = QColor(0,8,20,210)
        p.setBrush(QBrush(sb))
        p.drawRect(ox,oy,cw,38)
        sc = QColor(CYAN)
        sc.setAlpha(int(150+105*self._pls))
        p.setPen(QPen(sc))
        p.setFont(F(12,True))
        p.drawText(ox,oy,cw,38,Qt.AlignCenter,f"◈  {self._status}  ◈")

        # Bottom overlay
        p.setPen(Qt.NoPen)
        bb = QColor(0,8,20,200)
        p.setBrush(QBrush(bb))
        p.drawRect(ox,oy+ch-40,cw,40)

        p.setPen(QPen(ORANGE))
        p.setFont(F(13,True))
        p.drawText(ox+12,oy+ch-40,cw//2-12,40,Qt.AlignVCenter,f"✦ {self._gesture}")

        p.setPen(QPen(TEXT_D))
        p.setFont(F(10))
        p.drawText(ox+cw//2,oy+ch-40,cw//2-12,40,Qt.AlignVCenter|Qt.AlignRight,f"FPS {self._fps}")

        p.end()


# ════════════════════════════════════════════════════════════════════
#  EVENT LOG
# ════════════════════════════════════════════════════════════════════
class EventLog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = collections.deque(maxlen=16)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        t=QTimer(self); t.timeout.connect(self.update); t.start(250)

    def push(self, msg):
        self._entries.appendleft((msg, time.time()))

    def paintEvent(self, _):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); now=time.time()
        p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(6,16,30,230)))
        p.drawRoundedRect(0,0,w,h,7,7)
        p.setPen(QPen(BORDER,1.5)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(0,0,w,h,7,7)

        y0=24
        for i,(msg,ts) in enumerate(self._entries):
            if y0>h-8: break
            age=now-ts
            if age>15: continue
            a=255 if age<6 else int(255*(1-(age-6)/9))
            if i==0:
                c=QColor(CYAN); c.setAlpha(a)
                p.setFont(F(11,True))
            else:
                c=QColor(TEXT_D); c.setAlpha(min(a,180))
                p.setFont(F(9))
            p.setPen(QPen(c))
            ts_str=time.strftime("%H:%M:%S",time.localtime(ts))
            p.drawText(14,y0,w-28,18,Qt.AlignVCenter,f"{ts_str}  {msg}")
            y0+=20
        p.end()


# ════════════════════════════════════════════════════════════════════
#  STAT TILE
# ════════════════════════════════════════════════════════════════════
class StatTile(QWidget):
    def __init__(self, label, unit="", color=None, parent=None):
        super().__init__(parent)
        self.label  = label
        self.unit   = unit
        self.color  = color or CYAN
        self._value = "—"
        self.setFixedHeight(66)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, v): self._value=str(v); self.update()

    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height()
        p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(8,22,38,230)))
        p.drawRoundedRect(0,0,w,h,6,6)
        lc=QColor(self.color); lc.setAlpha(200)
        p.setBrush(QBrush(lc))
        p.drawRoundedRect(0,0,5,h,2,2)
        p.setPen(QPen(BORDER,1.5)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(0,0,w,h,6,6)
        p.setPen(QPen(TEXT_D)); p.setFont(F(9))
        p.drawText(14,4,w-16,26,Qt.AlignVCenter,self.label)
        p.setPen(QPen(QColor(self.color))); p.setFont(F(18,True))
        p.drawText(14,30,w-16,32,Qt.AlignVCenter,f"{self._value}{self.unit}")
        p.end()


# ════════════════════════════════════════════════════════════════════
#  SECTION DIVIDER
# ════════════════════════════════════════════════════════════════════
def divider(text, color="#00E5FF"):
    lbl=QLabel(text)
    lbl.setStyleSheet(f"""
        color:{color}; font-family:Consolas; font-size:10px;
        font-weight:bold; letter-spacing:3px;
        padding:6px 0px 6px 0px;
        border-bottom:1px solid #0F3F60;
    """)
    lbl.setMinimumHeight(24)
    return lbl


def hline():
    f=QFrame(); f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color:#0F3F60; background:#0F3F60;"); f.setFixedHeight(2)
    return f


def _vline():
    f=QFrame(); f.setFrameShape(QFrame.VLine)
    f.setStyleSheet("color:#0F3F60;background:#0F3F60;"); f.setFixedWidth(2)
    return f


# ════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ════════════════════════════════════════════════════════════════════
class JARVISv5(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS GESTURE CONTROL SYSTEM  v5")
        self.setMinimumSize(1480, 900)
        self.setStyleSheet(f"background:{BG.name()}; color:{TEXT.name()};")
        self._build()
        self._wire()

    def _build(self):
        root=QWidget(); self.setCentralWidget(root)
        main=QVBoxLayout(root)
        main.setContentsMargins(12, 10, 12, 10)
        main.setSpacing(10)

        # header
        main.addWidget(self._header())

        # body row (25%-50%-25% split)
        body=QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._left_panel(),   stretch=25)
        body.addWidget(self._centre_panel(), stretch=50)
        body.addWidget(self._right_panel(),  stretch=25)
        main.addLayout(body, stretch=1)

        # bottom
        main.addWidget(self._bottom_bar(), stretch=0)

    def _header(self):
        w=QWidget(); w.setFixedHeight(56)
        w.setStyleSheet("""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #08111E,stop:0.15 #0B1929,stop:0.85 #0B1929,stop:1 #08111E);
            border:1px solid #0F3F60; border-radius:7px;
        """)
        lay=QHBoxLayout(w); lay.setContentsMargins(20,0,20,0); lay.setSpacing(16)
        tl=QLabel("◈ ◈ ◈"); tl.setStyleSheet("color:#1565C0;font-size:13px;letter-spacing:8px;font-weight:bold;")
        lay.addWidget(tl)
        lay.addStretch()
        ti=QLabel("J · A · R · V · I · S   GESTURE CONTROL SYSTEM")
        ti.setStyleSheet("color:#00E5FF;font-family:Consolas;font-size:18px;font-weight:bold;letter-spacing:10px;")
        lay.addWidget(ti)
        lay.addStretch()
        self._clk=QLabel(); self._clk.setStyleSheet("color:#3A6680;font-family:Consolas;font-size:12px;font-weight:bold;")
        lay.addWidget(self._clk)
        self._tick_clock()
        ct=QTimer(self); ct.timeout.connect(self._tick_clock); ct.start(1000)
        return w

    def _left_panel(self):
        w=QWidget()
        w.setStyleSheet("background:#0B1929;border:1px solid #0F3F60;border-radius:8px;")
        w.setMinimumWidth(280)
        lay=QVBoxLayout(w); lay.setContentsMargins(14,16,14,16); lay.setSpacing(10)

        lay.addWidget(divider("MASTER VOLUME"))
        self.vol_bar=ThickBar("VOLUME","MASTER VOLUME",CYAN)
        lay.addWidget(self.vol_bar, stretch=1)

        lay.addWidget(hline())

        lay.addWidget(divider("DISPLAY BRIGHTNESS","#FF6D00"))
        self.bri_bar=ThickBar("BRIGHTNESS","DISPLAY BRIGHTNESS",ORANGE)
        lay.addWidget(self.bri_bar, stretch=1)

        lay.addWidget(hline())

        self._gest_lbl=QLabel("—")
        self._gest_lbl.setStyleSheet("""
            color:#FF9800;font-family:Consolas;font-size:22px;
            font-weight:bold;letter-spacing:4px;
            border:1px solid #1A3A50; border-radius:6px;
            padding:8px; background:#060F1C;
        """)
        self._gest_lbl.setAlignment(Qt.AlignCenter)
        self._gest_lbl.setMinimumHeight(42)
        lay.addWidget(self._gest_lbl)

        self._act_dot=QLabel("● SYSTEM ACTIVE")
        self._act_dot.setStyleSheet("color:#00E676;font-family:Consolas;font-size:11px;font-weight:bold;letter-spacing:3px;")
        self._act_dot.setAlignment(Qt.AlignCenter)
        self._act_dot.setMinimumHeight(20)
        lay.addWidget(self._act_dot)
        return w

    def _centre_panel(self):
        w=QWidget()
        w.setStyleSheet("background:#0B1929;border:1px solid #0F3F60;border-radius:8px;")
        lay=QVBoxLayout(w); lay.setContentsMargins(10,10,10,10); lay.setSpacing(10)

        self.cam=CameraView()
        self.cam.setMinimumHeight(300)
        lay.addWidget(self.cam, stretch=1)

        # arc + quick stats row
        bottom_row=QHBoxLayout()
        bottom_row.setSpacing(14)
        bottom_row.setContentsMargins(0,0,0,0)

        self.arc=ArcReactor(220)
        bottom_row.addWidget(self.arc, alignment=Qt.AlignVCenter|Qt.AlignHCenter)

        # quick stat tiles (2×2 grid)
        tiles_grid=QWidget()
        tg=QGridLayout(tiles_grid); tg.setSpacing(8); tg.setContentsMargins(0,0,0,0)
        self.tile_fps  =StatTile("CAMERA FPS","",CYAN)
        self.tile_gest =StatTile("GESTURE","",ORANGE)
        self.tile_cpu  =StatTile("CPU","%",GREEN)
        self.tile_ram  =StatTile("RAM","%",QColor("#FF5252"))
        tg.addWidget(self.tile_fps, 0,0)
        tg.addWidget(self.tile_gest,0,1)
        tg.addWidget(self.tile_cpu, 1,0)
        tg.addWidget(self.tile_ram, 1,1)
        bottom_row.addWidget(tiles_grid, stretch=1)

        lay.addLayout(bottom_row, stretch=0)
        return w

    def _right_panel(self):
        w=QWidget()
        w.setStyleSheet("background:#0B1929;border:1px solid #0F3F60;border-radius:8px;")
        w.setMinimumWidth(280)
        
        scroll = QScrollArea()
        scroll.setStyleSheet("QScrollArea { background:#0B1929; border:none; }")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content=QWidget()
        lay=QVBoxLayout(content); lay.setContentsMargins(14,16,14,16); lay.setSpacing(10)

        lay.addWidget(divider("SYSTEM TELEMETRY"))

        self.cpu_graph  = LiveGraph("CPU USAGE",  CYAN)
        self.ram_graph  = LiveGraph("RAM USAGE",  ORANGE)
        self.net_graph  = LiveGraph("NETWORK I/O",QColor("#76FF03"))
        lay.addWidget(self.cpu_graph, stretch=0)
        lay.addWidget(self.ram_graph, stretch=0)
        lay.addWidget(self.net_graph, stretch=0)

        lay.addWidget(hline())
        lay.addWidget(divider("SYSTEM INFO","#3A6680"))

        self.up_tile   =StatTile("UPTIME",    "",TEXT_M)
        self.disk_tile =StatTile("DISK USED", "%",QColor("#FF9800"))
        self.thr_tile  =StatTile("THREADS",   "",QColor("#CE93D8"))
        self.time_tile =StatTile("LOCAL TIME","",CYAN_D)
        for t in [self.up_tile,self.disk_tile,self.thr_tile,self.time_tile]:
            lay.addWidget(t, stretch=0)

        lay.addWidget(hline())
        lay.addWidget(divider("GESTURE MAP","#3A6680"))

        gestures=[("5 fingers","Brightness ▲"),("Fist","Brightness ▼"),
                  ("Pinch","Volume ▼"),("Spread","Volume ▲"),("3 fingers","Screenshot")]
        for g,a in gestures:
            row=QHBoxLayout(); row.setSpacing(6)
            gl=QLabel(f"✦ {g}"); gl.setStyleSheet("color:#007BA8;font-family:Consolas;font-size:10px;font-weight:bold;")
            al=QLabel(a);        al.setStyleSheet("color:#3A6680;font-family:Consolas;font-size:10px;")
            row.addWidget(gl); row.addStretch(); row.addWidget(al)
            lay.addLayout(row, stretch=0)

        lay.addStretch()
        
        scroll.setWidget(content)
        main_lay = QVBoxLayout(w)
        main_lay.setContentsMargins(0,0,0,0)
        main_lay.addWidget(scroll)
        return w

    def _bottom_bar(self):
        w=QWidget()
        w.setMinimumHeight(160)
        w.setMaximumHeight(180)
        w.setStyleSheet("background:#0B1929;border:1px solid #0F3F60;border-radius:8px;")
        lay=QHBoxLayout(w); lay.setContentsMargins(14,12,14,12); lay.setSpacing(12)

        # event log (left)
        lv=QVBoxLayout(); lv.setSpacing(6); lv.setContentsMargins(0,0,0,0)
        lv.addWidget(divider("EVENT LOG  //  GESTURE HISTORY"))
        self.log=EventLog()
        self.log.setMinimumHeight(100)
        lv.addWidget(self.log, stretch=1)
        lay.addLayout(lv, stretch=1)

        lay.addWidget(_vline())

        # mode status (right)
        rv=QVBoxLayout(); rv.setSpacing(8); rv.setContentsMargins(0,0,0,0)
        rv.addWidget(divider("MODE STATUS","#FF6D00"))
        mode_grid=QGridLayout(); mode_grid.setSpacing(8); mode_grid.setContentsMargins(0,0,0,0)
        self.m_gesture =StatTile("GESTURE MODE","",GREEN)
        self.m_cam     =StatTile("CAMERA","",CYAN)
        self.m_vol     =StatTile("VOLUME","",ORANGE)
        self.m_bri     =StatTile("BRIGHTNESS","",ORANGE)
        mode_grid.addWidget(self.m_gesture,0,0)
        mode_grid.addWidget(self.m_cam    ,0,1)
        mode_grid.addWidget(self.m_vol    ,1,0)
        mode_grid.addWidget(self.m_bri    ,1,1)
        rv.addLayout(mode_grid, stretch=1)
        lay.addLayout(rv, stretch=1)
        return w

    def _wire(self):
        self.gw=GestureWorker()
        self.gw.frame_ready.connect(self.cam.set_frame)
        self.gw.volume_changed.connect(self.vol_bar.set_value)
        self.gw.bright_changed.connect(self.bri_bar.set_value)
        self.gw.notification.connect(self._on_notif)
        self.gw.gesture_name.connect(self._on_gesture)
        self.gw.start()

        st=QTimer(self); st.timeout.connect(self._poll_stats); st.start(500)
        vt=QTimer(self); vt.timeout.connect(self._poll_vol);   vt.start(300)
        tt=QTimer(self); tt.timeout.connect(self._poll_tiles); tt.start(200)

        QTimer.singleShot(400,  lambda: self.log.push("⚡  JARVIS v5 system online"))
        QTimer.singleShot(900,  lambda: self.log.push("🎯  Gesture tracking active"))
        QTimer.singleShot(1400, lambda: self.log.push("📡  Iron Man animations initialized"))

        self.m_gesture.set_value("ONLINE")
        self.m_cam.set_value("ACTIVE")

        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()

    def _on_notif(self, msg):
        self.log.push(msg)

    def _on_gesture(self, name):
        self._gest_lbl.setText(name)
        self.cam.set_gesture(name)
        self.tile_gest.set_value(name[:10])

    def _poll_stats(self):
        cpu=psutil.cpu_percent()
        ram=psutil.virtual_memory().percent
        disk=psutil.disk_usage('/').percent

        now=time.time(); nc=psutil.net_io_counters()
        dt=max(0.01,now-self._last_net_t)
        net_mb=(nc.bytes_sent+nc.bytes_recv-self._last_net.bytes_sent-self._last_net.bytes_recv)/dt/1024/1024
        net_pct=min(100,net_mb*5)
        self._last_net=nc; self._last_net_t=now

        self.cpu_graph.push(cpu)
        self.ram_graph.push(ram)
        self.net_graph.push(net_pct)
        self.tile_cpu.set_value(f"{int(cpu)}")
        self.tile_ram.set_value(f"{int(ram)}")
        self.disk_tile.set_value(f"{int(disk)}")
        self.thr_tile.set_value(str(threading.active_count()))
        self.m_vol.set_value(f"{self.vol_bar._target}%")
        self.m_bri.set_value(f"{self.bri_bar._target}%")

        bt=int(time.time()-psutil.boot_time())
        h,r=divmod(bt,3600); m,s=divmod(r,60)
        self.up_tile.set_value(f"{h:02d}:{m:02d}:{s:02d}")

    def _poll_vol(self):
        if PYCAW_AVAILABLE and volume_ctrl:
            try: self.vol_bar.set_value(int(volume_ctrl.GetMasterVolumeLevelScalar()*100))
            except: pass
        if SBC_AVAILABLE:
            try: self.bri_bar.set_value(sbc.get_brightness()[0])
            except: pass

    def _poll_tiles(self):
        fps=self.cam._fps
        self.tile_fps.set_value(str(fps))
        self.time_tile.set_value(time.strftime("%H:%M:%S"))

    def _tick_clock(self):
        self._clk.setText(time.strftime("%Y-%m-%d   %H:%M:%S"))

    def closeEvent(self, e):
        self.gw.stop(); e.accept()


# ════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    app=QApplication(sys.argv); app.setStyle("Fusion")
    pal=QPalette()
    pal.setColor(QPalette.Window,        QColor("#08111E"))
    pal.setColor(QPalette.WindowText,    QColor("#C8E8F8"))
    pal.setColor(QPalette.Base,          QColor("#0B1929"))
    pal.setColor(QPalette.AlternateBase, QColor("#08131E"))
    pal.setColor(QPalette.Text,          QColor("#C8E8F8"))
    pal.setColor(QPalette.Button,        QColor("#0B1929"))
    pal.setColor(QPalette.ButtonText,    QColor("#00E5FF"))
    pal.setColor(QPalette.Highlight,     QColor("#00E5FF"))
    pal.setColor(QPalette.HighlightedText,QColor("#08111E"))
    app.setPalette(pal)
    w=JARVISv5(); w.showMaximized()
    sys.exit(app.exec_())