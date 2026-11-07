"""One-page vector poster shared by live preview, PDF and Word."""
import io,math,re
from xml.sax.saxutils import escape
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor, toColor
from docx import Document
from docx.shared import Inches,Pt
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree
import pypdfium2
from compact_report import top_topics,short
from standards import group as groups,stats,difficulty,abilities,scored,ABILITIES
def priorities(d):
    qs=[q for q in d['questions'] if not scored(q) or q['score']<q['max']]
    return sorted(qs,key=lambda q:(-q.get('priority',0),not scored(q),-(q['max']-(q['score'] or 0))))
N='#123856'; B='#238aca'; GOLD='#e5a12c'; BORDER='#b9cbd9'; MUTED='#637a8b'; COLORS=[N,B,GOLD,'#58a279','#8664a7']
def default_digest(d):
    rows=[]
    for q in priorities(d)[:5]:
        evidence=q['evidence'];answer=re.search(r'原始作答\s*(.*?)[。；]',evidence);ref=re.search(r'独立参考结果\s*(.*?)[；。]',evidence)
        if answer and ref:evidence=f"第{q['id']}题：答{answer[1]}；参考{ref[1]}"
        else:evidence=f"第{q['id']}题："+evidence.split('。')[0]
        cause=re.split('[，；。]',q['cause'])[0] or '原因待访谈核实'
        action=q['action'];action=re.split('[；。]',action)[0]
        if len(action)>28:action=re.split('[，、]',action)[0]+'；同考点新题复测'
        rows.append({'loss':'待核' if not scored(q) else f"{q['max']-q['score']:g}分",'topic':q['topic'],'evidence':q.get('digestEvidence') or evidence,'mastery':q.get('digestMastery') or cause,'action':q.get('digestAction') or action})
    return rows
class Scene:
    def __init__(self):self.ops=[];self.truncations=[]
    def rect(self,x,y,w,h,fill='white',stroke=None,r=0):self.ops.append(('rect',(x,y,w,h,fill,stroke,r)))
    def line(self,x1,y1,x2,y2,stroke=BORDER,width=1):self.ops.append(('line',(x1,y1,x2,y2,stroke,width)))
    def poly(self,points,fill=None,stroke=None,width=1):self.ops.append(('poly',(points,fill,stroke,width)))
    def circle(self,x,y,r,fill,stroke=None):self.ops.append(('circle',(x,y,r,fill,stroke)))
    def text(self,s,x,y,size=14,color=N,bold=False,anchor='start'):self.ops.append(('text',(str(s),x,y,size,color,bold,anchor)))
    def wrapped(self,s,x,y,width,size=13,lines=3,leading=19,color=N):
        # CJK-safe widths; same lines are used in all outputs.
        result=[];row='';used=0
        for ch in ' '.join(str(s or '').split()):
            unit=size*(1 if ord(ch)>255 else .56)
            if used+unit>width:result.append(row);row='';used=0
            row+=ch;used+=unit
        if row:result.append(row)
        if len(result)>lines:self.truncations.append(str(s));result=result[:lines];result[-1]=result[-1][:-1]+'…'
        for i,t in enumerate(result):self.text(t,x,y+i*leading,size,color)
    def svg(self):
        out=['<svg xmlns="http://www.w3.org/2000/svg" width="840" height="1188" viewBox="0 0 840 1188"><rect width="840" height="1188" fill="white"/>']
        for kind,a in self.ops:
            if kind=='rect':
                x,y,w,h,f,s,r=a;out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f or "none"}" stroke="{s or "none"}"/>')
            elif kind=='line':
                x,y,xx,yy,c,w=a;out.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{c}" stroke-width="{w}"/>')
            elif kind=='circle':
                x,y,r,f,s=a;out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f or "none"}" stroke="{s or "none"}"/>')
            elif kind=='poly':
                pts,f,s,w=a;out.append(f'<polygon points="{" ".join(str(x)+","+str(y) for x,y in pts)}" fill="{f or "none"}" stroke="{s or "none"}" stroke-width="{w}"/>')
            else:
                t,x,y,z,c,b,anchor=a;out.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei,SimSun,sans-serif" font-size="{z}" font-weight="{700 if b else 400}" text-anchor="{anchor}" fill="{c}">{escape(t)}</text>')
        return ''.join(out+['</svg>']).encode()
    def pdf(self):
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));b=io.BytesIO();c=canvas.Canvas(b,pagesize=(595.28,841.89));c.scale(595.28/840,841.89/1188)
        def color(f):return toColor(f) if f else None
        for kind,a in self.ops:
            if kind=='text':
                t,x,y,z,f,bold,anchor=a;c.setFillColor(color(f));c.setFont('STSong-Light',z)
                (c.drawCentredString if anchor=='middle' else c.drawRightString if anchor=='end' else c.drawString)(x,1188-y,t)
            elif kind=='rect':
                x,y,w,h,f,s,r=a
                if f:c.setFillColor(color(f))
                if s:c.setStrokeColor(color(s))
                c.setLineWidth(1);c.roundRect(x,1188-y-h,w,h,r,fill=int(bool(f)),stroke=int(bool(s)))
            elif kind=='circle':
                x,y,r,f,s=a
                if f:c.setFillColor(color(f))
                if s:c.setStrokeColor(color(s))
                c.circle(x,1188-y,r,fill=int(bool(f)),stroke=int(bool(s)))
            elif kind=='line':
                x,y,xx,yy,s,w=a;c.setStrokeColor(color(s));c.setLineWidth(w);c.line(x,1188-y,xx,1188-yy)
            else:
                pts,f,s,w=a;p=c.beginPath();p.moveTo(pts[0][0],1188-pts[0][1])
                for x,y in pts[1:]:p.lineTo(x,1188-y)
                p.close()
                if f:c.setFillColor(color(f))
                if s:c.setStrokeColor(color(s))
                c.setLineWidth(w);c.drawPath(p,fill=int(bool(f)),stroke=int(bool(s)))
        c.save();return b.getvalue()

def panel(s,num,title,x,y,w,h):
    s.rect(x,y,w,h,'#fbfcfe',BORDER,7);s.rect(x,y,43,32,N,None,5);s.text(num,x+21,y+23,22,'white',True,'middle');s.text(title,x+54,y+23,18,N,True);s.line(x,y+34,x+w,y+34)
def scene(d):
    s=Scene();qs=d['questions'];total,score,known=stats(d)
    s.text(d['institution']+'  /  '+d['stage']+'物理学科',28,23,12,MUTED)
    scoreline=f'得分 {score:g}/{known:g} 分' if known==total else f'已核 {score:g}/{known:g} 分 · 待核分值 {total-known:g}' if known else f'成绩待核 · 当前范围 {total:g} 分'
    s.text(scoreline,812,23,12,MUTED,False,'end')
    isretake=d.get('reportKind')=='retake'
    s.rect(28,34,784,52,N,None,5);s.text('讲解后独立复做分析报告' if isretake else '物理试卷测评分析报告',420,69,28,'white',True,'middle')
    identity=d['student']+'  ·  '+d['grade']+'  |  '+d['exam']
    identity_size=15
    while sum(identity_size*(1 if ord(ch)>255 else .56) for ch in identity)>780 and identity_size>11:identity_size-=.5
    s.wrapped(identity,28,114,784,identity_size,1,18)
    if isretake:
        pair=d['pairedScores'];comparison=f"共同已核{pair['count']}题：首次 {pair['before']:g}/{pair['max']:g} → 复做 {pair['after']:g}/{pair['max']:g}" if pair['count'] else '共同题组得分尚待核定'
        s.text(f"复做日期 {d.get('retakeDate') or '待填写'}  · {comparison}  · 范围{len(qs)}题 / {total:g}分",28,132,11,MUTED)
    # 01 gauge and text
    panel(s,'01','整体难度评估',28,140,384,194)
    diff=groups(d,'difficulty');level=difficulty(d);weighted=level['weighted'];label=level['label']
    s.wrapped('试卷综合难度：'+label,42,198,195,15,1,18)
    bullets=d.get('difficultyPoints') or ['基础题占比 '+f'{diff.get("基础",[0])[0]/total:.0%}','综合题关注条件与过程','实验题关注原理与方法']
    for i,t in enumerate(bullets[:3]):s.wrapped('• '+str(t),42,226+i*29,166,12.5,2,14)
    conclusion=d.get('difficultyConclusion') or ('先补'+priorities(d)[0]['topic'] if priorities(d) else '巩固方法并用新题复测')
    s.wrapped(conclusion,42,319,166,11.5,1,14)
    cx,cy,r=315,275,65
    for i in range(36):
        a=math.pi+i*math.pi/36;b=math.pi+(i+1)*math.pi/36
        pts=[(cx+rr*math.cos(t),cy+rr*math.sin(t)) for rr,t in [(r,a),(r,b),(r-11,b),(r-11,a)]];s.poly(pts,B if i<18 else GOLD)
    s.text('0',242,291,11,MUTED);s.text('1',374,291,11,MUTED);s.text(f"{level['normalized']:.2f}",315,198,13,N,True,'middle')
    a=math.pi+level['normalized']*math.pi;end=(cx+51*math.cos(a),cy+51*math.sin(a));s.line(cx,cy,*end,N,5);s.circle(cx,cy,8,N);s.circle(cx,cy,3,'white');s.text(label,315,320,20,N,True,'middle')
    # 02 type table
    panel(s,'02','题型结构分析',426,140,386,194)
    x,y=438,185;widths=[87,55,64,156];headers=['题型','占比','难度','核心能力'];xx=x
    for w,t in zip(widths,headers):s.rect(xx,y,w,27,N);s.text(t,xx+w/2,y+19,13,'white',True,'middle');xx+=w
    tg=groups(d,'type');items=list(tg.items());rows=items if len(items)<=5 else items[:4]+[('其他题型',[sum(v[0] for _,v in items[4:]),0,0])]
    for i,(k,v) in enumerate(rows):
        yy=y+27+i*24;related=[q for q in qs if q['type']==k];wd=sum({'基础':1,'中档':2,'提升':3}[q['difficulty']]*q['max'] for q in related)/v[0] if related else 2;ability=Counter(q['ability'] for q in related).most_common(1)
        vals=[k,f'{v[0]/total:.0%}',('基础' if wd<1.5 else '中档' if wd<2.4 else '提升'),ability[0][0] if ability else '综合运用'];xx=x
        for w,t in zip(widths,vals):s.rect(xx,yy,w,24,'white' if i%2==0 else '#eef4f8',BORDER);s.text(short(t,max(3,int((w-8)/13))),xx+w/2,yy+17,13,N,False,'middle');xx+=w
    # 03 donut
    panel(s,'03','考点分布',28,348,384,210);items=top_topics(d);cx,cy,r=133,472,70;start=-math.pi/2
    for i,(k,v) in enumerate(items):
        end=start+2*math.pi*v/total;n=max(3,int((end-start)*20));pts=[(cx,cy)]+[(cx+r*math.cos(start+(end-start)*j/n),cy+r*math.sin(start+(end-start)*j/n)) for j in range(n+1)];s.poly(pts,COLORS[i]);a=(start+end)/2
        if v/total>=.08:s.text(f'{v/total:.0%}',cx+r*.77*math.cos(a),cy+r*.77*math.sin(a)+4,15,'white',True,'middle')
        yy=412+i*29;s.circle(226,yy-4,5,COLORS[i]);s.text(short(k,10),238,yy,12);s.text(f'{v/total:.0%}',398,yy,13,N,True,'end');start=end
    s.circle(cx,cy,32,'white');s.text('物理',cx,cy+5,17,N,True,'middle')
    # 04 radar, do not invent zero values for unknown axes
    panel(s,'04','学生能力画像',426,348,386,210);cx,cy,R=549,469,57;ag=abilities(d.get('radarCurrent',d));angles=[-math.pi/2+i*2*math.pi/5 for i in range(5)]
    for ring in [.25,.5,.75,1]:s.poly([(cx+R*ring*math.cos(a),cy+R*ring*math.sin(a)) for a in angles],None,'#c9d6df')
    points=[]
    for k,a in zip(ABILITIES,angles):
        s.line(cx,cy,cx+R*math.cos(a),cy+R*math.sin(a),'#c9d6df');v=ag[k];rate=v['value']/100 if v['value'] is not None else None;points.append(None if rate is None else (cx+R*rate*math.cos(a),cy+R*rate*math.sin(a)))
        xx=cx+(R+22)*math.cos(a);yy=cy+(R+22)*math.sin(a);s.text(k,xx,yy,11,N,False,'middle');s.text(f'{rate:.0%}' if rate is not None else '待评估',xx,yy+14,10,MUTED,False,'middle')
    if all(p is not None for p in points):s.poly(points,'#afd2ed',B,2)
    else:
        for i in range(5):
            if points[i] and points[(i+1)%5]:s.line(*points[i],*points[(i+1)%5],B,2)
    for p in points:
        if p:s.circle(*p,3.3,B)
    if isretake:
        before=abilities(d['baseline']);bp=[]
        for k,a in zip(ABILITIES,angles):
            value=before[k]['value'];bp.append(None if value is None else (cx+R*value/100*math.cos(a),cy+R*value/100*math.sin(a)))
        for i in range(5):
            if bp[i] and bp[(i+1)%5]:s.line(*bp[i],*bp[(i+1)%5],GOLD,1.5)
        for p in bp:
            if p:s.circle(*p,2.5,GOLD)
        s.text('蓝色 复做 / 金色 首次',440,551,10,MUTED)
    rates=[(k,v['value']/100) for k,v in ag.items() if v['value'] is not None];strong=[k for k,v in rates if v>=.8];weak=[k for k,v in rates if v<.6];mid=[k for k,v in rates if .6<=v<.8]
    for i,(label,vals,c) in enumerate([('相对优势',strong,B),('优先补强',weak,'#d87932'),('继续提升',mid,'#579b73')]):
        yy=413+i*46;s.circle(688,yy-4,4,c);s.text(label,699,yy,12,c,True);s.wrapped('、'.join(vals) or '待评估',688,yy+19,110,11,2,14)
    # 05 loss table, rows editable in report digest
    panel(s,'05','失分与提分规划',28,572,784,388)
    custom=d.get('retakeRows') if isretake else d.get('lossDigest');rows=custom if isinstance(custom,list) and custom else default_digest(d)
    widths=[60,115,220,157,204];heads=['失分','失分板块','题目与作答证据','当前掌握程度','对应提分策略'];xx=42;yy=616
    for w,t in zip(widths,heads):s.rect(xx,yy,w,29,N);s.text(t,xx+w/2,yy+20,13,'white',True,'middle');xx+=w
    for i,q in enumerate(rows[:5]):
        xx=42;yy=645+i*60
        for j,(w,key) in enumerate(zip(widths,['loss','topic','evidence','mastery','action'])):
            s.rect(xx,yy,w,60,'white' if i%2==0 else '#eef4f8',BORDER);s.wrapped(q.get(key,''),xx+6,yy+18,w-12,12.8,3,17,'#bd4d35' if j==0 else N);xx+=w
    s.rect(28,972,784,160,'#eef4f8',BORDER,6);s.text('提分规划',42,997,17,N,True)
    strength=d.get('strengthText') or ('、'.join(strong)+'在本卷已核部分表现较好。' if strong else '尚需结合更多已核题目确认相对优势。')
    weaktext=d.get('weaknessText') or ('、'.join(weak)+'为当前优先补强方向。' if weak else '待结合原始作答和学生访谈定位薄弱环节。')
    for label,t,y in [('优势',strength,1020),('薄弱',weaktext,1057),('学习方向',d.get('directionText') or d['plan'] or '按错题原因训练，并用新题复测。',1094)]:
        s.text(label,42,y,13,'#b44c35',True);s.wrapped(t,107,y,688,12.5,2,16)
    s.text('教师：'+(d['teacher'] or '待填写')+'   |   '+('正式交付' if d.get('exportMode')=='final' else '校核草稿'),28,1155,11,MUTED)
    if isretake:
        rr=d['retakeMetrics'];s.text(f"学习验收 {rr['status']} · 原题通过率 {rr['rate']:.0%}",812,1155,11,MUTED,False,'end')
    return s

def export_pdf(d):return scene(d).pdf()
def export_svg(d):return scene(d).svg()
def export_docx(d):
    sc=scene(d);pdf=pypdfium2.PdfDocument(sc.pdf());im=pdf[0].render(scale=2).to_pil();png=io.BytesIO();im.save(png,format='PNG');pdf.close()
    doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.2677);sec.page_height=Inches(11.6929);sec.top_margin=sec.bottom_margin=Inches(.10);sec.left_margin=sec.right_margin=Inches(.10)
    p=doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph();p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1;p.paragraph_format.keep_with_next=False
    run=p.add_run();run.add_picture(io.BytesIO(png.getvalue()),width=Inches(8.02),height=Inches(11.34))
    part=Part(PackURI('/word/media/report_vector.svg'),'image/svg+xml',sc.svg(),doc.part.package);rid=doc.part.relate_to(part,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image');blip=run._r.xpath('.//a:blip')[0]
    extlist=OxmlElement('a:extLst');ext=OxmlElement('a:ext');ext.set('uri','{96DAC541-7B7A-43D3-8B79-37D633B846F1}');svgblip=etree.SubElement(ext,'{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip');svgblip.set(qn('r:embed'),rid);extlist.append(ext);blip.append(extlist)
    b=io.BytesIO();doc.save(b);return b.getvalue()
