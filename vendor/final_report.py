"""Reusable report adapted from the user's approved vector_rebuild / restore_orange.

The approved logo paths, embedded typefaces, palette and orange shading are retained.
All student and question content is supplied at runtime; no sample student's data is used.
"""
import io
import json
import math
import re
import threading
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from standards import stats, group, scored, report_view

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
W, H = 595.276, 841.89
O, N, B, D, G, R = '#F65B1B', '#173A5A', '#2868AE', '#222222', '#22AC72', '#F34E40'
COLORS = [B, G, R, O, '#8264A4', '#15979D']
RENDER_LOCK=threading.RLock()
for name, file in [('WYRegular', 'WenyuanSans-Regular.ttf'), ('WYBold', 'WenyuanSans-Bold.ttf'), ('WYMath', 'DejaVuSerif.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(ASSETS / file)))


def number(v):
    return f'{v:g}'


def text(value):
    return escape(str(value or '')).replace('\n', '<br/>')


def measure(markup, width, size):
    style = ParagraphStyle('m', fontName='WYRegular', fontSize=size, leading=size*1.56, wordWrap='CJK', splitLongWords=True)
    return Paragraph(markup, style).wrap(width, 10000)[1]


def priority(d):
    rows = [q for q in d['questions'] if not scored(q) or q['score'] < q['max']]
    return sorted(rows, key=lambda q: (-q.get('priority', 0), not scored(q), -(q['max']-(q.get('score') or 0))))


class Layout:
    def __init__(self, c):
        self.c = c

    def txt(self, x, y, s, size=10, bold=False, color=D):
        self.c.setFillColor(HexColor(color)); self.c.setFont('WYBold' if bold else 'WYRegular', size)
        self.c.drawString(x, H-y, str(s))

    def rect(self, x, y, w, h, fill='#FFFFFF', stroke=None, radius=7):
        self.c.setFillColor(HexColor(fill)); self.c.setStrokeColor(HexColor(stroke or fill)); self.c.setLineWidth(.6)
        self.c.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=int(bool(stroke)))

    def line(self, x, y, x2, y2, color='#E4EAF0', width=.6):
        self.c.setStrokeColor(HexColor(color)); self.c.setLineWidth(width); self.c.line(x,H-y,x2,H-y2)

    def para(self, x, y, value, width, max_height, size=9.1, color=D, bold=False, label='报告摘要'):
        return self.para_markup(x,y,text(value),width,max_height,size,color,bold,label)

    def para_markup(self, x, y, markup, width, max_height, size=9.1, color=D, bold=False, label='报告摘要'):
        for fs in [size, size-.3, size-.6, size-.9, max(7.4,size-1.2)]:
            style = ParagraphStyle('wy',fontName='WYBold' if bold else 'WYRegular',fontSize=fs,leading=fs*1.56,textColor=HexColor(color),wordWrap='CJK',splitLongWords=True)
            p = Paragraph(markup,style); _, height = p.wrap(width,10000)
            if height <= max_height:
                p.drawOn(self.c,x,H-y-height); return y+height
        raise ValueError(f'「{label}」文字超出最终模板区域，请在报告文案中精简；完整内容保留在逐题记录。')

    def rgt(self, x, y, s, size=8.5, bold=False, color=D):
        self.c.setFillColor(HexColor(color)); self.c.setFont('WYBold' if bold else 'WYRegular', size)
        self.c.drawRightString(x, H-y, str(s))

    def logo(self,x,y,w=23):
        self.c.saveState();self.c.setFillColor(HexColor(O))
        shapes=[[(35,195),(275,188),(338,215),(453,397),(294,602)],[(325,639),(685,180),(774,86),(877,40),(1127,36),(856,383),(587,695),(510,729),(432,729),(363,700)],[(648,695),(834,460),(932,331),(1005,303),(1205,303),(1018,542),(922,651),(850,684),(751,695)]]
        for ps in shapes:
            p=self.c.beginPath();p.moveTo(x+ps[0][0]*w/1240,H-y-ps[0][1]*w/1240)
            for xx,yy in ps[1:]:p.lineTo(x+xx*w/1240,H-y-yy*w/1240)
            p.close();self.c.drawPath(p,fill=1,stroke=0)
        self.c.restoreState()

    def header(self,title):
        self.logo(27,13);self.txt(58,25,'文源教育',9,True);self.txt(477,25,'试卷分析报告',8)
        self.line(27,35,568,35,O);self.txt(27,67,title,20,True);self.line(27,85,568,85,'#FFE4D0')

    def card(self,x,y,w,h,num,title):
        self.rect(x,y,w,h,stroke='#DFE6ED');self.line(x+8,y+1,x+w-8,y+1,B,1.3)
        self.rect(x+13,y+14,20,15,B,radius=3);self.txt(x+17,y+25,num,7.5,True,'#FFFFFF');self.txt(x+40,y+26,title,10.5,True,N)

    def bar(self,x,y,w,value,color=B):
        self.rect(x,y,w,5,'#E8EDF5',radius=2)
        if value>0:self.rect(x,y,w*min(1,value),5,color,radius=2)


def appendix_pdf(d, questions):
    buf=io.BytesIO()
    def head(c,doc):
        L=Layout(c);L.logo(27,13);L.txt(58,25,'文源教育',9,True);L.txt(477,25,'试卷分析报告',8);L.line(27,35,568,35,O)
    doc=SimpleDocTemplate(buf,pagesize=(W,H),leftMargin=27,rightMargin=27,topMargin=54,bottomMargin=51)
    title=ParagraphStyle('title',fontName='WYBold',fontSize=18,leading=27,textColor=HexColor(D),wordWrap='CJK')
    sub=ParagraphStyle('sub',fontName='WYBold',fontSize=11,leading=17,textColor=HexColor(B),wordWrap='CJK')
    body=ParagraphStyle('body',fontName='WYRegular',fontSize=10.2,leading=17,wordWrap='CJK',spaceAfter=9)
    box=ParagraphStyle('box',parent=body,backColor=HexColor('#F1F5FC'),borderPadding=9,spaceBefore=5,spaceAfter=16)
    story=[]
    for i,q in enumerate(questions):
        if i:story.append(PageBreak())
        score=f"{number(q['score'])}/{number(q['max'])}分" if scored(q) else '得分待核'
        has_practice=bool(str(q.get('practiceQuestion') or '').strip())
        subtitle=f"{score} / 原来怎么答 · 正确怎么做"+(' · 自主练习' if has_practice else '')
        story += [Paragraph(text(f"附件 {chr(65+i)}  第{q['id']}题 · {q['topic']}"),title),Spacer(1,8),Paragraph(text(subtitle),body),Spacer(1,9)]
        sections=[('学生原始作答',q.get('studentAnswer') or q.get('evidence') or '原始作答待核对'),('作答对照与问题定位',q.get('cause') or q.get('digestMastery') or '待结合原始作答补充分析'),('参考结果',q.get('referenceAnswer') or '参考结果待核'),('这道题先看哪里',q.get('conditions') or q.get('challenge') or '待补充关键条件'),('关键解法',q.get('solution') or '待补充关键解法'),('下次遇到这类题，按这个顺序做',q.get('action') or q.get('digestAction') or '待填写训练步骤')]
        if has_practice:sections.append(('自主练习',q['practiceQuestion']))
        sections.append(('验收要求',q.get('acceptance') or '独立完成；结果、关键步骤及必要表达完整。'))
        for label,value in sections:
            story.append(KeepTogether([Paragraph(text(label),sub),Spacer(1,5)]))
            story.append(Paragraph(text(value),box if label in ['关键解法','自主练习'] else body))
            if label=='自主练习':story.append(Spacer(1,18))
        if has_practice and q.get('practiceAnswer'):
            story.extend([Paragraph('练习参考答案（完成后查看）',sub),Paragraph(text(q['practiceAnswer']),body)])
        source=q.get('scoringSource') or '评分来源待核实'
        story.append(Paragraph(text('作答与评分依据：'+source+'；'+q.get('sourcePage','')),body))
    doc.build(story,onFirstPage=head,onLaterPages=head)
    return buf.getvalue()


def export_final_pdf(original,kind='first'):
    d=report_view(original,kind)
    d={**original,**d}
    if kind=='retake':
        d['analysisDate']=d.get('retakeDate') or d.get('analysisDate')
        for q in d['questions']:
            q['digestEvidence']=q.get('studentAnswer','');q['digestMastery']=q.get('cause','');q['digestAction']=q.get('action','')
        for field in ['planFirst','planNext','planLater','problemText','nextStepText']:
            d[field]=d.get('retake'+field[0].upper()+field[1:]) or ''
    if not d['questions']:raise ValueError('请先录入题目')
    full,score,known=stats(d);lost=known-score;complete=known==full
    loss_text=number(lost) if complete else number(lost)+'（已核）'
    rate=score/known if known else 0
    name=d.get('student') or '未命名学生';subject=d.get('subject') or '物理'
    strong=d.get('strengthText') or '；'.join(f"第{q['id']}题取得{number(q['score'])}/{number(q['max'])}分" for q in [q for q in d['questions'] if scored(q) and q['score']==q['max']][:3]) or '目前尚无已确认的满分题目，需结合实际过程确认优势。'
    weak=d.get('weaknessText') or '；'.join(f"第{q['id']}题{q['topic']}失{number(q['max']-q['score'])}分" for q in priority(d)[:3] if scored(q)) or '待结合逐题作答核实薄弱环节。'
    direction=d.get('directionText') or '先核对原始作答和评分依据，再按失分证据安排复习。'
    rows=priority(d)
    buf=io.BytesIO();c=canvas.Canvas(buf,pagesize=(W,H));c.setTitle(f'文源教育｜{name}试卷分析报告');c.setAuthor('文源教育');L=Layout(c)
    L.logo(45,56,47);L.txt(103,75,'文源教育',15,True);L.txt(103,88,'WENYUAN EDUCATION',5.7,True)
    L.txt(50,246,'试卷分析报告',40,True);L.line(50,269,147,269,O,1.7)
    for y,label,value in [(313,'学生：',name),(352,'学校：',d.get('school') or '—'),(390,'年级：',d.get('grade') or d.get('stage')),(428,'学科：',subject),(467,'考试：',d.get('exam') or '—'),(505,'报告日期：',d.get('analysisDate') or '—')]:
        L.txt(50,y,label,14);L.para(151 if label=='报告日期：' else 112,y-15,value,380,31,14,label='封面'+label)
    if kind=='retake':L.txt(50,548,'讲解后独立复做分析',12,True,N)
    c.showPage();L.header(subject+'试卷分析报告' if kind!='retake' else subject+'独立复做分析报告')
    L.card(27,100,262,322,'01','这次考得怎么样');L.card(306,100,262,322,'02','各类题拿了多少分')
    score_label=number(score) if known else '—';score_size=36
    while pdfmetrics.stringWidth(score_label,'WYBold',score_size)>65 and score_size>17:score_size-=1
    L.txt(41,174,score_label,score_size,True,O);L.txt(46+pdfmetrics.stringWidth(score_label,'WYBold',score_size),174,'分',8,color='#555555');L.line(126,141,126,176)
    L.txt(137,145,'满分',8,color='#666666');L.txt(137,172,number(full),16,True,O)
    summary=f'得分率 {rate*100:.1f}% · 失分 {number(lost)} 分' if complete else f'已核 {number(known)}/{number(full)}分 · 待核 {number(full-known)}分'
    L.txt(41,202,summary,8.7);L.bar(41,213,137,rate)
    cx,cy,rad=232,H-206,21
    # The dial is a 100-point score, normalized by the subject's full marks.
    # An incomplete score is not enough to claim a full-paper normalized score.
    gauge_rate=score/full if complete and full else None
    c.saveState();c.setLineWidth(5.2);c.setLineCap(0)
    c.setStrokeColor(HexColor('#E8ECF3'));c.arc(cx-rad,cy-rad,cx+rad,cy+rad,-30,240)
    sweep=240*max(0,min(1,gauge_rate)) if gauge_rate is not None else 0
    if sweep:
        c.setStrokeColor(HexColor('#F17B3E'));c.arc(cx-rad,cy-rad,cx+rad,cy+rad,210-sweep,sweep)
    angle=math.radians(210-sweep);dx,dy=math.cos(angle),math.sin(angle);nx,ny=-dy,dx
    pointer=c.beginPath();pointer.moveTo(cx-dx*2.6,cy-dy*2.6)
    pointer.lineTo(cx+nx*1.9,cy+ny*1.9);pointer.lineTo(cx+dx*rad*.81,cy+dy*rad*.81)
    pointer.lineTo(cx-nx*1.9,cy-ny*1.9);pointer.close()
    c.setFillColor(HexColor(N))
    if gauge_rate is not None:c.drawPath(pointer,fill=1,stroke=0)
    c.restoreState()
    y=L.para_markup(41,236,f'<font name="WYBold" color="{G}">优势｜</font>{text(strong)}',234,40,9.0,N,label='优势短摘要')
    full_qs=[q for q in d['questions'] if scored(q) and q['score']==q['max']]
    if full_qs:
        ids='、'.join(str(q['id']) for q in full_qs[:8])
        note=f'满分 {len(full_qs)} 题：第{ids}题'+('…' if len(full_qs)>8 else '')
        y=L.para_markup(41,y+2,f'<font color="#6B7A8A">{text(note)}</font>',234,15,7.5,'#6B7A8A',label='优势补充说明')
    y=L.para_markup(41,y+10,f'<font name="WYBold" color="{R}">短板｜</font>{text(weak)}',234,40,9.0,N,label='薄弱短摘要')
    top_lost=[q for q in rows if scored(q)][:3]
    if top_lost:
        note='、'.join(f"第{q['id']}题{number(q['max']-q['score'])}分" for q in top_lost)
        y=L.para_markup(41,y+2,f'<font color="#6B7A8A">失分最重：{text(note)}</font>',234,15,7.5,'#6B7A8A',label='薄弱补充说明')
    if top_lost and y+18<366:
        gain=sum(q['max']-q['score'] for q in top_lost)
        target='先拿回 '+number(gain)+' 分：'+' · '.join(f"第{q['id']}题" for q in top_lost)
        y=L.para_markup(41,y+8,f'<font color="#9A6A2E">{text(target)}</font>',234,14,7.6,'#9A6A2E',label='本轮目标')
    paired=d.get('pairedScores',{});result_note=direction
    if kind=='retake':
        result_note=(f"同范围得分：{number(paired.get('before',0))}/{number(paired.get('max',0))} → {number(paired.get('after',0))}/{number(paired.get('max',0))}；" if paired.get('max') else '')+'学习验收：'+d.get('retakeMetrics',{}).get('status','待完成')+'。'
    top=min(max(y+10,372),380);box_h=410-top
    L.rect(41,top,234,box_h,'#FFF6E5',radius=4);L.para(47,top+7,result_note,222,box_h-12,8.2,N,label='学习方向短摘要')
    types=list(group(d,'type').items())
    if len(types)>6:raise ValueError('最终模板的题型最多展示6类，请合并同类题型名称')
    step=min(70,266/max(1,len(types)))
    for i,(key,(total,got,verified)) in enumerate(types):
        yy=148+i*step;color=COLORS[i%len(COLORS)];v=got/verified if verified else 0
        L.txt(320,yy,key,9,True,color);L.txt(421,yy,f'{number(got)} / {number(total)}',8.5);L.txt(521,yy,f'{v*100:.1f}%' if verified==total else '待核',8,True,color);L.bar(320,yy+9,233,v,color)
        wrong=[q for q in d['questions'] if q['type']==key and scored(q) and q['score']<q['max']]
        default_comment=(f"尚有{number(total-verified)}分待核。" if verified<total else ('第'+'、'.join(q['id'] for q in wrong[:3])+'题失分，重点复习'+'、'.join(dict.fromkeys(q['topic'] for q in wrong[:2]))+'。' if wrong else '本次该题型均取得满分，继续巩固。'))
        comment=(d.get('typeComments') or {}).get(key) or default_comment
        L.para(320,yy+21,comment,233,max(17,step-27),8.1,color,label=key+'题型说明')
    L.card(27,437,262,318,'03',loss_text+' 分失分去了哪里');L.card(306,437,262,318,'04','做得好的地方，继续保持')
    loss_types=sorted([(k,max(0,v[2]-v[1])) for k,v in types if v[2]>v[1]],key=lambda kv:-kv[1])
    cx,cy,rad=158,H-552,44;start=90
    if lost:
        for i,(key,value) in enumerate(loss_types):
            c.setFillColor(HexColor(COLORS[i%len(COLORS)]));c.setStrokeColor(white);c.setLineWidth(.6);c.wedge(cx-rad,cy-rad,cx+rad,cy+rad,start,-360*value/lost,fill=1,stroke=1);start-=360*value/lost
    else:c.setFillColor(HexColor('#E8EDF5'));c.circle(cx,cy,rad,fill=1,stroke=0)
    c.setFillColor(white);c.circle(cx,cy,27,fill=1,stroke=0);L.txt(146,551,number(lost),12,True,N);L.txt(147,568,'失分',9,True,N)
    y=618;n=max(1,len(loss_types) or 1);step=min(24,86/n)
    for i,(key,value) in enumerate(loss_types or [('已核题目未失分',0)]):
        color=COLORS[i%len(COLORS)]
        L.rect(41,y-6,6,6,color,radius=1)
        L.txt(52,y,f'{key} 失{number(value)}分',9.2,True,color)
        L.rgt(270,y,f'{value/lost*100:.1f}%' if lost else '—',8.6,True,color)
        L.rect(52,y+5,210,3,'#EDF1F6',radius=1.5)
        if lost:L.rect(52,y+5,210*value/lost,3,color,radius=1.5)
        y+=step
    if loss_types:
        ranked=sorted(loss_types,key=lambda kv:-kv[1])
        insight=f'{ranked[0][0]}失{number(ranked[0][1])}分，占{ranked[0][1]/lost*100:.1f}%，是本次最大失分来源'+(f'；其次是{ranked[1][0]}。' if len(ranked)>1 else '。')
        L.para_markup(41,700,f'<font color="#6B7A8A">{text(insight)}</font>',233,30,7.9,'#6B7A8A',label='失分结构判断')
    else:
        L.para_markup(41,664,'<font color="#6B7A8A">本次已核题目全部得分，没有可拆解的失分结构。</font>',233,30,8.2,'#6B7A8A',label='失分结构判断')
    L.txt(41,739,f'本次实际失分合计{number(lost)}分。' if complete else f'已确认失分{number(lost)}分，另有{number(full-known)}分待核。',7.4,color='#666666')
    L.txt(320,486,'本次表现较好的部分',9.3,True,G)
    y=L.para_markup(320,497,strong,233,38,8.9,N,label='优势详细说明')
    show=sorted([q for q in d['questions'] if scored(q) and q['score']>0],key=lambda q:(-(q['score']/q['max']),-q['score']))[:6]
    if show:
        y=max(y+8,534)
        L.txt(320,y,'得分最稳的几道题',7.6,True,'#7A8796');y+=5
        rh=min(22,max(14,(670-y)/len(show)))
        for q in show:
            L.rect(320,y,233,rh-3,'#F7FAF8',radius=2)
            L.txt(326,y+rh-9,f"第{q['id']}题",8.1,True,N)
            L.txt(366,y+rh-9,q['topic'],8.1)
            L.rgt(547,y+rh-9,f"{number(q['score'])}/{number(q['max'])}",8.1,True,G)
            y+=rh
    wy=y+14
    L.txt(320,wy,'下一步先补这些地方',9.3,True,O)
    y=L.para_markup(320,wy+9,weak,233,40,8.9,R,label='薄弱详细说明')
    if 736-y>=40:
        bh=min(48,726-y)
        if bh>=40:
            L.rect(320,y+10,233,bh,'#F1F5FC',radius=4)
            L.para_markup(327,y+17,'<font color="#5A6B7D">保持方法：满分题隔周各做一道变式；每次限时 20 分钟，只查模型与步骤是否完整。</font>',219,bh-14,7.9,'#5A6B7D',label='04保持方法')
    if y+12<736:L.para_markup(320,738,'<font color="#6B7A8A">按 05 的顺序逐题改，改完在 06 的验收里打勾。</font>',233,12,7.4,'#6B7A8A',label='04页脚注')
    c.showPage();L.header('主要问题和复习安排');L.card(27,100,541,330,'05','哪些地方丢了分，怎么改')
    selected=(rows or (d['questions'] if kind=='retake' else []))[:4]
    if not selected:
        L.para(41,144,'本次已核题目没有失分；下面这些题的方法要保持，隔周用变式题验证。',511,34,9.6)
        keep=[q for q in d['questions'] if scored(q)][:16]
        y=190;rh=min(26,(418-y)/max(1,len(keep)))
        for q in keep:
            L.txt(41,y,f"第{q['id']}题 · {q['topic']}",8.8,True,N)
            L.txt(210,y,'独立复述一遍解法，隔周做一道变式',8.4,color='#6B7A8A')
            L.rgt(547,y,f"{number(q['score'])}/{number(q['max'])}",8.4,True,G)
            y+=rh
    cols=2 if len(selected)==4 else 1
    cell_w=250 if cols==2 else 511
    text_w=cell_w-6
    nrows=(len(selected)+cols-1)//cols if selected else 1
    gap=12;top0=144;bottom0=418
    cell_h=(bottom0-top0-gap*(nrows-1))/nrows
    for i,q in enumerate(selected):
        r,col=divmod(i,cols);x=41+col*266;y0=top0+r*(cell_h+gap)
        state=(f"复做{number(q['score'])}/{number(q['max'])}分" if kind=='retake' else f"失{number(q['max']-q['score'])}分") if scored(q) else '分数待核'
        L.txt(x,y0+3,f"第{q['id']}题 · {q['topic']}（{state}）",8.8,True,O)
        raw=[('原答',q.get('digestEvidence') or q.get('studentAnswer')),('卡点',q.get('digestMastery') or q.get('cause')),('怎么练',q.get('digestAction') or q.get('action')),('验收',q.get('acceptance'))]
        cells=[(f'<font name="WYBold" color="#7A8796">{label}｜</font>{text(value)}',f'第{q["id"]}题{label}') for label,value in raw if value]
        fs=9.0;hs=[measure(m,text_w,fs) for m,_ in cells]
        for fs in (9.0,8.7,8.4,8.1,7.8):
            hs=[measure(m,text_w,fs) for m,_ in cells]
            if 20+sum(hs)<=cell_h:break
        extra=max(0,min(6,(cell_h-20-sum(hs))/max(1,len(cells))))
        yy=y0+20
        for (m,lab),h in zip(cells,hs):
            yy=L.para_markup(x,yy,m,text_w,h+0.6,fs,N,label=lab)+extra
    L.card(27,444,541,164,'06','近期怎么复习：先抓重点，别同时铺开')
    defaults=[(selected[0].get('action') if selected else '') or direction,(selected[1].get('action') if len(selected)>1 else '') or d.get('plan') or direction,d.get('plan') or direction]
    for i,(label,key) in enumerate([('优先处理','planFirst'),('随后巩固','planNext'),('后续专题与检查习惯','planLater')]):
        xx=41+i*175;L.txt(xx,488,label,9,True,N);L.line(xx,497,xx+160,497,B);L.para(xx,505,d.get(key) or defaults[i],160,80,9.4,label=label+'安排')
    L.para_markup(41,588,'<font color="#6B7A8A">节奏：按上面的顺序推进，每完成一项打勾；两周后按 05 的验收复测。</font>',511,12,7.6,'#6B7A8A',label='06节奏')
    L.card(27,610,541,185,'07','诊断反馈')
    problem=d.get('problemText') or d.get('teacherCommunication') or weak
    step=d.get('nextStepText') or d.get('planFirst') or direction
    y=L.para_markup(41,666,f'<font name="WYBold" color="{N}">问题出在哪儿｜</font>{text(problem)}',511,46,8.9,N,label='诊断反馈·问题')
    y=L.para_markup(41,y+8,f'<font name="WYBold" color="{O}">接下来怎么做｜</font>{text(step)}',511,max(30,758-y),8.9,N,label='诊断反馈·做法')
    pick='、'.join(f"第{q['id']}题" for q in (selected or [])[:4])
    tail=f'下次课先查：{pick}，按 05 的验收逐条过；未过项当堂重做，不加新题。' if pick else '本次已核题目全部得分：保持现有节奏，隔周用变式题复测一次。'
    if y+22<790:L.para_markup(41,y+10,f'<font color="#6B7A8A">{escape(tail)}</font>',511,20,7.6,'#6B7A8A',label='诊断反馈·验收')
    c.showPage();c.save()
    requested=[s.strip() for s in str(d.get('appendixIds') or '').replace('，',',').split(',') if s.strip()]
    if requested:
        mapping={q['id']:q for q in d['questions']}
        if len(requested)>5 or len(set(requested))!=len(requested) or any(qid not in mapping for qid in requested):raise ValueError('附件题号须存在且不重复，最多5题；用英文逗号分隔')
        chosen=[mapping[qid] for qid in requested]
    else:chosen=(rows+[q for q in d['questions'] if q not in rows])[:2]
    with fitz.open(stream=buf.getvalue(),filetype='pdf') as main, fitz.open(ASSETS/'orange_cover.pdf') as cover:
        main[0].show_pdf_page(main[0].rect,cover,0,overlay=False)
        if chosen:
            with fitz.open(stream=appendix_pdf(d,chosen),filetype='pdf') as appendix:main.insert_pdf(appendix)
        total=len(main)
        foot=io.BytesIO();fc=canvas.Canvas(foot,pagesize=(W,H));F=Layout(fc)
        for i in range(total):
            if i:
                F.line(27,813,568,813);F.txt(27,829,'文源教育 · 试卷分析报告 · '+(d.get('analysisDate') or ''),7.6,color='#555555');F.txt(532,829,f'{i+1:02d} / {total:02d}',7.6,color='#555555')
            fc.showPage()
        fc.save()
        with fitz.open(stream=foot.getvalue(),filetype='pdf') as overlay:
            for i in range(1,total):main[i].show_pdf_page(main[i].rect,overlay,i)
        main.set_metadata({'title':f'文源教育｜{name}试卷分析报告','author':'文源教育'})
        return main.tobytes(garbage=4,deflate=True)


_render_uncached=export_final_pdf
@lru_cache(maxsize=3)
def _render_cached(serialized,kind):
    return _render_uncached(json.loads(serialized),kind)
def export_final_pdf(data,kind='first'):
    with RENDER_LOCK:
        return _render_cached(json.dumps(data,ensure_ascii=False,sort_keys=True),kind)

def preview_pages(data,kind='first'):
    with RENDER_LOCK:
        raw=export_final_pdf(data,kind)
        import base64
        with fitz.open(stream=raw,filetype='pdf') as doc:
            return {'count':len(doc),'pages':['data:image/png;base64,'+base64.b64encode(p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).tobytes('png')).decode() for p in doc]}
